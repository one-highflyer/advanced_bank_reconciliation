# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Regression test for Bank Transactions with no reference_number or description.

Bank statement imports can produce rows where both `reference_number` and
`description` are empty. ERPNext's Payment Entry validation rejects a
Bank-type PE with no `reference_no`, so the whole bulk reconcile run
previously aborted with a generic "No payment entries were created"
message. We now fall back to the Bank Transaction name so the PE always
has a stable, meaningful reference.
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_payment_entry_for_invoice,
)

from .fixtures import (
	TEST_COMPANY,
	create_test_bank_transaction,
	create_test_sales_invoice,
	setup_abr_test_data,
)


def _create_bare_bank_transaction(bank_account, deposit=0, withdrawal=0, reference_number="", description=""):
	"""Create a Bank Transaction without the fixture's default reference_number
	fallback. The fixture coerces empty strings to "_ABR-REF" via `or`, which
	would defeat the point of these tests.
	"""
	gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
	account_currency = frappe.db.get_value("Account", gl_account, "account_currency")

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"date": nowdate(),
			"bank_account": bank_account,
			"deposit": flt(deposit),
			"withdrawal": flt(withdrawal),
			"reference_number": reference_number,
			"description": description,
			"currency": account_currency,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


class TestBankTxnReferenceFallback(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(TEST_COMPANY)
		frappe.db.commit()

	def test_fallback_to_bank_transaction_name_when_reference_and_description_empty(self):
		"""A BT with both reference_number and description empty must still
		produce a valid PE. The fallback is the Bank Transaction name so
		the PE remains traceable back to its source.
		"""
		si = create_test_sales_invoice(outstanding=500)
		bt = _create_bare_bank_transaction(
			self.bank_account,
			deposit=500,
			reference_number="",
			description="",
		)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=500,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		self.assertEqual(pe.reference_no, bt.name)

	def test_reference_number_preferred_over_description_and_name(self):
		si = create_test_sales_invoice(outstanding=500)
		bt = create_test_bank_transaction(
			self.bank_account,
			deposit=500,
			reference_number="REF-123",
			description="Some description",
		)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=500,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		self.assertEqual(pe.reference_no, "REF-123")

	def test_description_used_when_reference_number_empty(self):
		si = create_test_sales_invoice(outstanding=500)
		bt = _create_bare_bank_transaction(
			self.bank_account,
			deposit=500,
			reference_number="",
			description="Stable description",
		)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=500,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		self.assertEqual(pe.reference_no, "Stable description")
