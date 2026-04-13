# Copyright (c) 2024, HighFlyer and contributors
# For license information, please see license.txt
"""Guards the FIFO ordering invariant on get_unpaid_si_matching_query and
get_unpaid_pi_matching_query. The matching dialog cascades partial
allocations in the order these queries return rows, so the order must
surface the oldest outstanding invoice first.
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	get_unpaid_pi_matching_query,
	get_unpaid_si_matching_query,
)

from .fixtures import (
	TEST_CUSTOMER,
	TEST_SUPPLIER,
	create_test_purchase_invoice,
	create_test_sales_invoice,
	setup_abr_test_data,
)


class TestUnpaidInvoiceFIFOOrder(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_abr_test_data()
		frappe.db.commit()

	def _run_query(self, query, party, currency):
		return frappe.db.sql(
			query,
			{
				"party": party,
				"amount": 0,
				"currency": currency,
				"from_date": None,
				"to_date": None,
			},
		)

	def test_unpaid_sales_invoices_returned_oldest_first(self):
		oldest = create_test_sales_invoice(outstanding=100, posting_date=add_days(nowdate(), -60))
		middle = create_test_sales_invoice(outstanding=100, posting_date=add_days(nowdate(), -30))
		newest = create_test_sales_invoice(outstanding=100, posting_date=nowdate())

		currency = oldest.currency
		rows = self._run_query(
			get_unpaid_si_matching_query(exact_match=False),
			TEST_CUSTOMER,
			currency,
		)
		names = [r[2] for r in rows]
		pos = {n: names.index(n) for n in (oldest.name, middle.name, newest.name) if n in names}
		self.assertLess(pos[oldest.name], pos[middle.name])
		self.assertLess(pos[middle.name], pos[newest.name])

	def test_unpaid_purchase_invoices_returned_oldest_first(self):
		oldest = create_test_purchase_invoice(outstanding=100, posting_date=add_days(nowdate(), -45))
		middle = create_test_purchase_invoice(outstanding=100, posting_date=add_days(nowdate(), -20))
		newest = create_test_purchase_invoice(outstanding=100, posting_date=nowdate())

		currency = oldest.currency
		rows = self._run_query(
			get_unpaid_pi_matching_query(exact_match=False, for_deposit=False),
			TEST_SUPPLIER,
			currency,
		)
		names = [r[2] for r in rows]
		pos = {n: names.index(n) for n in (oldest.name, middle.name, newest.name) if n in names}
		self.assertLess(pos[oldest.name], pos[middle.name])
		self.assertLess(pos[middle.name], pos[newest.name])
