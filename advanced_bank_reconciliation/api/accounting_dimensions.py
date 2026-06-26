import frappe

from advanced_bank_reconciliation.utils.logger import get_logger


def _get_dimension_checks(company):
	try:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			get_checks_for_pl_and_bs_accounts,
		)
	except ImportError:
		return {}

	checks = {}
	for row in get_checks_for_pl_and_bs_accounts():
		if company and row.company != company:
			continue
		checks[row.fieldname] = {
			"default_value": row.default_dimension or "",
			"mandatory_for_bs": bool(row.mandatory_for_bs),
			"mandatory_for_pl": bool(row.mandatory_for_pl),
		}
	return checks


def get_accounting_dimension_fields(company=None):
	"""Return custom accounting dimension field metadata for the bank rec UI."""
	try:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			get_accounting_dimensions,
		)

		dimensions = get_accounting_dimensions(as_list=False)
	except ImportError:
		return []
	except Exception:
		get_logger().warning("Failed to fetch accounting dimensions", exc_info=True)
		return []

	checks = _get_dimension_checks(company)
	result = []
	for dim in dimensions:
		try:
			has_company_field = bool(frappe.get_meta(dim.document_type).has_field("company"))
		except Exception:
			has_company_field = False
		result.append(
			{
				"fieldname": dim.fieldname,
				"fieldtype": "Link",
				"label": dim.label,
				"options": dim.document_type,
				"has_company_field": has_company_field,
				"default_value": checks.get(dim.fieldname, {}).get("default_value", ""),
				"mandatory_for_bs": checks.get(dim.fieldname, {}).get("mandatory_for_bs", False),
				"mandatory_for_pl": checks.get(dim.fieldname, {}).get("mandatory_for_pl", False),
			}
		)
	return result


def get_accounting_dimension_options(dimensions, company=None):
	options = {}

	for dimension in dimensions:
		fieldname = dimension.get("fieldname")
		doctype = dimension.get("options")
		if not fieldname or not doctype:
			continue

		filters = {}
		if dimension.get("has_company_field") and company:
			filters["company"] = company

		try:
			meta = frappe.get_meta(doctype)
			fields = ["name"]
			if meta.title_field and meta.title_field != "name":
				fields.append(meta.title_field)
			options[fieldname] = frappe.get_list(
				doctype,
				filters=filters,
				fields=fields,
				order_by="modified desc",
				limit_page_length=100,
			)
		except Exception:
			get_logger().warning(
				"Failed to fetch accounting dimension options for %s", fieldname, exc_info=True
			)
			options[fieldname] = []

	return options


def get_accounting_dimension_context(company=None):
	dimensions = get_accounting_dimension_fields(company)
	return {
		"accounting_dimensions": dimensions,
		"dimension_options": get_accounting_dimension_options(dimensions, company),
	}
