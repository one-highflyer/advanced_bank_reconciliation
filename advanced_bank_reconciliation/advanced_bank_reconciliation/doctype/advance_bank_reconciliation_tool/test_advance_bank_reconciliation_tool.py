# Copyright (c) 2024, High Flyer and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	_get_je_linked_party_reference,
)


class TestAdvanceBankReconciliationTool(FrappeTestCase):
	def test_get_je_linked_party_reference_skips_bank_row_and_uses_party(self):
		party_type, party = _get_je_linked_party_reference(
			[
				{"account": "Main Bank - TC", "party_type": "", "party": ""},
				{"account": "Debtors - TC", "party_type": "Customer", "party": "CUST-0001"},
			],
			"Main Bank - TC",
		)

		self.assertEqual(party_type, "Customer")
		self.assertEqual(party, "CUST-0001")

	def test_get_je_linked_party_reference_falls_back_to_reference_name(self):
		party_type, party = _get_je_linked_party_reference(
			[
				{"account": "Main Bank - TC", "party_type": "", "party": ""},
				{
					"account": "Donations - TC",
					"party_type": "",
					"party": "",
					"reference_type": "Customer",
					"reference_name": "CUST-REF-0001",
				},
			],
			"Main Bank - TC",
		)

		self.assertEqual(party_type, "Customer")
		self.assertEqual(party, "CUST-REF-0001")
