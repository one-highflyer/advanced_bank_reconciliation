# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Regression tests for company-scoped unpaid-invoice matching.

On multi-company sites the voucher-matching dialog must only return unpaid
Sales Invoices and unpaid Purchase Invoices that belong to the company
owning the bank account being reconciled. These tests verify:

  - Company B invoices do NOT surface when reconciling Company A's bank
    account (the bug that was fixed).
  - Company A invoices DO surface when reconciling Company A's bank account
    (happy-path regression guard).
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	check_matching,
)

from .fixtures import (
	TEST_COMPANY,
	TEST_COMPANY_2,
	TEST_CUSTOMER,
	TEST_SUPPLIER,
	create_test_bank_transaction,
	create_test_purchase_invoice,
	create_test_sales_invoice,
	ensure_bank_account_for_company,
	setup_abr_test_data,
)


class TestCompanyIsolation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Set up Company A (primary): bank account, customer, supplier, item
		cls.bank_account_a = setup_abr_test_data(company=TEST_COMPANY)
		# Set up Company B: only the bank infrastructure is needed; customer,
		# supplier, and item are shared across companies in ERPNext
		cls.bank_account_b = ensure_bank_account_for_company(TEST_COMPANY_2)
		frappe.db.commit()

	def _run_check_matching(self, bank_account, amount, direction, document_types):
		"""Run check_matching() the same way the reconciliation dialog does."""
		kwargs = {}
		if direction == "deposit":
			kwargs["deposit"] = amount
		else:
			kwargs["withdrawal"] = amount

		bt = create_test_bank_transaction(bank_account, **kwargs)
		bt.party_type = "Customer" if direction == "deposit" else "Supplier"
		bt.party = TEST_CUSTOMER if direction == "deposit" else TEST_SUPPLIER
		bt.unallocated_amount = amount

		gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
		company = frappe.db.get_value("Bank Account", bank_account, "company")

		return check_matching(
			gl_account,
			company,
			bt,
			document_types,
			from_date=None,
			to_date=None,
			filter_by_reference_date=None,
			from_reference_date=None,
			to_reference_date=None,
		)

	def _invoice_names(self, matching):
		return [row[2] for row in matching]

	# --- isolation tests (the bug) ---

	def test_unpaid_pi_company_isolation(self):
		"""Unpaid PI from Company B must not appear when reconciling Company A's bank account."""
		pi_company_a = create_test_purchase_invoice(outstanding=200.0, company=TEST_COMPANY)
		pi_company_b = create_test_purchase_invoice(outstanding=200.0, company=TEST_COMPANY_2)

		matching = self._run_check_matching(
			self.bank_account_a,
			amount=200.0,
			direction="withdrawal",
			document_types=["unpaid_purchase_invoice"],
		)
		names = self._invoice_names(matching)

		self.assertIn(pi_company_a.name, names, "Company A PI should be in results")
		self.assertNotIn(pi_company_b.name, names, "Company B PI must not appear for Company A reconciliation")

	def test_unpaid_si_company_isolation(self):
		"""Unpaid SI from Company B must not appear when reconciling Company A's bank account."""
		si_company_a = create_test_sales_invoice(outstanding=200.0, company=TEST_COMPANY)
		si_company_b = create_test_sales_invoice(outstanding=200.0, company=TEST_COMPANY_2)

		matching = self._run_check_matching(
			self.bank_account_a,
			amount=200.0,
			direction="deposit",
			document_types=["unpaid_sales_invoice"],
		)
		names = self._invoice_names(matching)

		self.assertIn(si_company_a.name, names, "Company A SI should be in results")
		self.assertNotIn(si_company_b.name, names, "Company B SI must not appear for Company A reconciliation")

	# --- happy-path regression guards ---

	def test_unpaid_pi_same_company_still_matches(self):
		"""Unpaid PI belonging to Company A is returned when reconciling Company A's bank account."""
		pi = create_test_purchase_invoice(outstanding=175.0, company=TEST_COMPANY)

		matching = self._run_check_matching(
			self.bank_account_a,
			amount=175.0,
			direction="withdrawal",
			document_types=["unpaid_purchase_invoice"],
		)
		names = self._invoice_names(matching)

		self.assertIn(pi.name, names, "Company A PI must appear for Company A reconciliation")

	def test_unpaid_si_same_company_still_matches(self):
		"""Unpaid SI belonging to Company A is returned when reconciling Company A's bank account."""
		si = create_test_sales_invoice(outstanding=175.0, company=TEST_COMPANY)

		matching = self._run_check_matching(
			self.bank_account_a,
			amount=175.0,
			direction="deposit",
			document_types=["unpaid_sales_invoice"],
		)
		names = self._invoice_names(matching)

		self.assertIn(si.name, names, "Company A SI must appear for Company A reconciliation")
