import logging

import frappe
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
        """
        Clear clearance date for different document types
        For Sales Invoice, it handles the Sales Invoice Payment child table
        For Purchase Invoice, it handles the direct clearance_date field
        """
        logger = get_logger()
        try:
            # Handle Sales Invoice - clearance date goes on Sales Invoice Payment child table
            if document_type == "Sales Invoice":
                # Load the Sales Invoice document
                sales_invoice = frappe.get_doc("Sales Invoice", document_name)
                bank_account = frappe.db.get_value(
                    "Bank Account", self.bank_account, "account"
                )

                # Iterate through payments child table and clear clearance dates
                for payment in sales_invoice.payments:
                    if payment.account == bank_account and payment.clearance_date:
                        frappe.db.set_value(
                            "Sales Invoice Payment",
                            payment.name,
                            "clearance_date",
                            None,
                        )
                        logger.info(
                            "Cleared clearance_date for Sales Invoice Payment %s",
                            payment.name,
                        )

            # Handle other document types with direct clearance_date field
            elif document_type in [
                "Payment Entry",
                "Journal Entry",
                "Purchase Invoice",
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

    def add_payment_entries(self, vouchers):
        "Add the vouchers with zero allocation. Save() will perform the allocations and clearance"
        logger = get_logger()

        if 0.0 >= self.unallocated_amount:
            frappe.throw(
                frappe._("Bank Transaction {0} is already fully reconciled").format(
                    self.name
                )
            )

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
                    "allocated_amount": voucher["amount"],
                }
                self.append("payment_entries", pe)
                added = True

        # runs on_update_after_submit
        if added:
            self.save()
