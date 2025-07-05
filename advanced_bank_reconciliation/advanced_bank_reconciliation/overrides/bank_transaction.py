import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import logger, getdate
import json


class BankTransaction(Document):
	def on_update_after_submit(self):
		# Call parent's on_update_after_submit if it exists
		try:
			super().on_update_after_submit()
		except AttributeError:
			pass
		
		# Trigger background validation when bank transaction is updated
		self.trigger_background_validation()
	
	def trigger_background_validation(self):
		"""Trigger background validation when bank transaction is updated with payment entries"""
		try:
			# Only trigger validation if this transaction has payment entries
			if self.payment_entries:
				frappe.enqueue(
					"advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.validate_bank_transaction_async",
					bank_transaction_name=self.name,
					queue='long',
					timeout=300,
					job_name="validate_bank_transaction_%s" % self.name
				)
				logger.info("Triggered background validation for bank transaction %s", self.name)
		except Exception as e:
			logger.error("Failed to trigger background validation for bank transaction %s: %s", self.name, str(e), exc_info=True)
	
	def process_removed_payment_entries(self):
		"""Process any payment entries that were removed from the bank transaction"""
		try:
			# Get the previous document state
			if hasattr(self, '_doc_before_save'):
				previous_payments = self._doc_before_save.get('payment_entries', [])
				current_payments = self.payment_entries or []
				
				# Find removed payments
				current_payment_keys = {(p.payment_document, p.payment_entry) for p in current_payments}
				removed_payments = [p for p in previous_payments if (p.payment_document, p.payment_entry) not in current_payment_keys]
				
				# Clear clearance dates for removed payments
				for previous_payment in removed_payments:
					self.clear_document_clearance_date(previous_payment.payment_document, previous_payment.payment_entry)
		except Exception as e:
			logger.error("Error processing removed payment entries for bank transaction %s: %s", self.name, str(e), exc_info=True)

	def clear_document_clearance_date(self, document_type, document_name):
		"""
		Clear clearance date for different document types
		For Sales Invoice, it handles the Sales Invoice Payment child table
		For Purchase Invoice, it handles the direct clearance_date field
		"""
		try:
			# Handle Sales Invoice - clearance date goes on Sales Invoice Payment child table
			if document_type == "Sales Invoice":
				# Load the Sales Invoice document
				sales_invoice = frappe.get_doc("Sales Invoice", document_name)
				bank_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
				
				# Iterate through payments child table and clear clearance dates
				for payment in sales_invoice.payments:
					if payment.account == bank_account and payment.clearance_date:
						frappe.db.set_value("Sales Invoice Payment", payment.name, "clearance_date", None)
						logger.info("Cleared clearance_date for Sales Invoice Payment %s", payment.name)
			
			# Handle other document types with direct clearance_date field
			elif document_type in ["Payment Entry", "Journal Entry", "Purchase Invoice"]:
				# Check if the document exists and has clearance_date field
				if frappe.db.exists(document_type, document_name):
					# Get the meta to check if clearance_date field exists
					meta = frappe.get_meta(document_type)
					if meta.has_field("clearance_date"):
						frappe.db.set_value(document_type, document_name, "clearance_date", None)
						logger.info("Cleared clearance_date for %s %s", document_type, document_name)
					else:
						logger.debug("%s does not have clearance_date field", document_type)
			else:
				logger.debug("Document type %s not supported for clearance date clearing", document_type)
				
		except Exception as e:
			logger.error("Error clearing clearance date for %s %s: %s", document_type, document_name, str(e), exc_info=True)