import frappe
import logging
from erpnext.accounts.doctype.bank_transaction.bank_transaction import BankTransaction

logger = frappe.logger("bank_rec")
logger.setLevel(logging.INFO)


class ExtendedBankTransaction(BankTransaction):

		def before_update_after_submit(self):
				super().before_update_after_submit()
				logger.info(f"before_update_after_submit: {self.name}")
				# Fetch the current state of the document from the database
				existing_doc = frappe.get_doc(self.doctype, self.name)
				# Store the current state of the child table
				self._previous_payments = existing_doc.get("payment_entries")

		def on_update_after_submit(self):
				logger.info(f"on_update_after_submit: {self.name}")
				logger.info(
						f"self.payment_entries: {self.payment_entries} vs {self._previous_payments}"
				)
				self.process_removed_payment_entries()
				
				# Trigger background validation if payment entries were added or modified
				if self.payment_entries and len(self.payment_entries) > 0:
					self.trigger_background_validation()

		def process_removed_payment_entries(self):
				for previous_payment in self._previous_payments:
						removed = True
						for payment_entry in self.payment_entries:
								if (
										payment_entry.payment_document == previous_payment.payment_document
										and payment_entry.payment_entry == previous_payment.payment_entry
								):
										removed = False
										break
						# If the payment entry was removed, we need to clear the clearance date
						if removed:
								logger.info(
										f"Payment entry {previous_payment.payment_document} {previous_payment.payment_entry} was removed from the bank transaction {self.name}. Clearing the clearance date."
								)
								if previous_payment.payment_document == "Payment Entry":
									frappe.db.set_value(
											"Payment Entry",
											previous_payment.payment_entry,
											"clearance_date",
											None,
									)
								elif previous_payment.payment_document == "Journal Entry":
									frappe.db.set_value(
											"Journal Entry",
											previous_payment.payment_entry,
											"clearance_date",
											None,
									)

		def trigger_background_validation(self):
				"""
				Trigger background validation for this bank transaction
				"""
				try:
					logger.info(f"Triggering background validation for bank transaction {self.name}")
					
					# Import the validation function
					from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import validate_bank_transaction_async
					
					# Call the async validation function
					result = validate_bank_transaction_async(self.name)
					
					if result.get("success"):
						logger.info(f"Successfully queued validation for bank transaction {self.name}")
					else:
						logger.error(f"Failed to queue validation for bank transaction {self.name}: {result.get('error')}")
						
				except Exception as e:
					logger.error(f"Error triggering background validation for bank transaction {self.name}: {str(e)}")
					# Don't raise the exception as we don't want to break the main transaction flow

		def add_payment_entries(self, vouchers):
				"Add the vouchers with zero allocation. Save() will perform the allocations and clearance"
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

						print(f"Voucher: {voucher}")
						if not found:
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
