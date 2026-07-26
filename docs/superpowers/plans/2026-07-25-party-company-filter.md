# Configurable Party Company Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in, explicitly mapped company policy for Customer, Supplier, and Employee selections across every Advanced Bank Reconciliation workflow.

**Architecture:** A new `api/party_company.py` module owns mapping validation, eligibility checks, and permission-aware party search. The Single settings DocType stores one explicit Company Link fieldname per supported Party Type. Legacy, modern, direct API, and bank-rule mutation paths all delegate to the same server policy, while the two frontends use the same search endpoint for suggestions.

**Tech Stack:** Frappe v15, ERPNext v15, Python 3, MariaDB, Frappe Desk JavaScript, Vue 3, TypeScript, Vite, `FrappeTestCase`.

## Global Constraints

- The feature is disabled by default, and disabled behavior remains global.
- Supported Party Types are exactly `Customer`, `Supplier`, and `Employee`.
- Customer and Supplier mappings have no default. Employee defaults to `company`.
- A configured mapping is valid only when its DocField exists, has `fieldtype == "Link"`, and has `options == "Company"`.
- Administrators select mappings explicitly. Never infer or auto-select a Customer or Supplier field.
- A party is eligible when its mapped company equals the reconciliation company or is blank/null.
- When filtering is enabled, missing or stale configuration fails closed.
- Existing documents and ABR Bank Rules are not rewritten.
- All party mutation paths remain server-authoritative and preserve existing read permissions.
- Search must retain normal Frappe read/select permissions, enabled/disabled behavior, and text matching.
- Enabling the policy is blocked when any enabled ABR Bank Rule with a party is incompatible.
- Error messages must not disclose party records before read permission is established.
- Public repository artifacts must contain no customer names, site URLs, private fieldnames, ticket identifiers, contact details, dates tied to customers, or identifying transaction data.
- Use tabs in Python files and the existing formatter conventions.
- Use `FrappeTestCase`; do not use pytest.
- Commit subjects use Conventional Commits with `fix:` so semantic-release produces a patch.
- Do not merge or deploy as part of this plan.

---

### Task 1: Settings, Metadata Validation, Eligibility, and Search

**Files:**

- Create: `advanced_bank_reconciliation/api/party_company.py`
- Create: `advanced_bank_reconciliation/api/test_party_company.py`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_settings/advance_bank_reconciliation_settings.json`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_settings/advance_bank_reconciliation_settings.py`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_settings/advance_bank_reconciliation_settings.js`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_settings/test_advance_bank_reconciliation_settings.py`

**Interfaces:**

- Produces:
  - `SUPPORTED_PARTY_TYPES: tuple[str, ...]`
  - `PARTY_COMPANY_SETTING_FIELDS: dict[str, str]`
  - `get_company_link_fields(party_type: str) -> list[dict[str, str]]`
  - `get_party_company_field(party_type: str, settings=None) -> str | None`
  - `is_party_eligible_for_company(party_type: str, party: str, company: str, settings=None) -> bool`
  - `assert_party_eligible_for_company(party_type: str, party: str, company: str, user: str | None = None, settings=None)`
  - `search_parties(doctype, txt, searchfield, start, page_len, filters) -> list[list[str]]`
  - `validate_party_company_settings(settings) -> None`
  - `validate_enabled_bank_rules(settings, limit: int = 20) -> None`
- Consumes:
  - `Advance Bank Reconciliation Settings.filter_parties_by_company`
  - `Advance Bank Reconciliation Settings.customer_company_field`
  - `Advance Bank Reconciliation Settings.supplier_company_field`
  - `Advance Bank Reconciliation Settings.employee_company_field`

- [ ] **Step 1: Add failing metadata and settings tests**

Replace the empty settings test with `FrappeTestCase` tests using generic metadata stubs:

```python
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.api.party_company import (
	get_company_link_fields,
	validate_party_company_settings,
)


def field(fieldname, fieldtype="Link", options="Company", label=None):
	return frappe._dict(
		fieldname=fieldname,
		fieldtype=fieldtype,
		options=options,
		label=label or fieldname.replace("_", " ").title(),
	)


class TestAdvanceBankReconciliationSettings(FrappeTestCase):
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
		with patch("frappe.get_meta", return_value=meta):
			self.assertEqual(
				get_company_link_fields("Customer"),
				[
					{"fieldname": "company_scope", "label": "Company Scope"},
					{"fieldname": "represents_company", "label": "Represents Company"},
				],
			)
```

Also assert the JSON schema directly:

```python
	def test_mapping_defaults_are_safe(self):
		meta = frappe.get_meta("Advance Bank Reconciliation Settings")
		self.assertEqual(meta.get_field("filter_parties_by_company").default, "0")
		self.assertFalse(meta.get_field("customer_company_field").default)
		self.assertFalse(meta.get_field("supplier_company_field").default)
		self.assertEqual(meta.get_field("employee_company_field").default, "company")
```

- [ ] **Step 2: Add failing policy and search tests**

Create `api/test_party_company.py` with table-driven tests for the exact policy:

```python
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
```

Add these explicit cases to the same class:

```python
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
```

- [ ] **Step 3: Run the focused tests and confirm they fail**

Run:

```bash
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_settings.test_advance_bank_reconciliation_settings
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_party_company
```

Expected: failures because the settings fields and `party_company` interfaces do not exist.

- [ ] **Step 4: Add the settings fields**

Add this field order after `compact_matching_vouchers_table`:

```json
"party_company_filtering_section",
"filter_parties_by_company",
"customer_company_field",
"supplier_company_field",
"employee_company_field"
```

Add the fields:

```json
{
 "fieldname": "party_company_filtering_section",
 "fieldtype": "Section Break",
 "label": "Party Company Filtering"
},
{
 "default": "0",
 "description": "Restrict Customer, Supplier, and Employee selections to the reconciliation company while allowing records with a blank company as shared.",
 "fieldname": "filter_parties_by_company",
 "fieldtype": "Check",
 "label": "Filter Parties by Company"
},
{
 "depends_on": "eval:doc.filter_parties_by_company",
 "description": "Link field on Customer that identifies the owning company.",
 "fieldname": "customer_company_field",
 "fieldtype": "Autocomplete",
 "label": "Customer Company Field",
 "mandatory_depends_on": "eval:doc.filter_parties_by_company"
},
{
 "depends_on": "eval:doc.filter_parties_by_company",
 "description": "Link field on Supplier that identifies the owning company.",
 "fieldname": "supplier_company_field",
 "fieldtype": "Autocomplete",
 "label": "Supplier Company Field",
 "mandatory_depends_on": "eval:doc.filter_parties_by_company"
},
{
 "default": "company",
 "depends_on": "eval:doc.filter_parties_by_company",
 "description": "Link field on Employee that identifies the owning company.",
 "fieldname": "employee_company_field",
 "fieldtype": "Autocomplete",
 "label": "Employee Company Field",
 "mandatory_depends_on": "eval:doc.filter_parties_by_company"
}
```

Update the generated type block with the four new field annotations without changing code outside the block.

- [ ] **Step 5: Implement the authoritative party policy**

Implement these constants and helpers in `api/party_company.py`:

```python
SUPPORTED_PARTY_TYPES = ("Customer", "Supplier", "Employee")
PARTY_COMPANY_SETTING_FIELDS = {
	"Customer": "customer_company_field",
	"Supplier": "supplier_company_field",
	"Employee": "employee_company_field",
}
```

Implementation rules:

```python
def _get_settings(settings=None):
	return settings or frappe.get_cached_doc("Advance Bank Reconciliation Settings")


def _require_supported_party_type(party_type):
	if party_type not in SUPPORTED_PARTY_TYPES:
		frappe.throw(
			_("Party Type {0} is not supported in Bank Rec.").format(party_type)
		)


def _validate_company_link_field(party_type, fieldname):
	field = frappe.get_meta(party_type).get_field(fieldname)
	if not field or field.fieldtype != "Link" or field.options != "Company":
		frappe.throw(
			_("Field {0} on {1} must be a Link to Company.").format(
				fieldname,
				party_type,
			)
		)
	return field
```

`get_party_company_field` returns `None` immediately when filtering is disabled. When enabled, it validates the corresponding configured field and throws `Configure the <Party Type> Company Field in Advance Bank Reconciliation Settings.` if blank.

`assert_party_eligible_for_company` must:

1. Validate supported type and party/type pairing.
2. Load the party document and call `frappe.has_permission(..., throw=True)`.
3. Return the document immediately when filtering is disabled.
4. Require company when filtering is enabled.
5. Read the mapped company with `frappe.get_cached_value(party_type, party, fieldname)`.
6. Return the document when the value is blank or equal to company.
7. Throw `<Party Type> <party> is not available for company <company>.` otherwise.

`is_party_eligible_for_company` applies the same mapped-field comparison without replacing the permission check in the assertion helper.

Implement `search_parties` with:

- Parsed dict filters containing `company` and optional `party_type`.
- The allowlist check before querying.
- A function-local import of `assert_company_access` to avoid a circular import with `api/permission.py`.
- `assert_company_access(company)` for every search. Filtering enabled without a company fails with `Company is required when party company filtering is enabled.`
- `frappe.get_list`, never `frappe.get_all`, so read/select and user permissions remain active.
- Standard fields `name`, title field, and metadata search fields when they are valid text-like fields.
- Standard `enabled = 1` and `disabled != 1` filters when those Check fields exist.
- Text `or_filters` for name, title field, and search fields.
- The company filter exactly `[doctype, mapped_field, "in", [company, ""]]`, which Frappe v15 coalesces to include null values.
- `start` and `page_len` pagination.
- No caching of results.

- [ ] **Step 6: Validate settings and enabled rules**

In the settings controller:

```python
def validate(self):
	validate_party_company_settings(self)
	validate_enabled_bank_rules(self)
```

`validate_party_company_settings` returns immediately when disabled. When enabled, it resolves all three mappings with the settings document passed in.

`validate_enabled_bank_rules` returns immediately when disabled. Otherwise it reads enabled rules with nonblank `party_type` and `party`, evaluates each against `rule.company` using the unsaved settings document, and rejects the save with at most 20 rule names plus an overflow count. The message must direct the administrator to correct or disable those rules. It must not update the rules.

- [ ] **Step 7: Populate safe Autocomplete choices**

In the settings client script:

```javascript
const partyCompanyFields = {
	customer_company_field: "Customer",
	supplier_company_field: "Supplier",
	employee_company_field: "Employee",
};

frappe.ui.form.on("Advance Bank Reconciliation Settings", {
	async refresh(frm) {
		for (const [fieldname, partyType] of Object.entries(partyCompanyFields)) {
			const { message = [] } = await frappe.call({
				method: "advanced_bank_reconciliation.api.party_company.get_company_link_fields",
				args: { party_type: partyType },
			});
			frm.fields_dict[fieldname].set_data(
				message.map((row) => ({
					label: `${row.label} (${row.fieldname})`,
					value: row.fieldname,
				}))
			);
		}
	},
});
```

Whitelist `get_company_link_fields` and require read permission on the settings DocType before returning metadata.

- [ ] **Step 8: Run focused tests and migrate the local test site**

Run:

```bash
bench --site demo.localhost migrate
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_settings.test_advance_bank_reconciliation_settings
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_party_company
```

Expected: all Task 1 tests pass.

- [ ] **Step 9: Commit Task 1**

```bash
git add advanced_bank_reconciliation/api/party_company.py \
  advanced_bank_reconciliation/api/test_party_company.py \
  advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_settings
git commit -m "fix: add configurable party company policy"
```

---

### Task 2: Server-Side Enforcement Across Every Mutation Path

**Files:**

- Modify: `advanced_bank_reconciliation/api/permission.py`
- Modify: `advanced_bank_reconciliation/api/create_voucher.py`
- Modify: `advanced_bank_reconciliation/api/matching.py`
- Modify: `advanced_bank_reconciliation/api/cash_coding.py`
- Modify: `advanced_bank_reconciliation/api/test_bank_rec.py`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_tool/advance_bank_reconciliation_tool.py`
- Create: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_tool/tests/test_party_company_enforcement.py`

**Interfaces:**

- Consumes:
  - `assert_party_eligible_for_company(party_type, party, company, user=None, settings=None)`
- Produces:
  - `assert_party_access(party_type=None, party=None, company=None, user=None)`
- Guarantees:
  - Every party-bearing legacy and modern mutation derives or receives the Bank Transaction company and validates before creating or saving a document.

- [ ] **Step 1: Add failing permission delegation tests**

Add to `api/test_party_company.py`:

```python
from advanced_bank_reconciliation.api.permission import assert_party_access


class TestPartyCompanyPermissionIntegration(FrappeTestCase):
	def test_assert_party_access_delegates_company_policy(self):
		doc = frappe._dict(name="_Test Customer")
		with patch(
			"advanced_bank_reconciliation.api.permission.assert_party_eligible_for_company",
			return_value=doc,
		) as assert_eligible:
			self.assertIs(
				assert_party_access(
					"Customer",
					"_Test Customer",
					company="_Test Company",
				),
				doc,
			)
		assert_eligible.assert_called_once_with(
			"Customer",
			"_Test Customer",
			"_Test Company",
			user=frappe.session.user,
		)
```

Keep the existing pairing errors for missing Party Type or Party.

- [ ] **Step 2: Add failing legacy mutation tests**

Create `tests/test_party_company_enforcement.py` with mocks that prove validation occurs before mutation:

```python
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
```

Use one `frappe.get_cached_value` call for the Bank Account account, followed by one call for the Account company. The tests must assert the rejected call never reaches `frappe.new_doc` or `get_party_account`.

- [ ] **Step 3: Add failing modern API and cash-coding tests**

Extend `api/test_bank_rec.py` with focused mocks:

```python
	def test_update_metadata_passes_transaction_company_to_party_policy(self):
		transaction = frappe._dict(
			name="_Test Bank Transaction",
			company="_Test Company",
			status="Unreconciled",
			reference_number="",
			party_type="",
			party="",
		)
		transaction.reload = lambda: None
		transaction.save = lambda: None
		transaction.as_dict = lambda: transaction
		with (
			patch(
				"advanced_bank_reconciliation.api.matching.assert_bank_transaction_access",
				return_value=transaction,
			),
			patch("advanced_bank_reconciliation.api.matching._lock_bank_transaction"),
			patch("advanced_bank_reconciliation.api.matching.assert_party_access") as assert_party,
		):
			update_transaction_metadata(
				transaction.name,
				party_type="Customer",
				party="_Test Customer",
			)
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company="_Test Company",
		)

	def test_create_voucher_passes_resolved_company_to_party_policy(self):
		transaction = frappe._dict(name="_Test Bank Transaction")
		payload = {"party_type": "Customer", "party": "_Test Customer"}
		with (
			patch("advanced_bank_reconciliation.api.create_voucher._get_company", return_value="_Test Company"),
			patch("advanced_bank_reconciliation.api.create_voucher.assert_party_access") as assert_party,
			patch("advanced_bank_reconciliation.api.create_voucher.create_payment_entry_bts", return_value=frappe._dict()),
		):
			_build_voucher(transaction, payload, allow_edit=True)
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company="_Test Company",
		)
```

For both cash-coding paths, use:

```python
	def _cash_coding_row(self):
		return {
			"bank_transaction_name": "_Test Bank Transaction",
			"party_type": "Customer",
			"party": "_Test Customer",
			"account": "Income - TC",
		}

	def _cash_coding_transaction(self):
		transaction = frappe._dict(
			name="_Test Bank Transaction",
			company="_Test Company",
			bank_account="_Test Bank Account",
			status="Unreconciled",
			unallocated_amount=10,
		)
		transaction.reload = lambda: None
		return transaction

	def test_cash_coding_preview_passes_company_to_party_policy(self):
		row = self._cash_coding_row()
		transaction = self._cash_coding_transaction()
		with (
			patch(
				"advanced_bank_reconciliation.api.cash_coding.assert_bank_transaction_access",
				return_value=transaction,
			),
			patch("advanced_bank_reconciliation.api.cash_coding.assert_company_access"),
			patch(
				"advanced_bank_reconciliation.api.cash_coding.assert_party_access",
				side_effect=frappe.ValidationError("Not available"),
			) as assert_party,
			patch("advanced_bank_reconciliation.api.cash_coding._assert_account") as assert_account,
		):
			result = preview_cash_coding([row])
		self.assertEqual(result["results"][0]["status"], "error")
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company="_Test Company",
		)
		assert_account.assert_not_called()

	def test_cash_coding_submit_rejects_before_journal_entry(self):
		row = self._cash_coding_row()
		transaction = self._cash_coding_transaction()
		with (
			patch(
				"advanced_bank_reconciliation.api.cash_coding.assert_bank_transaction_access",
				return_value=transaction,
			),
			patch("advanced_bank_reconciliation.api.cash_coding._lock_bank_transaction"),
			patch("advanced_bank_reconciliation.api.cash_coding.assert_company_access"),
			patch(
				"advanced_bank_reconciliation.api.cash_coding.assert_party_access",
				side_effect=frappe.ValidationError("Not available"),
			) as assert_party,
			patch(
				"advanced_bank_reconciliation.api.cash_coding.create_journal_entry_bts"
			) as create_journal_entry,
			patch(
				"advanced_bank_reconciliation.api.cash_coding.get_abr_default_settings",
				return_value={"default_journal_entry_type": "Bank Entry"},
			),
			patch("advanced_bank_reconciliation.api.cash_coding.frappe.db.savepoint"),
			patch("advanced_bank_reconciliation.api.cash_coding.frappe.db.rollback"),
		):
			result = submit_cash_coding([row])
		self.assertEqual(result["results"][0]["status"], "error")
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company="_Test Company",
		)
		create_journal_entry.assert_not_called()
```

Import `preview_cash_coding`, `submit_cash_coding`, `_build_voucher`, and `update_transaction_metadata` into the test module alongside its existing API imports.

- [ ] **Step 4: Run the new mutation tests and confirm they fail**

Run:

```bash
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_party_company
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.tests.test_party_company_enforcement
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec
```

Expected: failures show that company is not yet passed to the policy.

- [ ] **Step 5: Delegate `assert_party_access` to the shared policy**

Change the signature:

```python
def assert_party_access(party_type=None, party=None, company=None, user=None):
```

Retain the existing supported-type and pairing validation. For a complete pair, call:

```python
return assert_party_eligible_for_company(
	party_type,
	party,
	company,
	user=user,
)
```

Use `SUPPORTED_PARTY_TYPES` from `party_company.py` as the single allowlist source and keep `ALLOWED_PARTY_TYPES` as an alias only if unchanged callers or tests import it.

- [ ] **Step 6: Enforce the policy in legacy mutations**

For `update_bank_transaction`, load the Bank Transaction first and resolve:

```python
company = bank_transaction.company or frappe.get_cached_value(
	"Bank Account",
	bank_transaction.bank_account,
	"company",
)
assert_party_access(party_type, party, company=company)
```

For both voucher helpers:

1. Include `company` in the initial Bank Transaction field query when available.
2. Otherwise derive it from the Bank Account or bank GL Account.
3. Call `assert_party_access(party_type, party, company=company)` after company resolution and before party-account lookup, `frappe.new_doc`, or mutation.

The helpers must continue accepting no party for Journal Entries on non-receivable/payable accounts. Payment Entry still requires a complete party pair through its existing business path.

- [ ] **Step 7: Enforce the policy in modern mutations**

Pass the resolved company in:

```python
assert_party_access(
	common["party_type"],
	common["party"],
	company=company,
)
```

Apply the same form to:

- `matching.update_transaction_metadata`, using `transaction.company` or the Bank Account fallback.
- `cash_coding.preview_cash_coding`, using the already resolved row company.
- `cash_coding.submit_cash_coding`, using the already resolved row company.

Voucher draft creation is covered because it uses `_build_voucher`.

- [ ] **Step 8: Run Task 2 tests**

Run:

```bash
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_party_company
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.tests.test_party_company_enforcement
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec
```

Expected: all focused mutation tests pass, including disabled-policy regressions already covered by existing API tests.

- [ ] **Step 9: Commit Task 2**

```bash
git add advanced_bank_reconciliation/api/permission.py \
  advanced_bank_reconciliation/api/create_voucher.py \
  advanced_bank_reconciliation/api/matching.py \
  advanced_bank_reconciliation/api/cash_coding.py \
  advanced_bank_reconciliation/api/test_bank_rec.py \
  advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_tool
git commit -m "fix: enforce party company eligibility"
```

---

### Task 3: Bank Rule and Legacy Desk Filtering

**Files:**

- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule/abr_bank_rule.py`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule/abr_bank_rule.js`
- Modify: `advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule/test_abr_bank_rule.py`
- Modify: `advanced_bank_reconciliation/public/js/advance_bank_reconciliation_tool/dialog_manager.js`

**Interfaces:**

- Consumes:
  - Search query path `advanced_bank_reconciliation.api.party_company.search_parties`
  - `assert_party_access(party_type=None, party=None, company=None, user=None)`
- Produces:
  - Company-aware Dynamic Link queries on the legacy reconciliation dialog and ABR Bank Rule form.
  - Bank Rule validation and execution that cannot bypass the shared policy.

- [ ] **Step 1: Add failing Bank Rule validation and execution tests**

Extend `test_abr_bank_rule.py`:

```python
	def test_rule_party_is_validated_for_rule_company(self):
		rule = self._make_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
		)
		with patch(
			f"{ABR_MODULE}.assert_party_access",
			side_effect=frappe.ValidationError,
		) as assert_party:
			with self.assertRaises(frappe.ValidationError):
				rule.insert()
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company=TEST_COMPANY,
		)
```

Add this `_execute_rule_action` test:

```python
	def test_rule_execution_revalidates_party_company(self):
		transaction = frappe._dict(
			name="_Test Bank Transaction",
			company=TEST_COMPANY,
			reference_number="",
			date=today(),
		)
		rule = frappe._dict(
			name="ABR-RULE-TEST",
			title="Runtime Validation Rule",
			entry_type="Payment Entry",
			company=TEST_COMPANY,
			party_type="Customer",
			party="_Test Customer",
			cost_center=None,
			project=None,
		)
		with (
			patch(f"{ABR_MODULE}._get_rule_dimensions", return_value={}),
			patch(
				f"{ABR_MODULE}.assert_party_access",
				side_effect=frappe.ValidationError("Not available"),
			) as assert_party,
			patch(f"{ABR_MODULE}.create_payment_entry_bts") as create_payment_entry,
		):
			with self.assertRaises(frappe.ValidationError):
				_execute_rule_action(transaction, rule, get_test_logger())
		assert_party.assert_called_once_with(
			"Customer",
			"_Test Customer",
			company=TEST_COMPANY,
		)
		create_payment_entry.assert_not_called()
```

Import `_execute_rule_action` from the Bank Rule controller. This runtime validation protects rules whose party metadata changed after save.

- [ ] **Step 2: Run the Bank Rule tests and confirm failure**

Run:

```bash
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.test_abr_bank_rule
```

Expected: the new company-policy assertions fail.

- [ ] **Step 3: Enforce Bank Rule policy**

In `ABRBankRule.validate`, after required party checks:

```python
assert_party_access(
	self.party_type,
	self.party,
	company=self.company,
)
```

In `_execute_rule_action`, validate the party again before either Journal Entry or Payment Entry helper:

```python
assert_party_access(
	rule.party_type,
	rule.party,
	company=transaction.company or rule.company,
)
```

The voucher helpers remain a second enforcement layer.

- [ ] **Step 4: Add the shared query to the legacy reconciliation dialog**

Set the Party Dynamic Link query:

```javascript
get_query: () => ({
	query: "advanced_bank_reconciliation.api.party_company.search_parties",
	filters: {
		party_type: this.dialog.get_value("party_type"),
		company: this.company,
	},
}),
```

Add an `onchange` handler to Party Type:

```javascript
onchange: () => {
	this.dialog.set_value("party", "");
},
```

Limit the legacy Party Type choices to the three supported types instead of every `frappe.boot.party_account_types` key.

- [ ] **Step 5: Add the shared query to the ABR Bank Rule form**

In `refresh`:

```javascript
frm.set_query("party", () => ({
	query: "advanced_bank_reconciliation.api.party_company.search_parties",
	filters: {
		party_type: frm.doc.party_type,
		company: frm.doc.company,
	},
}));
```

Clear dependent values:

```javascript
company(frm) {
	for (const field of ["bank_account", "account", "cost_center", "party"]) {
		frm.set_value(field, "");
	}
},

party_type(frm) {
	frm.set_value("party", "");
},
```

- [ ] **Step 6: Syntax-check JavaScript and run Bank Rule tests**

Run:

```bash
node --check advanced_bank_reconciliation/public/js/advance_bank_reconciliation_tool/dialog_manager.js
node --check advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule/abr_bank_rule.js
bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.test_abr_bank_rule
```

Expected: syntax checks succeed and all Bank Rule tests pass.

- [ ] **Step 7: Commit Task 3**

```bash
git add advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule \
  advanced_bank_reconciliation/public/js/advance_bank_reconciliation_tool/dialog_manager.js
git commit -m "fix: filter parties in desk workflows"
```

---

### Task 4: Modern Bank Rec Party Autocomplete

**Files:**

- Create: `bank_rec/src/components/PartyAutocomplete.vue`
- Modify: `bank_rec/src/services/api.ts`
- Modify: `bank_rec/src/types/bankRec.ts`
- Modify: `bank_rec/src/components/CreateVoucherPanel.vue`
- Modify: `bank_rec/src/components/UpdateTransactionPanel.vue`
- Modify: `bank_rec/src/pages/CashCodingPage.vue`

**Interfaces:**

- Consumes:
  - `search_parties(doctype, txt, searchfield, start, page_len, filters)`
- Produces:
  - `PartySearchResult { value: string; label: string }`
  - `searchParties(params: { party_type: string; company: string; txt?: string; page_len?: number }): Promise<PartySearchResult[]>`
  - Reusable `PartyAutocomplete` with props `company`, `partyType`, `modelValue`, `label?`, `placeholder?`, and `disabled?`.

- [ ] **Step 1: Add the typed search service**

Add:

```typescript
export interface PartySearchResult {
  value: string;
  label: string;
}
```

In `api.ts`, add:

```typescript
const partyCompanyApiPath =
  "/api/method/advanced_bank_reconciliation.api.party_company.";

export async function searchParties(params: {
  party_type: string;
  company: string;
  txt?: string;
  page_len?: number;
}) {
  const rows = await call<string[][]>(partyCompanyApiPath, "search_parties", {
    doctype: params.party_type,
    txt: params.txt || "",
    searchfield: "name",
    start: 0,
    page_len: params.page_len || 20,
    filters: {
      party_type: params.party_type,
      company: params.company,
    },
  });
  return rows.map((row) => ({
    value: row[0],
    label: row[1] && row[1] !== row[0] ? `${row[1]} (${row[0]})` : row[0],
  }));
}
```

- [ ] **Step 2: Implement the reusable component**

`PartyAutocomplete.vue` must:

- Render a label when supplied, an input, a loading indicator, an error message, and a positioned result list.
- Debounce input searches by 250 ms.
- Ignore stale responses using an incrementing request id.
- Use `company`, `partyType`, and typed text in `searchParties`.
- Emit typed input as `modelValue` so direct submissions remain possible, and replace it with the selected result `value` when a result is chosen. The server remains authoritative for typed values not selected from the list.
- Close on blur after selection can complete.
- When company or Party Type changes, search the current value and retain it only if an exact result remains; otherwise emit `update:modelValue` with `""`.
- Clear results and emit `""` when Party Type or company is blank.
- Cancel the debounce timer in `onBeforeUnmount`.

Use this public shape:

```typescript
const props = withDefaults(
  defineProps<{
    company: string;
    partyType: string;
    modelValue: string;
    label?: string;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    label: "",
    placeholder: "Search parties",
    disabled: false,
  }
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();
```

Use semantic buttons for results and the existing Bank Rec border, focus, muted, and error utility classes.

- [ ] **Step 3: Replace Create and Update free-text fields**

In `CreateVoucherPanel.vue`:

```vue
<PartyAutocomplete
  v-model="party"
  :company="defaults.bank_account.company"
  :party-type="partyType"
  :label="contactLabel"
/>
```

In `UpdateTransactionPanel.vue`:

```vue
<PartyAutocomplete
  v-model="party"
  :company="transaction.company || ''"
  :party-type="partyType"
  label="Party"
/>
```

Import the component in both files. Keep existing payload and dirty-state behavior.

- [ ] **Step 4: Replace Cash Coding free-text fields**

Replace only the party text input with:

```vue
<PartyAutocomplete
  v-model="row.party"
  :company="row.transaction.company || store.selectedCompany"
  :party-type="row.party_type"
  placeholder="Party"
  @update:model-value="markDirty(row.transaction.name)"
/>
```

On Party Type change, clear `row.party` before marking the row dirty so a party from the previous DocType is never submitted.

- [ ] **Step 5: Build the modern frontend**

Run:

```bash
yarn --cwd bank_rec build
```

Expected: TypeScript and Vite build succeed with no errors.

- [ ] **Step 6: Verify all three modern call sites**

Use source checks:

```bash
rg -n "<PartyAutocomplete" \
  bank_rec/src/components/CreateVoucherPanel.vue \
  bank_rec/src/components/UpdateTransactionPanel.vue \
  bank_rec/src/pages/CashCodingPage.vue
rg -n 'v-model="party"|v-model="row.party"' \
  bank_rec/src/components/CreateVoucherPanel.vue \
  bank_rec/src/components/UpdateTransactionPanel.vue \
  bank_rec/src/pages/CashCodingPage.vue
```

Expected: exactly one `PartyAutocomplete` use at each target and no remaining free-text party input.

- [ ] **Step 7: Commit Task 4**

```bash
git add bank_rec/src
git commit -m "fix: filter parties in bank rec frontend"
```

---

### Task 5: Cross-Workflow Regression and Release Verification

**Files:**

- Modify only if a regression is found in a file already owned by Tasks 1 to 4.

**Interfaces:**

- Consumes all prior task outputs.
- Produces test evidence for server policy, mutations, rules, legacy JavaScript, and the modern production build.

- [ ] **Step 1: Run the complete app test suite**

Run:

```bash
bench --site demo.localhost run-tests --app advanced_bank_reconciliation
```

Expected: all app tests pass.

- [ ] **Step 2: Run static and frontend verification**

Run:

```bash
pre-commit run --all-files
node --check advanced_bank_reconciliation/public/js/advance_bank_reconciliation_tool/dialog_manager.js
node --check advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/abr_bank_rule/abr_bank_rule.js
yarn --cwd bank_rec build
```

Expected: every command succeeds.

- [ ] **Step 3: Verify configuration and policy behavior on the local site**

Using `bench --site demo.localhost console`, create generic test parties. If Customer or Supplier has no safe generic ownership field, create a temporary `company_scope` Custom Field with `fieldtype = "Link"` and `options = "Company"`, use it for this verification, then delete that Custom Field after restoring the settings to disabled. Verify:

1. Filtering disabled returns a permitted global party.
2. Filtering enabled with exact-company mapping returns and accepts the party.
3. A blank mapped company returns and accepts the party as shared.
4. A different mapped company does not return the party and rejects direct mutation.
5. Missing mapping fails closed.
6. An enabled incompatible ABR Bank Rule blocks settings activation.

Roll back the console transaction or delete only the generic test records created for this verification.

- [ ] **Step 4: Browser-check the four user-facing workflows**

On `demo.localhost`:

1. Open Advance Bank Reconciliation Settings and confirm each mapping Autocomplete shows only Company Link fields with label and fieldname.
2. Open legacy Bank Reconciliation, change Party Type, and confirm Party clears and searches only exact-company/shared records.
3. Open an ABR Bank Rule, change Company or Party Type, and confirm Party clears and uses the same filtered search.
4. Open modern Create, Update, and Cash Coding screens, type a party query, and confirm only exact-company/shared results render.
5. Confirm no new browser console errors.

- [ ] **Step 5: Scan the branch for public-data safety and scope**

Run:

```bash
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Run the required customer-identifier scan using the private pattern list held outside this public repository. Do not copy those identifiers into a tracked file, commit message, PR title, or PR body.

Expected: no whitespace errors, only intended files, and no customer-specific matches.

- [ ] **Step 6: Commit any verification-only fixes**

If Tasks 1 to 4 required a correction, stage only the corrected implementation and covering test, then commit:

```bash
git commit -m "fix: complete party company filtering safeguards"
```

If no correction was needed, do not create an empty commit.

- [ ] **Step 7: Prepare a merge-ready pull request**

Before creating the PR:

```bash
git status --short
git log --oneline main..HEAD
git diff --stat main...HEAD
```

Scan the full diff and proposed PR text with the private safety pattern list before pushing. Push the branch and create a PR with a generic `fix:` title. The description must include behavior, configuration defaults, test evidence, risk, and rollout steps without customer-specific context. Do not merge it.
