import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from frappe.utils.jinja_globals import is_rtl

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	get_abr_default_settings,
	get_account_balance,
	get_accounting_dimensions_for_dialog,
	get_bank_transactions as get_existing_bank_transactions,
	get_reconciled_bank_transactions,
)
from advanced_bank_reconciliation.api.permission import (
	assert_bank_account_access,
	assert_bank_transaction_access,
	get_allowed_company_names,
	require_bank_rec_permission,
)


def _date_or_none(value):
	return getdate(value) if value else None


def _amount_for_transaction(row):
	return flt(row.get("deposit")) or -flt(row.get("withdrawal"))


def _direction_for_transaction(row):
	if flt(row.get("deposit")):
		return "deposit"
	if flt(row.get("withdrawal")):
		return "withdrawal"
	return "unknown"


def _transaction_to_dto(row, status=None):
	return {
		"name": row.get("name"),
		"date": row.get("date"),
		"description": row.get("description"),
		"reference_number": row.get("reference_number"),
		"bank_party_name": row.get("bank_party_name"),
		"custom_particulars": row.get("custom_particulars"),
		"custom_code": row.get("custom_code"),
		"deposit": flt(row.get("deposit")),
		"withdrawal": flt(row.get("withdrawal")),
		"amount": _amount_for_transaction(row),
		"direction": _direction_for_transaction(row),
		"currency": row.get("currency"),
		"bank_account": row.get("bank_account"),
		"company": row.get("company"),
		"unallocated_amount": flt(row.get("unallocated_amount")),
		"party_type": row.get("party_type"),
		"party": row.get("party"),
		"party_display": row.get("party_display") or row.get("party") or "",
		"payment_document": row.get("payment_document"),
		"payment_entry": row.get("payment_entry"),
		"allocated_amount": flt(row.get("allocated_amount")),
		"status": status or row.get("status"),
	}


def _dedupe_reconciled_rows(rows):
	unique = {}
	for row in rows:
		transaction = unique.setdefault(
			row["name"],
			{
				**row,
				"linked_payments": [],
			},
		)
		if row.get("payment_document") and row.get("payment_entry"):
			transaction["linked_payments"].append(
				{
					"payment_document": row.get("payment_document"),
					"payment_entry": row.get("payment_entry"),
					"allocated_amount": flt(row.get("allocated_amount")),
				}
			)

	return list(unique.values())


def _bank_account_to_dto(row):
	account_currency = frappe.get_cached_value("Account", row.account, "account_currency")
	return {
		"name": row.name,
		"account_name": row.account_name,
		"bank": row.bank,
		"account": row.account,
		"company": row.company,
		"currency": account_currency,
	}


def _get_bank_account_companies():
	allowed_companies = get_allowed_company_names()
	if not allowed_companies:
		return []

	rows = frappe.get_list(
		"Bank Account",
		filters={
			"is_company_account": 1,
			"company": ["in", allowed_companies],
		},
		pluck="company",
		group_by="company",
		order_by="company asc",
	)
	return sorted({company for company in rows if company})


def _get_filtered_transactions(bank_account, from_date=None, to_date=None, status="unreconciled"):
	assert_bank_account_access(bank_account)

	if status == "unreconciled":
		return [
			_transaction_to_dto(row, status="Unreconciled")
			for row in get_existing_bank_transactions(bank_account, from_date, to_date)
		]
	if status == "reconciled":
		return _dedupe_reconciled_rows([
			_transaction_to_dto(row, status="Reconciled")
			for row in get_reconciled_bank_transactions(bank_account, from_date, to_date)
		])
	if status == "all":
		unreconciled = _get_filtered_transactions(bank_account, from_date, to_date, "unreconciled")
		reconciled = _get_filtered_transactions(bank_account, from_date, to_date, "reconciled")
		return sorted(unreconciled + reconciled, key=lambda row: (row.get("date"), row.get("name")))

	frappe.throw(_("Unsupported transaction status {0}.").format(status))


@frappe.whitelist()
def get_boot():
	require_bank_rec_permission()
	return {
		"default_route": "/bank-rec/reconcile",
		"site_name": frappe.local.site,
		"csrf_token": frappe.sessions.get_csrf_token(),
		"session_user": frappe.session.user,
		"lang": frappe.local.lang,
		"dir": "rtl" if is_rtl() else "ltr",
		"allowed_roles": sorted(frappe.get_roles()),
		"allowed_companies": _get_bank_account_companies(),
		"settings": get_abr_default_settings(),
		"accounting_dimensions": get_accounting_dimensions_for_dialog(),
	}


@frappe.whitelist()
def get_bank_accounts(company=None):
	require_bank_rec_permission()
	allowed_companies = get_allowed_company_names()

	if company:
		if company not in allowed_companies:
			raise frappe.PermissionError(_("You are not permitted to access company {0}.").format(company))
		allowed_companies = [company]

	if not allowed_companies:
		return []

	rows = frappe.get_list(
		"Bank Account",
		filters={
			"is_company_account": 1,
			"company": ["in", allowed_companies],
		},
		fields=["name", "account_name", "bank", "account", "company"],
		order_by="account_name asc",
	)
	return [_bank_account_to_dto(row) for row in rows]


@frappe.whitelist()
def get_bank_rules(bank_account=None):
	require_bank_rec_permission()
	filters = {}

	if bank_account:
		bank_account_doc = assert_bank_account_access(bank_account)
		filters["bank_account"] = bank_account_doc.name
	else:
		allowed_companies = get_allowed_company_names()
		if not allowed_companies:
			return []
		filters["company"] = ["in", allowed_companies]

	rows = frappe.get_list(
		"ABR Bank Rule",
		filters=filters,
		fields=[
			"name",
			"title",
			"enabled",
			"priority",
			"company",
			"bank_account",
			"entry_type",
			"account",
			"party_type",
			"party",
			"modified",
		],
		order_by="priority asc, modified desc",
	)

	return [
		{
			**row,
			"desk_url": "/app/abr-bank-rule/{0}".format(row.name),
		}
		for row in rows
	]


@frappe.whitelist()
def get_statement_summary(bank_account, from_date=None, to_date=None):
	assert_bank_account_access(bank_account)
	from_date = _date_or_none(from_date)
	to_date = _date_or_none(to_date)
	unreconciled = get_existing_bank_transactions(bank_account, from_date, to_date)
	cleared_balance_date = to_date or getdate(nowdate())

	return {
		"bank_account": bank_account,
		"from_date": from_date,
		"to_date": to_date,
		"unreconciled_count": len(unreconciled),
		"selected_amount": None,
		"cleared_balance": flt(get_account_balance(bank_account, cleared_balance_date)),
		"unreconciled_total": sum(abs(flt(row.get("unallocated_amount"))) for row in unreconciled),
	}


@frappe.whitelist()
def get_transactions(bank_account, from_date=None, to_date=None, status="unreconciled"):
	from_date = _date_or_none(from_date)
	to_date = _date_or_none(to_date)
	return _get_filtered_transactions(bank_account, from_date, to_date, status or "unreconciled")


@frappe.whitelist()
def get_transaction_context(bank_transaction_name, filters=None):
	transaction = assert_bank_transaction_access(bank_transaction_name)
	bank_account = assert_bank_account_access(transaction.bank_account)

	linked_payments = []
	for row in transaction.get("payment_entries", []):
		linked_payments.append(
			{
				"payment_document": row.payment_document,
				"payment_entry": row.payment_entry,
				"allocated_amount": flt(row.allocated_amount),
			}
		)

	return {
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
		"bank_account": _bank_account_to_dto(bank_account),
		"linked_payments": linked_payments,
	}
