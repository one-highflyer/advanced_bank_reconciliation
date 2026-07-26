# Copyright (c) 2025, HighFlyer and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from advanced_bank_reconciliation.api.party_company import (
	validate_enabled_bank_rules,
	validate_party_company_settings,
)


class AdvanceBankReconciliationSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer_company_field: DF.Autocomplete | None
		employee_company_field: DF.Autocomplete | None
		filter_parties_by_company: DF.Check
		reconcile_unpaid_invoices_in_background: DF.Check
		supplier_company_field: DF.Autocomplete | None
		validate_selection_against_unallocated_amount: DF.Check
	# end: auto-generated types

	def validate(self):
		validate_party_company_settings(self)
		validate_enabled_bank_rules(self)
