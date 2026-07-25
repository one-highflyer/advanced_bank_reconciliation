import frappe
from frappe import _


SUPPORTED_PARTY_TYPES: tuple[str, ...] = ("Customer", "Supplier", "Employee")
PARTY_COMPANY_SETTING_FIELDS: dict[str, str] = {
	"Customer": "customer_company_field",
	"Supplier": "supplier_company_field",
	"Employee": "employee_company_field",
}

TEXT_FIELD_TYPES = {
	"Data",
	"Text",
	"Small Text",
	"Long Text",
	"Link",
	"Select",
	"Read Only",
	"Text Editor",
}


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


@frappe.whitelist()
def get_company_link_fields(party_type: str) -> list[dict[str, str]]:
	frappe.has_permission(
		"Advance Bank Reconciliation Settings",
		"read",
		throw=True,
	)
	_require_supported_party_type(party_type)

	return [
		{"fieldname": field.fieldname, "label": field.label}
		for field in frappe.get_meta(party_type).fields
		if field.fieldtype == "Link" and field.options == "Company"
	]


def get_party_company_field(party_type: str, settings=None) -> str | None:
	settings = _get_settings(settings)
	if not settings.get("filter_parties_by_company"):
		return None

	_require_supported_party_type(party_type)
	settings_field = PARTY_COMPANY_SETTING_FIELDS[party_type]
	fieldname = settings.get(settings_field)
	if not fieldname:
		frappe.throw(
			_("Configure the {0} Company Field in Advance Bank Reconciliation Settings.").format(
				party_type
			)
		)

	_validate_company_link_field(party_type, fieldname)
	return fieldname


def is_party_eligible_for_company(
	party_type: str,
	party: str,
	company: str,
	settings=None,
) -> bool:
	fieldname = get_party_company_field(party_type, settings=settings)
	if not fieldname:
		return True

	party_company = frappe.get_cached_value(party_type, party, fieldname)
	return not party_company or party_company == company


def assert_party_eligible_for_company(
	party_type: str,
	party: str,
	company: str,
	user: str | None = None,
	settings=None,
):
	_require_supported_party_type(party_type)
	if not party:
		frappe.throw(_("Party is required when Party Type is set."))

	user = user or frappe.session.user
	doc = frappe.get_doc(party_type, party)
	frappe.has_permission(party_type, "read", doc=doc, user=user, throw=True)

	fieldname = get_party_company_field(party_type, settings=settings)
	if not fieldname:
		return doc
	if not company:
		frappe.throw(_("Company is required when party company filtering is enabled."))

	party_company = frappe.get_cached_value(party_type, party, fieldname)
	if not party_company or party_company == company:
		return doc

	frappe.throw(
		_("{0} {1} is not available for company {2}.").format(
			party_type,
			party,
			company,
		)
	)


def _get_search_fields(meta, searchfield):
	candidates = ["name"]
	if meta.title_field:
		candidates.append(meta.title_field)
	if meta.search_fields:
		candidates.extend(meta.get_search_fields())
	if searchfield:
		candidates.append(searchfield)

	fields = []
	for fieldname in candidates:
		fieldname = fieldname.strip()
		field = meta.get_field(fieldname)
		if fieldname == "name" or (
			not meta.translated_doctype
			and field
			and field.fieldtype in TEXT_FIELD_TYPES
		):
			if fieldname not in fields:
				fields.append(fieldname)
	return fields


def _has_check_field(meta, fieldname):
	field = meta.get_field(fieldname)
	return bool(field and field.fieldtype == "Check")


@frappe.whitelist()
def search_parties(
	doctype,
	txt,
	searchfield,
	start,
	page_len,
	filters,
	exact_party=None,
):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	if not isinstance(filters, dict):
		frappe.throw(_("Party search filters must be a dictionary."))

	party_type = filters.get("party_type") or doctype
	_require_supported_party_type(party_type)
	if doctype != party_type:
		frappe.throw(
			_("Party Type {0} does not match {1}.").format(party_type, doctype)
		)

	company = filters.get("company")
	mapped_field = get_party_company_field(party_type)
	if mapped_field and not company:
		frappe.throw(_("Company is required when party company filtering is enabled."))

	from advanced_bank_reconciliation.api.permission import assert_company_access

	company = assert_company_access(company)
	meta = frappe.get_meta(doctype)
	fields = _get_search_fields(meta, searchfield)
	query_filters = []
	if _has_check_field(meta, "enabled"):
		query_filters.append([doctype, "enabled", "=", 1])
	if _has_check_field(meta, "disabled"):
		query_filters.append([doctype, "disabled", "!=", 1])
	if mapped_field:
		query_filters.append([doctype, mapped_field, "in", [company, ""]])
	if exact_party:
		query_filters.append([doctype, "name", "=", exact_party])

	or_filters = []
	if txt:
		or_filters = [
			[doctype, fieldname, "like", f"%{txt}%"]
			for fieldname in fields
		]

	return frappe.get_list(
		doctype,
		fields=fields,
		filters=query_filters,
		or_filters=or_filters,
		limit_start=int(start),
		limit_page_length=int(page_len),
		as_list=True,
	)


def validate_party_company_settings(settings) -> None:
	if not settings.get("filter_parties_by_company"):
		return

	for party_type in SUPPORTED_PARTY_TYPES:
		get_party_company_field(party_type, settings=settings)


def validate_enabled_bank_rules(settings, limit: int = 20) -> None:
	if not settings.get("filter_parties_by_company"):
		return

	rules = frappe.get_all(
		"ABR Bank Rule",
		filters={
			"enabled": 1,
			"party_type": ["is", "set"],
			"party": ["is", "set"],
		},
		fields=["name", "party_type", "party", "company"],
		order_by="name",
	)
	ineligible_rules = [
		rule.name
		for rule in rules
		if not is_party_eligible_for_company(
			rule.party_type,
			rule.party,
			rule.company,
			settings=settings,
		)
	]
	if not ineligible_rules:
		return

	shown_rules = ineligible_rules[:limit]
	overflow = len(ineligible_rules) - len(shown_rules)
	rule_list = ", ".join(shown_rules)
	if overflow:
		rule_list = _("{0}, and {1} more").format(rule_list, overflow)

	frappe.throw(
		_(
			"These enabled bank rules use parties that are not available for their companies: "
			"{0}. Please correct or disable those rules."
		).format(rule_list)
	)
