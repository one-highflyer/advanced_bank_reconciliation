from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_journal_entry_bts,
	create_payment_entry_bts,
	update_bank_transaction,
)

MODULE = (
	"advanced_bank_reconciliation.advanced_bank_reconciliation.doctype."
	"advance_bank_reconciliation_tool.advance_bank_reconciliation_tool"
)


class TestLegacyPartyCompanyEnforcement(FrappeTestCase):
	def test_update_validates_against_transaction_company(self):
		transaction = frappe._dict(
			name="_Test Bank Transaction",
			company="_Test Company",
			reference_number="",
			party_type="",
			party="",
		)
		transaction.save = lambda: None
		with (
			patch(f"{MODULE}.frappe.get_doc", return_value=transaction),
			patch(f"{MODULE}.assert_party_access") as assert_party,
			patch(f"{MODULE}.frappe.db.get_all", return_value=[transaction]),
		):
			update_bank_transaction(
				transaction.name,
				"REF",
				"Customer",
				"_Test Customer",
			)
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company="_Test Company",
		)

	def test_journal_entry_rejects_before_new_document(self):
		with (
			patch(
				f"{MODULE}.frappe.db.get_values",
				return_value=[
					frappe._dict(
						name="_Test Bank Transaction",
						deposit=10,
						withdrawal=0,
						bank_account="_Test Bank Account",
						currency="NZD",
						unallocated_amount=10,
					)
				],
			),
			patch(f"{MODULE}.frappe.get_value", side_effect=["Bank - TC", "_Test Company"]),
			patch(f"{MODULE}.frappe.db.get_value", return_value="Income"),
			patch(f"{MODULE}.assert_party_access", side_effect=frappe.ValidationError),
			patch(f"{MODULE}.frappe.new_doc") as new_doc,
		):
			with self.assertRaises(frappe.ValidationError):
				create_journal_entry_bts(
					"_Test Bank Transaction",
					entry_type="Bank Entry",
					second_account="Income - TC",
					party_type="Customer",
					party="_Test Customer",
				)
		new_doc.assert_not_called()

	def test_payment_entry_rejects_before_party_account_lookup(self):
		with (
			patch(
				f"{MODULE}.frappe.db.get_values",
				return_value=[
					frappe._dict(
						name="_Test Bank Transaction",
						deposit=10,
						bank_account="_Test Bank Account",
						currency="NZD",
						unallocated_amount=10,
					)
				],
			),
			patch(f"{MODULE}.frappe.get_cached_value", side_effect=["Bank - TC", "_Test Company"]),
			patch(f"{MODULE}.assert_party_access", side_effect=frappe.ValidationError),
			patch("erpnext.accounts.party.get_party_account") as get_party_account,
		):
			with self.assertRaises(frappe.ValidationError):
				create_payment_entry_bts(
					"_Test Bank Transaction",
					party_type="Supplier",
					party="_Test Supplier",
				)
		get_party_account.assert_not_called()
