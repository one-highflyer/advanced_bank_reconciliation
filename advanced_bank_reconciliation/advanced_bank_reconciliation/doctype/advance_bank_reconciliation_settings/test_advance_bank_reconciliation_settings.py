# Copyright (c) 2025, HighFlyer and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.api.party_company import (
	get_company_link_fields,
	validate_enabled_bank_rules,
	validate_party_company_settings,
)
from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	get_abr_default_settings,
)


def field(fieldname, fieldtype="Link", options="Company", label=None):
	return frappe._dict(
		fieldname=fieldname,
		fieldtype=fieldtype,
		options=options,
		label=label or fieldname.replace("_", " ").title(),
	)


class TestAdvanceBankReconciliationSettings(FrappeTestCase):
	def test_default_settings_include_configured_navbar_logo(self):
		settings = frappe._dict(
			default_reconciliation_action="Match Against Voucher",
			default_document_type="Payment Entry",
			default_journal_entry_type="Bank Entry",
			compact_matching_vouchers_table=0,
			navbar_logo="/files/bank-rec-logo.svg",
		)
		with patch("frappe.get_single", return_value=settings):
			default_settings = get_abr_default_settings()

		self.assertEqual(default_settings["navbar_logo"], "/files/bank-rec-logo.svg")

	def test_disabled_settings_allow_blank_mappings(self):
		settings = frappe._dict(filter_parties_by_company=0)
		validate_party_company_settings(settings)

	def test_enabled_settings_require_every_mapping(self):
		settings = frappe._dict(
			filter_parties_by_company=1,
			customer_company_field="",
			supplier_company_field="supplier_scope",
			employee_company_field="company",
		)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"Configure the Customer Company Field",
		):
			validate_party_company_settings(settings)

	def test_enabled_settings_accept_company_links(self):
		settings = frappe._dict(
			filter_parties_by_company=1,
			customer_company_field="customer_scope",
			supplier_company_field="supplier_scope",
			employee_company_field="company",
		)
		metas = {
			"Customer": frappe._dict(fields=[field("customer_scope")]),
			"Supplier": frappe._dict(fields=[field("supplier_scope")]),
			"Employee": frappe._dict(fields=[field("company")]),
		}
		for meta in metas.values():
			meta.get_field = lambda fieldname, meta=meta: next(
				(row for row in meta.fields if row.fieldname == fieldname),
				None,
			)
		with patch("frappe.get_meta", side_effect=lambda doctype: metas[doctype]):
			validate_party_company_settings(settings)

	def test_non_company_link_mapping_is_rejected(self):
		settings = frappe._dict(
			filter_parties_by_company=1,
			customer_company_field="customer_scope",
			supplier_company_field="supplier_scope",
			employee_company_field="company",
		)
		meta = frappe._dict(fields=[field("customer_scope", options="Customer Group")])
		meta.get_field = lambda fieldname: next(
			(row for row in meta.fields if row.fieldname == fieldname),
			None,
		)
		with patch("frappe.get_meta", return_value=meta):
			with self.assertRaisesRegex(
				frappe.ValidationError,
				"must be a Link to Company",
			):
				validate_party_company_settings(settings)

	def test_candidate_fields_only_include_company_links(self):
		meta = frappe._dict(
			fields=[
				field("company_scope", label="Company Scope"),
				field("represents_company"),
				field("territory", options="Territory"),
				field("notes", fieldtype="Data", options=None),
			]
		)
		with (
			patch("frappe.has_permission", return_value=True),
			patch("frappe.get_meta", return_value=meta),
		):
			self.assertEqual(
				get_company_link_fields("Customer"),
				[
					{"fieldname": "company_scope", "label": "Company Scope"},
					{"fieldname": "represents_company", "label": "Represents Company"},
				],
			)

	def test_mapping_defaults_are_safe(self):
		meta = frappe.get_meta("Advance Bank Reconciliation Settings")
		self.assertEqual(meta.get_field("filter_parties_by_company").default, "0")
		self.assertFalse(meta.get_field("customer_company_field").default)
		self.assertFalse(meta.get_field("supplier_company_field").default)
		self.assertEqual(meta.get_field("employee_company_field").default, "company")

	def test_disabled_settings_skip_rule_validation(self):
		settings = frappe._dict(filter_parties_by_company=0)
		with patch("frappe.get_all") as get_all:
			validate_enabled_bank_rules(settings)
		get_all.assert_not_called()

	def test_enabled_settings_reject_ineligible_rules_without_updating_them(self):
		settings = frappe._dict(filter_parties_by_company=1)
		rules = [
			frappe._dict(
				name="Rule One",
				party_type="Customer",
				party="_Test Customer",
				company="_Test Company",
			),
			frappe._dict(
				name="Rule Two",
				party_type="Supplier",
				party="_Test Supplier",
				company="_Test Company",
			),
		]
		with (
			patch("frappe.get_all", return_value=rules),
			patch(
				"advanced_bank_reconciliation.api.party_company.is_party_eligible_for_company",
				side_effect=[False, True],
			),
			patch("frappe.db.set_value") as set_value,
		):
			with self.assertRaisesRegex(
				frappe.ValidationError,
				"Rule One.*correct or disable",
			):
				validate_enabled_bank_rules(settings)
		set_value.assert_not_called()
