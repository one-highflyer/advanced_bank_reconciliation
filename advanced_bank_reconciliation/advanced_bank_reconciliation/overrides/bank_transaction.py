import logging

import frappe
from frappe.utils import flt

from advanced_bank_reconciliation.utils.logger import (
    get_logger,
)
from erpnext.accounts.doctype.bank_transaction.bank_transaction import BankTransaction


class ExtendedBankTransaction(BankTransaction):
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
                pe = {
                    "payment_document": voucher["payment_doctype"],
                    "payment_entry": voucher["payment_name"],
                    "allocated_amount": flt(voucher["amount"], allocated_precision),
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
