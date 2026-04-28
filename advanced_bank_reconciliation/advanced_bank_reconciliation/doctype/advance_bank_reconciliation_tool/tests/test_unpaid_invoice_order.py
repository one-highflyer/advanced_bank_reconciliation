# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Guards the FIFO ordering invariant on get_unpaid_si_matching_query and
get_unpaid_pi_matching_query. The matching dialog cascades partial
allocations in the order these queries return rows, so the order must
surface the oldest outstanding invoice first.

Also exercises the end-to-end pipeline through check_matching() to prove
that the sort_unpaid_invoices_by_posting_date setting actually neutralises
the amount-match rank tie-breaker that pushes matching-amount invoices to
the top of the dialog.
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	check_matching,
	get_unpaid_pi_matching_query,
	get_unpaid_si_matching_query,
)

from .fixtures import (
	TEST_CUSTOMER,
	TEST_SUPPLIER,
	create_test_bank_transaction,
	create_test_purchase_invoice,
	create_test_sales_invoice,
	setup_abr_test_data,
)


SETTINGS_DOCTYPE = "Advance Bank Reconciliation Settings"
SETTING_FIELD = "sort_unpaid_invoices_by_posting_date"


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


class TestUnpaidInvoiceFIFOToggle(FrappeTestCase):
	"""End-to-end coverage for the sort_unpaid_invoices_by_posting_date toggle.

	Drives the full check_matching() pipeline that the dialog uses. With the
	setting OFF (default), invoices whose outstanding_amount equals the bank
	transaction amount are pushed to the top by the rank tie-breaker even when
	older invoices exist. With the setting ON, all candidates share the same
	rank and the inner FIFO ORDER BY wins, surfacing the oldest invoice first.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		# Belt-and-braces: tearDown already resets the toggle, but if a test
		# crashes before tearDown runs the committed setting would leak into
		# subsequent test classes. Force it back to 0 unconditionally here so
		# this class is self-contained and order-independent.
		frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, 0)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		# Always start each test with the toggle OFF so the default-OFF
		# branch is exercised in test_default_off_surfaces_amount_match_first.
		frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, 0)
		frappe.db.commit()

	def tearDown(self):
		# Reset the toggle for any subsequent test classes that may rely on
		# the default-off behaviour.
		frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, 0)
		frappe.db.commit()
		super().tearDown()

	def _build_invoice_set(self):
		"""Three $100 invoices and one older $250 invoice, all for the same customer."""
		older_different = create_test_sales_invoice(
			outstanding=250, posting_date=add_days(nowdate(), -90)
		)
		oldest_match = create_test_sales_invoice(
			outstanding=100, posting_date=add_days(nowdate(), -60)
		)
		middle_match = create_test_sales_invoice(
			outstanding=100, posting_date=add_days(nowdate(), -30)
		)
		newest_match = create_test_sales_invoice(outstanding=100, posting_date=nowdate())
		return older_different, oldest_match, middle_match, newest_match

	def _run_check_matching(
		self,
		amount,
		party,
		currency,
		party_type="Customer",
		document_types=None,
		direction="deposit",
	):
		"""Drive check_matching() the same way the dialog does.

		direction: "deposit" for receipts (Customer / unpaid_sales_invoice) or
		"withdrawal" for payments (Supplier / unpaid_purchase_invoice). The
		distinction matters because Bank Transaction stores the amount on
		different fields and check_matching reads the right one based on
		whether deposit or withdrawal is set.
		"""
		if document_types is None:
			document_types = ["unpaid_sales_invoice"]

		kwargs = {"currency": currency}
		if direction == "withdrawal":
			kwargs["withdrawal"] = amount
		else:
			kwargs["deposit"] = amount

		bt = create_test_bank_transaction(self.bank_account, **kwargs)
		# Prime the transaction with the party and unallocated amount fields
		# that check_matching reads from.
		bt.party_type = party_type
		bt.party = party
		# unallocated_amount is set on submit but make it explicit for clarity.
		bt.unallocated_amount = amount

		gl_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
		company = frappe.db.get_value("Bank Account", self.bank_account, "company")

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

	def _names_in_order(self, matching):
		# matching is a list of tuples; column 2 is the doc name.
		return [row[2] for row in matching]

	def test_default_off_surfaces_amount_match_first(self):
		older_different, oldest_match, middle_match, newest_match = self._build_invoice_set()
		currency = oldest_match.currency

		matching = self._run_check_matching(100, TEST_CUSTOMER, currency)
		names = self._names_in_order(matching)

		# Sanity: all four invoices we created should be in the result set.
		for inv in (older_different, oldest_match, middle_match, newest_match):
			self.assertIn(inv.name, names)

		older_pos = names.index(older_different.name)
		match_positions = [
			names.index(oldest_match.name),
			names.index(middle_match.name),
			names.index(newest_match.name),
		]
		# With the setting OFF, the three $100 invoices outrank the older
		# $250 invoice because the amount-match term boosts their rank by 1.
		self.assertTrue(
			all(pos < older_pos for pos in match_positions),
			f"Expected $100 matches before older $250 invoice, got order {names}",
		)

	def test_setting_on_surfaces_oldest_invoice_first(self):
		frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, 1)
		frappe.db.commit()

		older_different, oldest_match, middle_match, newest_match = self._build_invoice_set()
		currency = oldest_match.currency

		matching = self._run_check_matching(100, TEST_CUSTOMER, currency)
		names = self._names_in_order(matching)

		for inv in (older_different, oldest_match, middle_match, newest_match):
			self.assertIn(inv.name, names)

		older_pos = names.index(older_different.name)
		match_positions = [
			names.index(oldest_match.name),
			names.index(middle_match.name),
			names.index(newest_match.name),
		]
		# With strict FIFO ON, the older $250 invoice (posting date -90d)
		# beats the three $100 matches even though their amount equals the
		# deposit. All ranks tie, so posting_date ASC wins.
		self.assertTrue(
			all(older_pos < pos for pos in match_positions),
			f"Expected older $250 invoice before $100 matches, got order {names}",
		)
		# And among the three matches themselves, FIFO is preserved.
		self.assertLess(names.index(oldest_match.name), names.index(middle_match.name))
		self.assertLess(names.index(middle_match.name), names.index(newest_match.name))

	def test_setting_on_surfaces_oldest_pi_first(self):
		"""Mirror of test_setting_on_surfaces_oldest_invoice_first for PI.

		Cheap insurance against a one-sided regression in
		get_unpaid_pi_matching_query: the FIFO toggle code path is duplicated
		across the SI and PI queries, so the PI branch needs its own
		end-to-end check_matching coverage. Only the ON case is covered;
		the toggle is symmetric so the SI OFF test already guards the
		default behaviour.
		"""
		frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, 1)
		frappe.db.commit()

		older_different = create_test_purchase_invoice(
			outstanding=250, posting_date=add_days(nowdate(), -90)
		)
		oldest_match = create_test_purchase_invoice(
			outstanding=100, posting_date=add_days(nowdate(), -60)
		)
		middle_match = create_test_purchase_invoice(
			outstanding=100, posting_date=add_days(nowdate(), -30)
		)
		newest_match = create_test_purchase_invoice(outstanding=100, posting_date=nowdate())
		currency = oldest_match.currency

		matching = self._run_check_matching(
			100,
			TEST_SUPPLIER,
			currency,
			party_type="Supplier",
			document_types=["unpaid_purchase_invoice"],
			direction="withdrawal",
		)
		names = self._names_in_order(matching)

		for inv in (older_different, oldest_match, middle_match, newest_match):
			self.assertIn(inv.name, names)

		older_pos = names.index(older_different.name)
		match_positions = [
			names.index(oldest_match.name),
			names.index(middle_match.name),
			names.index(newest_match.name),
		]
		# With strict FIFO ON, the older $250 PI (posting date -90d) beats
		# the three $100 matches even though their amount equals the
		# withdrawal. All ranks tie, so posting_date ASC wins.
		self.assertTrue(
			all(older_pos < pos for pos in match_positions),
			f"Expected older $250 PI before $100 matches, got order {names}",
		)
		# And among the three matches themselves, FIFO is preserved.
		self.assertLess(names.index(oldest_match.name), names.index(middle_match.name))
		self.assertLess(names.index(middle_match.name), names.index(newest_match.name))
