# Copyright (c) 2025, HighFlyer and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AdvanceBankReconciliationSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		reconcile_unpaid_invoices_in_background: DF.Check
		validate_selection_against_unallocated_amount: DF.Check
	# end: auto-generated types
	pass
