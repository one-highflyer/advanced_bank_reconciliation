from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.api.party_company import (
	assert_party_eligible_for_company,
	get_party_company_field,
	is_party_eligible_for_company,
	search_parties,
)


def enabled_settings():
	return frappe._dict(
		filter_parties_by_company=1,
		customer_company_field="company_scope",
		supplier_company_field="company_scope",
		employee_company_field="company",
	)


class TestPartyCompanyPolicy(FrappeTestCase):
	def test_disabled_policy_returns_no_mapping(self):
		settings = frappe._dict(filter_parties_by_company=0)
		self.assertIsNone(get_party_company_field("Customer", settings=settings))

	def test_exact_company_is_eligible(self):
		with (
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value="company_scope",
			),
			patch("frappe.get_cached_value", return_value="_Test Company"),
		):
			self.assertTrue(
				is_party_eligible_for_company(
					"Customer",
					"_Test Customer",
					"_Test Company",
					settings=enabled_settings(),
				)
			)

	def test_blank_company_is_shared(self):
		with (
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value="company_scope",
			),
			patch("frappe.get_cached_value", return_value=None),
		):
			self.assertTrue(
				is_party_eligible_for_company(
					"Supplier",
					"_Test Supplier",
					"_Test Company",
					settings=enabled_settings(),
				)
			)

	def test_other_company_is_ineligible(self):
		with (
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value="company",
			),
			patch("frappe.get_cached_value", return_value="_Test Company 1"),
		):
			self.assertFalse(
				is_party_eligible_for_company(
					"Employee",
					"_Test Employee",
					"_Test Company",
					settings=enabled_settings(),
				)
			)

	def test_assertion_checks_read_permission_before_company_error(self):
		doc = frappe._dict(name="_Test Customer")
		with (
			patch("frappe.get_doc", return_value=doc),
			patch("frappe.has_permission", side_effect=frappe.PermissionError),
			patch("frappe.get_cached_value") as get_company,
		):
			with self.assertRaises(frappe.PermissionError):
				assert_party_eligible_for_company(
					"Customer",
					doc.name,
					"_Test Company",
					settings=enabled_settings(),
				)
			get_company.assert_not_called()

	def test_enabled_policy_requires_company(self):
		doc = frappe._dict(name="_Test Customer")
		with (
			patch("frappe.get_doc", return_value=doc),
			patch("frappe.has_permission", return_value=True),
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value="company_scope",
			),
		):
			with self.assertRaisesRegex(
				frappe.ValidationError,
				"Company is required when party company filtering is enabled",
			):
				assert_party_eligible_for_company(
					"Customer",
					doc.name,
					"",
					settings=enabled_settings(),
				)

	def test_search_adds_exact_or_blank_mapping_filter(self):
		meta = frappe._dict(
			title_field="customer_name",
			search_fields="customer_name",
			translated_doctype=False,
			fields=[],
		)
		meta.get_search_fields = Mock(return_value=["customer_name"])
		meta.get_field = Mock(
			side_effect=lambda name: frappe._dict(
				fieldname=name,
				fieldtype="Data",
			)
		)
		with (
			patch("frappe.get_meta", return_value=meta),
			patch("frappe.get_list", return_value=[["_Test Customer"]]) as get_list,
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value="company_scope",
			),
			patch(
				"advanced_bank_reconciliation.api.permission.assert_company_access",
				return_value="_Test Company",
			),
			patch("frappe.db.exists", return_value=True),
		):
			result = search_parties(
				"Customer",
				"_Test",
				"name",
				0,
				20,
				{"company": "_Test Company", "party_type": "Customer"},
			)
		self.assertEqual(result, [["_Test Customer"]])
		self.assertIn(
			["Customer", "company_scope", "in", ["_Test Company", ""]],
			get_list.call_args.kwargs["filters"],
		)

	def test_search_rejects_unsupported_party_type(self):
		with patch("frappe.db.exists", return_value=True):
			with self.assertRaisesRegex(
				frappe.ValidationError,
				"Party Type Lead is not supported",
			):
				search_parties(
					"Lead",
					"",
					"name",
					0,
					20,
					{"company": "_Test Company", "party_type": "Lead"},
				)

	def test_disabled_search_has_no_company_filter(self):
		with (
			patch("frappe.get_meta") as get_meta,
			patch("frappe.get_list", return_value=[]) as get_list,
			patch(
				"advanced_bank_reconciliation.api.party_company.get_party_company_field",
				return_value=None,
			),
			patch(
				"advanced_bank_reconciliation.api.permission.assert_company_access",
				return_value="_Test Company",
			),
			patch("frappe.db.exists", return_value=True),
		):
			meta = get_meta.return_value
			meta.title_field = ""
			meta.search_fields = ""
			meta.translated_doctype = False
			meta.fields = []
			meta.get_search_fields.return_value = []
			meta.get_field.return_value = None
			search_parties(
				"Customer",
				"",
				"name",
				0,
				20,
				{"company": "_Test Company", "party_type": "Customer"},
			)
		self.assertNotIn(
			["Customer", "company_scope", "in", ["_Test Company", ""]],
			get_list.call_args.kwargs["filters"],
		)

	def test_stale_mapping_fails_closed(self):
		meta = frappe._dict(fields=[])
		meta.get_field = lambda fieldname: None
		with patch("frappe.get_meta", return_value=meta):
			with self.assertRaisesRegex(
				frappe.ValidationError,
				"must be a Link to Company",
			):
				get_party_company_field("Customer", settings=enabled_settings())

	def test_each_supported_party_type_uses_its_mapping(self):
		settings = enabled_settings()
		expected = {
			"Customer": "company_scope",
			"Supplier": "company_scope",
			"Employee": "company",
		}
		meta = frappe._dict()
		meta.get_field = lambda fieldname: frappe._dict(
			fieldname=fieldname,
			fieldtype="Link",
			options="Company",
		)
		with patch("frappe.get_meta", return_value=meta):
			for party_type, fieldname in expected.items():
				with self.subTest(party_type=party_type):
					self.assertEqual(
						get_party_company_field(
							party_type,
							settings=settings,
						),
						fieldname,
					)
