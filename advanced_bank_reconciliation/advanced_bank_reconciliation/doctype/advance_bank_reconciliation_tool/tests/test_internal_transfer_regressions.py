import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	get_linked_payments,
	get_pe_matching_query,
	reconcile_vouchers,
)
from advanced_bank_reconciliation.utils.internal_transfer import (
	get_internal_transfer_clearance_date,
)

from .fixtures import (
	TEST_COMPANY,
	create_test_bank_transaction,
	ensure_bank_and_bank_account,
	ensure_bank_account_for_company,
	ensure_erpnext_test_company,
	ensure_fiscal_year_for_company,
)


TOOL_MODULE = (
	"advanced_bank_reconciliation.advanced_bank_reconciliation.doctype."
	"advance_bank_reconciliation_tool.advance_bank_reconciliation_tool"
)


class TestInternalTransferRegressions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_erpnext_test_company()
		ensure_fiscal_year_for_company(TEST_COMPANY)
		cls.source_bank_account = ensure_bank_and_bank_account(TEST_COMPANY)
		cls.target_bank_account = ensure_bank_account_for_company(TEST_COMPANY)
		cls.source_gl_account = frappe.db.get_value(
			"Bank Account", cls.source_bank_account, "account"
		)
		cls.target_gl_account = frappe.db.get_value(
			"Bank Account", cls.target_bank_account, "account"
		)
		frappe.db.commit()

	def test_exact_match_uses_remaining_bank_leg_amount(self):
		transaction = SimpleNamespace(
			bank_account="Source Bank Account",
			unallocated_amount=60,
			precision=lambda fieldname: 2,
		)
		voucher = (
			2,
			"Payment Entry",
			"PE-PARTIAL-TRANSFER",
			100,
			"REF",
			getdate("2026-09-10"),
			None,
			None,
			getdate("2026-09-10"),
			"NZD",
			None,
			1,
		)

		with (
			patch(f"{TOOL_MODULE}.frappe.get_doc", return_value=transaction),
			patch(
				f"{TOOL_MODULE}.frappe.db.get_values",
				return_value=[frappe._dict(account="Source Bank", company="Test Company")],
			),
			patch(f"{TOOL_MODULE}.check_matching", return_value=[voucher]),
			patch(
				f"{TOOL_MODULE}.get_total_allocated_amount",
				return_value={
					("Payment Entry", "PE-PARTIAL-TRANSFER"): {
						"Source Bank": {"total": 40}
					}
				},
			),
		):
			matches = get_linked_payments(
				"BT-EXACT-REMAINDER",
				["payment_entry", "exact_match"],
				"2026-09-01",
				"2026-09-30",
				False,
				None,
				None,
			)
			transaction.unallocated_amount = 50
			non_matches = get_linked_payments(
				"BT-NONMATCHING-REMAINDER",
				["payment_entry", "exact_match"],
				"2026-09-01",
				"2026-09-30",
				False,
				None,
				None,
			)

		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0][3], 60)
		self.assertEqual(non_matches, [])

	def test_exact_match_finds_actual_partially_allocated_transfer_leg(self):
		payment_entry = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Internal Transfer",
				"company": TEST_COMPANY,
				"posting_date": nowdate(),
				"paid_from": self.source_gl_account,
				"paid_to": self.target_gl_account,
				"paid_amount": 100,
				"received_amount": 100,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"reference_no": "_ABR-EXACT-PARTIAL",
				"reference_date": nowdate(),
			}
		).insert(ignore_permissions=True)
		payment_entry.submit()
		first_transaction = create_test_bank_transaction(
			self.source_bank_account,
			withdrawal=40,
			date=nowdate(),
		)
		reconcile_vouchers(
			first_transaction.name,
			json.dumps(
				[
					{
						"payment_doctype": "Payment Entry",
						"payment_name": payment_entry.name,
						"amount": 40,
					}
				]
			),
		)
		remaining_transaction = create_test_bank_transaction(
			self.source_bank_account,
			withdrawal=60,
			date=nowdate(),
		)

		matches = get_linked_payments(
			remaining_transaction.name,
			["payment_entry", "exact_match"],
			add_days(nowdate(), -1),
			add_days(nowdate(), 1),
			False,
			None,
			None,
		)
		candidate = next(row for row in matches if row[2] == payment_entry.name)

		self.assertEqual(candidate[3], 60)
		self.assertEqual(candidate[11], 1)

	def test_exact_query_keeps_only_directional_internal_transfer_candidates(self):
		for deposit, expected_side in ((100, "paid_to"), (0, "paid_from")):
			with self.subTest(expected_side=expected_side):
				transaction = SimpleNamespace(
					deposit=deposit,
					withdrawal=0 if deposit else 100,
					reference_number="REF",
				)
				query = get_pe_matching_query(
					True,
					expected_side,
					transaction,
					"2026-09-01",
					"2026-09-30",
					False,
					None,
					None,
				)

				self.assertIn(
					f"payment_type = 'Internal Transfer' AND {expected_side} = %(bank_account)s",
					query,
				)
				self.assertIn(
					"(payment_type = 'Internal Transfer') AS is_internal_transfer",
					query,
				)

	def test_clearance_date_uses_latest_linked_bank_transaction(self):
		with patch(
			"advanced_bank_reconciliation.utils.internal_transfer.frappe.db.sql",
			return_value=[[getdate("2026-09-20")]],
		):
			clearance_date = get_internal_transfer_clearance_date(
				"PE-CROSS-LEG",
				current_date="2026-09-10",
			)

		self.assertEqual(clearance_date, getdate("2026-09-20"))

	def test_clearance_date_keeps_later_current_transaction(self):
		with patch(
			"advanced_bank_reconciliation.utils.internal_transfer.frappe.db.sql",
			return_value=[[getdate("2026-09-10")]],
		):
			clearance_date = get_internal_transfer_clearance_date(
				"PE-CROSS-LEG",
				current_date="2026-09-20",
			)

		self.assertEqual(clearance_date, getdate("2026-09-20"))

	def test_cross_leg_clearance_is_independent_of_reconciliation_order(self):
		payment_entry = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Internal Transfer",
				"company": TEST_COMPANY,
				"posting_date": nowdate(),
				"paid_from": self.source_gl_account,
				"paid_to": self.target_gl_account,
				"paid_amount": 50,
				"received_amount": 50,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"reference_no": "_ABR-CLEARANCE-ORDER",
				"reference_date": nowdate(),
			}
		).insert(ignore_permissions=True)
		payment_entry.submit()

		later_date = getdate(nowdate())
		earlier_date = add_days(later_date, -10)
		target_transaction = create_test_bank_transaction(
			self.target_bank_account,
			deposit=50,
			date=later_date,
		)
		source_transaction = create_test_bank_transaction(
			self.source_bank_account,
			withdrawal=50,
			date=earlier_date,
		)
		voucher = json.dumps(
			[
				{
					"payment_doctype": "Payment Entry",
					"payment_name": payment_entry.name,
					"amount": 50,
				}
			]
		)

		reconcile_vouchers(target_transaction.name, voucher)
		payment_entry.reload()
		self.assertFalse(payment_entry.clearance_date)

		reconcile_vouchers(source_transaction.name, voucher)
		payment_entry.reload()

		self.assertEqual(payment_entry.clearance_date, later_date)
