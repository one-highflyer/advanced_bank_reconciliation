import logging

import frappe
from frappe.utils import flt

from advanced_bank_reconciliation.utils.logger import (
    get_logger,
)
from erpnext.accounts.doctype.bank_transaction.bank_transaction import (
    BankTransaction,
    get_clearance_details,
    get_related_bank_gl_entries,
    get_total_allocated_amount,
)


def get_voucher_allocation_amount(voucher, precision):
    """Use ERPNext allocation only for internal transfers with two bank legs."""
    if voucher["payment_doctype"] == "Payment Entry":
        payment_type = frappe.db.get_value(
            "Payment Entry", voucher["payment_name"], "payment_type"
        )
        if payment_type == "Internal Transfer":
            return 0.0

    return flt(voucher["amount"], precision)


def validate_internal_transfer_selection(transaction, vouchers):
    """Validate the selection and return automatic amounts keyed by transfer name."""
    if transaction.docstatus != 1:
        frappe.throw(frappe._("Bank Transaction must be submitted"))

    existing = [
        {
            "payment_doctype": row.payment_document,
            "payment_name": row.payment_entry,
            "amount": row.allocated_amount,
        }
        for row in transaction.get("payment_entries", [])
    ]
    rows = existing + list(vouchers)
    transfers = []
    has_negative = any(flt(row.get("amount")) < 0 for row in rows)
    for row in rows:
        doctype, name = row["payment_doctype"], row["payment_name"]
        if doctype == "Payment Entry":
            payment = frappe.get_doc(doctype, name)
            if payment.payment_type == "Internal Transfer":
                transfers.append(payment)
        elif doctype in ("Sales Invoice", "Purchase Invoice"):
            if flt(frappe.db.get_value(doctype, name, "outstanding_amount")) < 0:
                has_negative = True
    if not transfers:
        return {}
    keys = [(row["payment_doctype"], row["payment_name"]) for row in vouchers]
    if len(keys) != len(set(keys)):
        frappe.throw(frappe._("Select each voucher only once."))
    if has_negative:
        frappe.throw(
            frappe._(
                "Reconcile refunds and negative allocations separately from internal transfers."
            )
        )
    bank_account = frappe.db.get_value(
        "Bank Account", transaction.bank_account, "account"
    )
    bank_side = "paid_to" if flt(transaction.deposit) > 0 else "paid_from"
    for payment in transfers:
        if payment.docstatus != 1 or payment.get(bank_side) != bank_account:
            frappe.throw(
                frappe._(
                    "The internal transfer does not match this bank transaction's account and direction."
                )
            )

    transfer_names = {payment.name for payment in transfers}
    selected_transfers = [
        row for row in vouchers
        if row["payment_doctype"] == "Payment Entry" and row["payment_name"] in transfer_names
    ]
    if not selected_transfers:
        return {}
    precision = transaction.precision("allocated_amount", "payment_entries")
    remaining = flt(transaction.unallocated_amount, precision) - sum(
        flt(row.get("amount"), precision) for row in vouchers if row not in selected_transfers
    )
    docs = [("Payment Entry", row["payment_name"]) for row in selected_transfers]
    gl_entries = get_related_bank_gl_entries(docs)
    allocations = get_total_allocated_amount(docs)
    transfer_amounts = {}
    for row in selected_transfers:
        key = ("Payment Entry", row["payment_name"])
        available, _, _ = get_clearance_details(
            transaction,
            frappe._dict(payment_document="Payment Entry", payment_entry=row["payment_name"]),
            dict(allocations.get(key, {})), dict(gl_entries.get(key, {})), bank_account,
        )
        amount = flt(min(available, remaining), precision)
        if amount <= 0:
            frappe.throw(frappe._("No amount remains to allocate to the selected internal transfer."))
        transfer_amounts[row["payment_name"]] = amount
        remaining = flt(remaining - amount, precision)
    return transfer_amounts


class ExtendedBankTransaction(BankTransaction):
    @frappe.whitelist()
    def remove_payment_entries(self):
        # Removal mutates the child table. Iterate a copy to unlink every row.
        for payment_entry in list(self.payment_entries):
            self.remove_payment_entry(payment_entry)
        self.save()

    def clear_linked_payment_entry(self, payment_entry, clearance_date=None):
        if (
            clearance_date
            and payment_entry.payment_document == "Payment Entry"
            and frappe.db.get_value(
                "Payment Entry", payment_entry.payment_entry, "payment_type"
            )
            == "Internal Transfer"
        ):
            from advanced_bank_reconciliation.utils.internal_transfer import (
                get_internal_transfer_clearance_date,
            )

            clearance_date = get_internal_transfer_clearance_date(
                payment_entry.payment_entry, current_date=clearance_date
            )
        super().clear_linked_payment_entry(payment_entry, clearance_date)

    def before_update_after_submit(self):
        super().before_update_after_submit()
        # Fetch the current state of the document from the database
        existing_doc = frappe.get_doc(self.doctype, self.name)
        # Store the current state of the child table
        self._previous_payments = existing_doc.get("payment_entries")

    def on_update_after_submit(self):
        self.process_removed_payment_entries()

        # Trigger background validation if payment entries were added or modified
        if self.payment_entries and len(self.payment_entries) > 0:
            self.trigger_background_validation()

    def on_cancel(self):
        super().on_cancel()
        # delink_payment_entry is overridden to no-op for PI/SI so that the
        # save-path's process_removed_payment_entries can decide whether
        # cumulative allocations still cover paid_amount before clearing.
        # on_cancel never fires process_removed_payment_entries, so we have
        # to re-evaluate PI/SI clearance here directly. By this point
        # super().on_cancel() has marked the BT cancelled, so the cumulative
        # SQL (docstatus=1 filter) correctly excludes this BT's allocations.
        logger = get_logger()
        try:
            for pe in self.payment_entries or []:
                if pe.payment_document in ("Purchase Invoice", "Sales Invoice"):
                    self.clear_document_clearance_date(
                        pe.payment_document, pe.payment_entry
                    )
        except Exception as e:
            logger.error(
                "Error re-evaluating PI/SI clearance on cancel of BT %s: %s",
                self.name, str(e), exc_info=True,
            )

    def process_removed_payment_entries(self):
        """Process any payment entries that were removed from the bank transaction"""
        logger = get_logger()
        try:
            # Get the previous document state
            if hasattr(self, "_previous_payments") and self._previous_payments:
                logger.info(
                    "Processing removed payment entries for bank transaction %s",
                    self.name,
                )
                current_payments = self.payment_entries or []

                # Find removed payments
                current_payment_keys = {
                    (p.payment_document, p.payment_entry) for p in current_payments
                }
                removed_payments = [
                    p
                    for p in self._previous_payments
                    if (p.payment_document, p.payment_entry) not in current_payment_keys
                ]

                # Clear clearance dates for removed payments
                for previous_payment in removed_payments:
                    logger.info(
                        "Clearing clearance date for %s %s",
                        previous_payment.payment_document,
                        previous_payment.payment_entry,
                    )
                    self.clear_document_clearance_date(
                        previous_payment.payment_document,
                        previous_payment.payment_entry,
                    )
        except Exception as e:
            logger.error(
                "Error processing removed payment entries for bank transaction %s: %s",
                self.name,
                str(e),
                exc_info=True,
            )

    def clear_document_clearance_date(self, document_type, document_name):
        """Reset clearance_date on a removed allocation target.

        Sales Invoice clears the matching Sales Invoice Payment child row;
        Purchase Invoice clears the direct field; Payment Entry / Journal
        Entry clear their own clearance_date field. For PI/SI the clear is
        conditional on cumulative submitted allocations no longer matching
        paid_amount (within tolerance) - when other BTs still cover the
        invoice the clearance is preserved.
        """
        logger = get_logger()
        try:
            # Handle Sales Invoice - clearance date goes on Sales Invoice Payment child table
            if document_type == "Sales Invoice":
                from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
                    should_clear_invoice,
                )
                sales_invoice = frappe.get_doc("Sales Invoice", document_name)
                bank_account_gl = frappe.db.get_value(
                    "Bank Account", self.bank_account, "account"
                )

                for payment in sales_invoice.payments:
                    if payment.account == bank_account_gl and payment.clearance_date:
                        if not should_clear_invoice(
                            "Sales Invoice", document_name, payment.amount, bank_account_gl
                        ):
                            frappe.db.set_value(
                                "Sales Invoice Payment",
                                payment.name,
                                "clearance_date",
                                None,
                            )
                            logger.info(
                                "Cleared clearance_date for Sales Invoice Payment %s (cumulative dropped below)",
                                payment.name,
                            )
                        else:
                            logger.info(
                                "Keeping clearance_date for Sales Invoice Payment %s: cumulative still matches amount",
                                payment.name,
                            )

            # Handle Purchase Invoice - conditional on cumulative allocation
            elif document_type == "Purchase Invoice":
                from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
                    should_clear_invoice,
                )
                if frappe.db.exists(document_type, document_name):
                    meta = frappe.get_meta(document_type)
                    if meta.has_field("clearance_date"):
                        bank_account_gl = frappe.db.get_value(
                            "Bank Account", self.bank_account, "account"
                        )
                        target_paid_amount = frappe.db.get_value(
                            document_type, document_name, "paid_amount"
                        ) or 0
                        if not should_clear_invoice(
                            document_type, document_name, target_paid_amount, bank_account_gl
                        ):
                            frappe.db.set_value(
                                document_type, document_name, "clearance_date", None
                            )
                            logger.info(
                                "Cleared clearance_date for %s %s (cumulative dropped below paid_amount)",
                                document_type,
                                document_name,
                            )
                        else:
                            logger.info(
                                "Keeping clearance_date for %s %s: cumulative still matches paid_amount",
                                document_type,
                                document_name,
                            )
                    else:
                        logger.debug(
                            "%s does not have clearance_date field", document_type
                        )

            # Handle Payment Entry and Journal Entry with direct clearance_date field
            elif document_type in [
                "Payment Entry",
                "Journal Entry",
            ]:
                # Check if the document exists and has clearance_date field
                if frappe.db.exists(document_type, document_name):
                    # Get the meta to check if clearance_date field exists
                    meta = frappe.get_meta(document_type)
                    if meta.has_field("clearance_date"):
                        frappe.db.set_value(
                            document_type, document_name, "clearance_date", None
                        )
                        logger.info(
                            "Cleared clearance_date for %s %s",
                            document_type,
                            document_name,
                        )
                    else:
                        logger.debug(
                            "%s does not have clearance_date field", document_type
                        )
            else:
                logger.debug(
                    "Document type %s not supported for clearance date clearing",
                    document_type,
                )

        except Exception as e:
            logger.error(
                "Error clearing clearance date for %s %s: %s",
                document_type,
                document_name,
                str(e),
                exc_info=True,
            )

    def trigger_background_validation(self):
        """Trigger background validation when bank transaction is updated with payment entries"""
        logger = get_logger()
        try:
            # Only trigger validation if this transaction has payment entries
            if self.payment_entries:
                frappe.enqueue(
                    "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.validate_single_bank_transaction",
                    bank_transaction_name=self.name,
                    queue="long",
                    timeout=300,
                    job_name="validate_bank_transaction_%s" % self.name,
                )
                logger.info(
                    "Triggered background validation for bank transaction %s", self.name
                )
        except Exception as e:
            logger.error(
                "Failed to trigger background validation for bank transaction %s: %s",
                self.name,
                str(e),
                exc_info=True,
            )

    def delink_payment_entry(self, payment_entry):
        """Override upstream to skip clear_linked_payment_entry for paid SI/PI.

        Upstream's delink_payment_entry unconditionally clears the PI/SI
        clearance_date before ABR's process_removed_payment_entries runs.
        That breaks the deferred-clearance "preserve" semantic: a PI whose
        cumulative allocation still covers paid_amount (e.g. when one of
        several over-allocating BTs is unreconciled) loses its clearance_date
        even though the remaining allocations still settle it.

        For Bank Transaction parent doc references, keep upstream behavior
        (chained-BT support). For PE/JE keep upstream behavior (their
        clearance semantics already correctly track allocated_amount vs
        paid_amount inside clear_linked_payment_entry's get_clearance_details).
        For PI/SI, skip the upstream clear here; ABR's
        process_removed_payment_entries -> clear_document_clearance_date
        (which uses the tolerance-aware should_clear_invoice helper)
        becomes the sole clearance-clearing path for those types.
        """
        if payment_entry.payment_document == "Bank Transaction":
            self.update_linked_bank_transaction(
                payment_entry.payment_entry, allocated_amount=None
            )
        elif payment_entry.payment_document in ("Purchase Invoice", "Sales Invoice"):
            return
        else:
            self.clear_linked_payment_entry(payment_entry, clearance_date=None)

    def add_payment_entries(self, vouchers):
        "Add the vouchers with zero allocation. Save() will perform the allocations and clearance"
        logger = get_logger()
        validate_internal_transfer_selection(self, vouchers)

        if 0.0 >= self.unallocated_amount:
            frappe.throw(
                frappe._("Bank Transaction {0} is already fully reconciled").format(
                    self.name
                )
            )

        # Round to the child field's precision so the in-memory value matches
        # what gets persisted. Without this, an unrounded float
        # (e.g. 110.28999999999996 from JS arithmetic) triggers
        # UpdateAfterSubmitError on the subsequent save in reconcile_vouchers,
        # because validate_update_after_submit compares the unrounded
        # in-memory value against the rounded DB value.
        allocated_precision = self.precision("allocated_amount", "payment_entries")

        added = False
        for voucher in vouchers:
            # Can't add same voucher twice
            found = False
            for pe in self.payment_entries:
                if (
                    pe.payment_document == voucher["payment_doctype"]
                    and pe.payment_entry == voucher["payment_name"]
                ):
                    found = True

            if not found:
                logger.info(
                    "Voucher: %s being added to bank transaction %s", voucher, self.name
                )
                # An internal transfer has two bank legs, so its amount must come
                # from the GL entry for this Bank Transaction's account. Keep the
                # supplied amount for other vouchers because ABR supports signed
                # refund and mixed allocations.
                pe = {
                    "payment_document": voucher["payment_doctype"],
                    "payment_entry": voucher["payment_name"],
                    "allocated_amount": get_voucher_allocation_amount(
                        voucher, allocated_precision
                    ),
                }
                self.append("payment_entries", pe)
                added = True

        # runs on_update_after_submit
        if added:
            self.save()

    def update_allocated_amount(self):
        """
        Override of ERPNext upstream to handle signed allocations correctly.

        ABR stores allocated_amount on Bank Transaction Payments rows with sign
        preserved (negative for refunds, positive for normal payments). This is
        intentional and lets users net refunds against batched deposits in a
        single Bank Transaction. Upstream computes
            unallocated_amount = abs(W - D) - sum(allocated_amount)
        which breaks for standalone refund matches (e.g. a $31.22 deposit
        matched against a single -$31.22 refund allocation) because the sum is
        signed. We compute against abs(sum) so that:
          - All-positive allocations behave as upstream
          - Batched mixed allocations summing to BT magnitude still net to zero
          - Standalone single-sign allocations (positive OR negative) work
        self.allocated_amount stays signed (sum, not abs) so downstream consumers
        see the net as users entered it.
        """
        signed_sum = (
            sum(p.allocated_amount for p in self.payment_entries)
            if self.payment_entries
            else 0.0
        )
        bt_magnitude = abs(flt(self.withdrawal) - flt(self.deposit))
        unallocated_amount = bt_magnitude - abs(signed_sum)

        self.allocated_amount = flt(signed_sum, self.precision("allocated_amount"))
        self.unallocated_amount = flt(
            unallocated_amount, self.precision("unallocated_amount")
        )
