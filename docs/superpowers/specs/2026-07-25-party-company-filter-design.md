# Configurable Party Company Filtering

## Summary

Advanced Bank Reconciliation currently treats Customer, Supplier, and Employee
as global parties. On a multi-company site, a user can therefore select a party
associated with a different company while reconciling a bank account.

This change adds an optional company filter for parties. Each site explicitly
maps Customer, Supplier, and Employee to the Link field that represents the
party's owning company. Advanced Bank Reconciliation then uses that mapping for
party searches and server-side validation.

The feature is disabled by default. Enabling it does not modify historical
documents.

## Goals

- Prevent a party associated with another company from being selected or
  submitted in bank reconciliation workflows.
- Treat a blank party company as shared and eligible for every company.
- Support custom Company Link fieldnames without hard-coding site-specific
  metadata in the shared app.
- Preserve current behavior when filtering is disabled.
- Apply one authoritative eligibility rule to legacy and modern interfaces,
  direct API calls, and automated bank rules.

## Non-goals

- Assigning parties to more than one specific company.
- Migrating or populating party company fields.
- Modifying historical Bank Transactions, Journal Entries, Payment Entries, or
  ABR Bank Rules.
- Inferring business meaning from a field label or fieldname.
- Supporting party doctypes other than Customer, Supplier, and Employee.

## Approaches Considered

### Automatic Company Link discovery

The app could select the first or only Link field whose target is Company.
This is unsafe because Customer and Supplier already contain
`represents_company`, which describes an internal trading relationship rather
than ownership or availability.

### Explicit fields in ABR Settings

Add one mapping field for each supported Party Type. Metadata supplies the
available choices and validates the saved value. This is the selected approach.
The supported Party Types are already a fixed allowlist, so three settings are
clearer and smaller than a new mapping child table.

### Mapping child table

A child table would be more extensible if arbitrary Party Types were supported.
It adds another DocType, grid behavior, duplicate-row validation, and dynamic
field options without providing a current benefit.

## Settings

Add a **Party Company Filtering** section to the Single DocType
`Advance Bank Reconciliation Settings`.

Fields:

| Fieldname | Type | Default | Behavior |
| --- | --- | --- | --- |
| `filter_parties_by_company` | Check | `0` | Enables party filtering and validation |
| `customer_company_field` | Autocomplete | blank | Customer Link field that represents owning company |
| `supplier_company_field` | Autocomplete | blank | Supplier Link field that represents owning company |
| `employee_company_field` | Autocomplete | `company` | Employee Link field that represents owning company |

The three mapping fields are visible and mandatory only when filtering is
enabled. Their autocomplete choices come from server-validated DocType metadata
and include only fields where:

- `fieldtype` is `Link`
- `options` is `Company`

The UI displays both label and fieldname so administrators can distinguish
similarly named fields. Customer and Supplier mappings are intentionally not
defaulted. In particular, the app must not assume `represents_company` is an
ownership field.

When filtering is enabled, settings validation requires all three mappings.
Each mapping must still exist and remain a Link to Company. Invalid, deleted, or
renamed fields produce an actionable validation error.

Saving an enabled configuration checks enabled ABR Bank Rules that contain a
party. If an enabled rule's party is not eligible for the rule company, saving
is rejected with a bounded list of affected rules. The administrator must
correct or disable those rules before activation.

## Party Eligibility

For a selected reconciliation company and a configured Party Type:

| Party company value | Result |
| --- | --- |
| Selected company | Eligible |
| Blank or null | Eligible as shared |
| Another company | Ineligible |

Existing read permissions, select permissions, disabled-party behavior, and
standard Frappe search behavior remain in force.

If filtering is enabled but configuration is missing or invalid at runtime,
the operation fails with a configuration error. It must not silently return an
unfiltered list.

## Server Architecture

Create a focused module:

`advanced_bank_reconciliation/api/party_company.py`

It owns configuration resolution, metadata validation, party search, and
company eligibility.

Public interfaces:

```python
SUPPORTED_PARTY_TYPES = ("Customer", "Supplier", "Employee")

def get_company_link_fields(party_type: str) -> list[dict]:
    """Return valid Company Link fields as fieldname and label records."""

def get_party_company_field(
    party_type: str,
    settings=None,
) -> str | None:
    """Return the configured field, or None when filtering is disabled."""

def is_party_eligible_for_company(
    party_type: str,
    party: str,
    company: str,
    settings=None,
) -> bool:
    """Return whether the party is exact-company or shared."""

def assert_party_eligible_for_company(
    party_type: str,
    party: str,
    company: str,
    user: str | None = None,
    settings=None,
):
    """Check party validity, read access, and optional company eligibility."""

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_parties(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters,
):
    """Return permitted party matches for the supplied company."""
```

The search method validates the Party Type allowlist, Company access, configured
metadata, search inputs, and user permissions. When filtering is enabled it
adds an exact-company-or-blank condition. When disabled it preserves standard
global search behavior.

Settings and DocType metadata may use Frappe's normal document and metadata
caches. Search results are not cached because permissions and search text vary
per request.

`assert_party_access` in `api/permission.py` gains a `company` argument and
delegates company eligibility to the shared module. When filtering is enabled
and a party is supplied, company is mandatory.

## Mutation Coverage

Every path that writes or acts on a party must supply the company:

- Legacy `update_bank_transaction`
- Legacy `create_journal_entry_bts`
- Legacy `create_payment_entry_bts`
- Modern `update_transaction_metadata`
- Modern voucher creation and draft creation
- Cash-coding preview and submission
- ABR Bank Rule validation
- ABR Bank Rule action execution

Legacy voucher methods derive company from the Bank Transaction's Bank Account
before validating the party. Modern methods use the company already resolved
through their Bank Transaction access checks.

ABR Bank Rule validation checks the configured party against the rule company.
Rule execution validates again through the voucher method so a later metadata
or party change cannot bypass the rule.

## Legacy Interface

The legacy reconciliation dialog's Party Dynamic Link uses `search_parties`
with the selected Bank Account company. Party Type changes clear the existing
Party value.

The ABR Bank Rule form uses the same query with the rule company and Party Type.
Changing either controlling value clears the Party value.

If filtering is disabled, the query returns the same globally permitted parties
as the current Link search.

## Modern Interface

Add a reusable `PartyAutocomplete` component to the modern Bank Rec frontend.
It accepts:

- `company`
- `partyType`
- `modelValue`
- disabled and label presentation properties

The component performs a debounced search through `search_parties`, renders
permitted results, and emits the selected party name. It clears its value when
Company or Party Type changes and the current value is no longer valid.

Use the component in:

- Create Voucher
- Update Bank Transaction
- Cash Coding

The server remains authoritative if a user types or submits a value that is not
in the suggestions.

## Errors

Errors must identify the action the administrator or user can take:

- Filtering enabled with a missing mapping:
  `Configure the Customer Company Field in Advance Bank Reconciliation Settings.`
- Mapping does not resolve to a Company Link:
  `Field <fieldname> on <doctype> must be a Link to Company.`
- Party belongs to another company:
  `<party_type> <party> is not available for company <company>.`
- Missing company during an enabled validation:
  `Company is required when party company filtering is enabled.`

Messages must not expose records that the current user cannot read.

## Backward Compatibility

- The setting defaults to disabled.
- Disabled behavior remains global and matches the current implementation.
- Migration only adds settings fields and frontend/server behavior.
- Existing documents and rules are not rewritten.
- Enabling is blocked until mappings and enabled rules are valid.
- Disabling restores current global party behavior.

## Test Strategy

Use Frappe v15 `FrappeTestCase` and generic test records.

### Settings and metadata

- Disabled setting permits blank mappings.
- Enabled setting requires all mappings.
- Valid Link-to-Company mappings save.
- Missing fields, non-Link fields, and Links to another DocType are rejected.
- Metadata candidate API returns only Links to Company.
- Customer and Supplier mappings are not automatically assigned.

### Eligibility and search

For Customer, Supplier, and Employee:

- Exact-company party is returned and accepted.
- Blank-company party is returned and accepted.
- Other-company party is neither returned nor accepted.
- Filtering disabled returns current permitted results.
- Unsupported Party Types are rejected.
- Missing or stale configuration fails closed.
- User permissions remain effective.

### Mutation paths

- Bank Transaction metadata update rejects an ineligible party.
- Journal Entry creation rejects an ineligible reference party.
- Payment Entry creation rejects an ineligible accounting party.
- Voucher draft creation rejects an ineligible party.
- Cash-coding preview and submission reject an ineligible party.
- Eligible and shared parties continue to work.

### Bank rules

- Rule validation rejects an ineligible party.
- Enabling settings detects incompatible enabled rules.
- Rule execution cannot bypass validation after configuration or party changes.

### Frontend verification

- Legacy Party search sends Party Type and company.
- Party is cleared when its controlling values change.
- Modern frontend production build succeeds.
- Browser checks cover Create, Update, Cash Coding, and Bank Rule party searches.
- Browser console contains no new errors.

## Rollout

1. Deploy the patch with filtering disabled.
2. Ensure each supported Party Type has a populated ownership Company field.
3. Configure the three mappings.
4. Review any incompatible enabled bank rules.
5. Enable filtering.
6. Validate exact-company and shared party searches in Bank Rec.

No production configuration or deployment is part of this pull request.
