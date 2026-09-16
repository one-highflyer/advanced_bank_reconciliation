# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.api.matching import (
	_normalise_vouchers,
	_resolve_internal_transfer_amounts,
	_submit_match,
)


MATCHING_MODULE = "advanced_bank_reconciliation.api.matching"
ALLOCATION_MODULE = "advanced_bank_reconciliation.advanced_bank_reconciliation.overrides.bank_transaction"


class TestMatchingInternalTransferGuards(FrappeTestCase):
	def test_normalise_vouchers_rejects_duplicate_selection(self):
		voucher = {
			"voucher_type": "Payment Entry",
			"voucher_name": "ACC-PAY-TEST",
			"amount": 100,
		}

		with self.assertRaisesRegex(
			frappe.ValidationError, "cannot be selected more than once"
		):
			_normalise_vouchers([voucher, dict(voucher)])

	def test_submit_match_rejects_draft_transaction_before_locking(self):
		transaction = SimpleNamespace(
			name="ACC-BTN-DRAFT",
			docstatus=0,
		)

		with (
			patch(f"{MATCHING_MODULE}.require_bank_rec_permission"),
			patch(
				f"{MATCHING_MODULE}.assert_bank_transaction_access",
				return_value=transaction,
			),
			patch(f"{MATCHING_MODULE}._lock_bank_transaction") as lock_transaction,
			self.assertRaisesRegex(
				frappe.ValidationError, "Only submitted bank transactions"
			),
		):
			_submit_match(transaction.name, [])

		lock_transaction.assert_not_called()

	def test_transfer_reservation_uses_rounded_ordinary_amount(self):
		transaction = SimpleNamespace(
			unallocated_amount=100,
			bank_account="_Test Bank Account",
			deposit=0,
			docstatus=1,
			get=lambda field, default: default,
			precision=Mock(return_value=2),
		)
		transfer = frappe._dict(
			doctype="Payment Entry",
			name="ACC-PAY-TRANSFER",
			payment_type="Internal Transfer",
			docstatus=1,
			paid_from="Bank - _TC",
		)
		journal = frappe._dict(
			doctype="Journal Entry",
			name="ACC-JV-TEST",
		)
		vouchers = [
			{
				"payment_doctype": "Payment Entry",
				"payment_name": transfer.name,
				"amount": 999,
				"source_type": "Payment Entry",
			},
			{
				"payment_doctype": "Journal Entry",
				"payment_name": journal.name,
				"amount": 20.004,
				"source_type": "Journal Entry",
			},
		]
		docs = {transfer.name: transfer, journal.name: journal}

		with (
			patch("frappe.get_doc", side_effect=lambda _doctype, name: docs[name]),
			patch(
				f"{MATCHING_MODULE}.assert_voucher_access",
				side_effect=lambda _doctype, name: docs[name],
			),
			patch(f"{ALLOCATION_MODULE}.get_related_bank_gl_entries", return_value={}) as gl_entries,
			patch(f"{ALLOCATION_MODULE}.get_total_allocated_amount", return_value={}) as allocations,
			patch("frappe.get_system_settings", return_value="Banker's Rounding"),
			patch("frappe.db.get_value", return_value="Bank - _TC"),
			patch(
				f"{ALLOCATION_MODULE}.get_clearance_details",
				return_value=(100, False, None),
			),
		):
			_resolve_internal_transfer_amounts(transaction, vouchers)

		self.assertEqual(vouchers[1]["amount"], 20)
		self.assertEqual(vouchers[0]["amount"], 80)
		gl_entries.assert_called_once()
		allocations.assert_called_once()
		transaction.precision.assert_called_with(
			"allocated_amount", "payment_entries"
		)

	def test_transfer_reservation_rejects_amount_rounded_to_zero(self):
		transaction = SimpleNamespace(
			unallocated_amount=100,
			bank_account="_Test Bank Account",
			deposit=0,
			docstatus=1,
			get=lambda field, default: default,
			precision=Mock(return_value=2),
		)
		transfer = frappe._dict(
			doctype="Payment Entry",
			name="ACC-PAY-TRANSFER",
			payment_type="Internal Transfer",
			docstatus=1,
			paid_from="Bank - _TC",
		)
		vouchers = [
			{
				"payment_doctype": "Payment Entry",
				"payment_name": transfer.name,
				"amount": 1,
				"source_type": "Payment Entry",
			}
		]

		with (
			patch("frappe.get_doc", return_value=transfer),
			patch(
				f"{MATCHING_MODULE}.assert_voucher_access",
				return_value=transfer,
			),
			patch(f"{ALLOCATION_MODULE}.get_related_bank_gl_entries", return_value={}),
			patch(f"{ALLOCATION_MODULE}.get_total_allocated_amount", return_value={}),
			patch("frappe.get_system_settings", return_value="Banker's Rounding"),
			patch("frappe.db.get_value", return_value="Bank - _TC"),
			patch(
				f"{ALLOCATION_MODULE}.get_clearance_details",
				return_value=(0.004, False, None),
			),
			self.assertRaisesRegex(
				frappe.ValidationError, "No amount remains to allocate"
			),
		):
			_resolve_internal_transfer_amounts(transaction, vouchers)
