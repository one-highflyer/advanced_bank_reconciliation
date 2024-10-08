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
								frappe.db.set_value(
										previous_payment.doctype,
										previous_payment.name,
										"clearance_date",
										None,
								)

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
