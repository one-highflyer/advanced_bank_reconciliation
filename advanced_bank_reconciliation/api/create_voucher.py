import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.abr_bank_rule import (
	create_bank_rule_from_voucher,
)
from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_journal_entry_bts,
	create_payment_entry_bts,
	get_abr_default_settings,
)
from advanced_bank_reconciliation.api.accounting_dimensions import get_accounting_dimension_context
from advanced_bank_reconciliation.api.bank_rec import _bank_account_to_dto, _transaction_to_dto
from advanced_bank_reconciliation.api.matching import _linked_payment_dto, _lock_bank_transaction
from advanced_bank_reconciliation.api.permission import (
	assert_party_access,
	assert_bank_transaction_access,
	assert_company_access,
	log_unexpected_api_exception,
	require_bank_rec_permission,
)


def _parse_payload(payload):
	if payload is None:
		return {}
	if isinstance(payload, str):
		return frappe.parse_json(payload)
	return payload


def _desk_url(doctype, name):
	return "/app/{0}/{1}".format(frappe.scrub(doctype).replace("_", "-"), name)


def _get_company(transaction):
	company = transaction.company or frappe.get_cached_value(
		"Bank Account",
		transaction.bank_account,
		"company",
	)
	return assert_company_access(company)


def _assert_account_access(account, company):
	if not account:
		return None

	doc = frappe.get_doc("Account", account)
	frappe.has_permission("Account", "read", doc=doc, throw=True)
	if doc.company != company:
		raise frappe.PermissionError(_("Account {0} is not in company {1}.").format(account, company))
	if doc.is_group:
		frappe.throw(_("Select a ledger account, not a group account."))
	return doc


def _selected_entry_type(payload):
	if payload.get("account"):
		return "Journal Entry"
	if payload.get("party_type") and payload.get("party"):
		return "Payment Entry"
	return "Journal Entry"


def _default_reference(transaction, payload):
	return (
		payload.get("reference_number")
		or transaction.reference_number
		or transaction.description
		or transaction.name
	)


def _common_kwargs(transaction, payload):
	return {
		"bank_transaction_name": transaction.name,
		"reference_number": _default_reference(transaction, payload),
		"reference_date": payload.get("reference_date") or transaction.date,
		"posting_date": payload.get("posting_date") or transaction.date,
		"mode_of_payment": payload.get("mode_of_payment"),
		"party_type": payload.get("party_type"),
		"party": payload.get("party"),
		"cost_center": payload.get("cost_center"),
		"project": payload.get("project"),
		"dimensions": payload.get("dimensions"),
	}


def _build_voucher(transaction, payload, allow_edit=False):
	company = _get_company(transaction)
	entry_type = _selected_entry_type(payload)
	common = _common_kwargs(transaction, payload)
	assert_party_access(common["party_type"], common["party"])

	if entry_type == "Payment Entry":
		if not common["party_type"] or not common["party"]:
			frappe.throw(_("Contact is required to create a payment entry."))
		return (
			"Payment Entry",
			create_payment_entry_bts(
				**common,
				allow_edit=allow_edit,
			),
		)

	account = payload.get("account")
	account_doc = _assert_account_access(account, company)
	if not account_doc:
		frappe.throw(_("Account is required to create a journal entry."))
	if account_doc.account_type in ["Receivable", "Payable"] and (
		not common["party_type"] or not common["party"]
	):
		frappe.throw(_("Contact is required for receivable or payable accounts."))

	settings = get_abr_default_settings()
	return (
		"Journal Entry",
		create_journal_entry_bts(
			**common,
			entry_type=payload.get("journal_entry_type")
			or settings.get("default_journal_entry_type")
			or "Bank Entry",
			second_account=account,
			allow_edit=allow_edit,
		),
	)


def _new_linked_voucher(before_keys, transaction):
	after_keys = {
		(row.payment_document, row.payment_entry)
		for row in transaction.get("payment_entries", [])
		if row.payment_document and row.payment_entry
	}
	new_keys = list(after_keys - before_keys)
	if not new_keys:
		return None, None
	return new_keys[0]


def _rule_conditions(transaction):
	value = transaction.description or transaction.bank_party_name or transaction.reference_number
	if not value:
		value = transaction.name
	return [
		{
			"field_name": "Description",
			"condition": "Contains",
			"value": value[:140],
		}
	]


def _maybe_create_rule(transaction, payload, entry_type):
	if not payload.get("save_as_rule"):
		return None

	return create_bank_rule_from_voucher(
		bank_transaction_name=transaction.name,
		title=payload.get("rule_title") or transaction.bank_party_name or transaction.description or transaction.name,
		entry_type=entry_type,
		conditions=_rule_conditions(transaction),
		second_account=payload.get("account"),
		party_type=payload.get("party_type"),
		party=payload.get("party"),
		cost_center=payload.get("cost_center"),
		project=payload.get("project"),
		dimensions=payload.get("dimensions"),
	)


def _validate_rule_request(payload):
	if not payload.get("save_as_rule"):
		return
	frappe.has_permission("ABR Bank Rule", "create", throw=True)
	if not payload.get("rule_title"):
		frappe.throw(_("Rule title is required when saving a bank rule."))


@frappe.whitelist()
def get_create_defaults(bank_transaction_name):
	transaction = assert_bank_transaction_access(bank_transaction_name)
	company = _get_company(transaction)
	bank_account = frappe.get_doc("Bank Account", transaction.bank_account)
	settings = get_abr_default_settings()
	dimension_context = get_accounting_dimension_context(company)

	accounts = frappe.get_list(
		"Account",
		filters={"company": company, "is_group": 0, "disabled": 0},
		fields=["name", "account_name", "account_type", "root_type"],
		order_by="account_name asc",
		limit_page_length=200,
	)
	mode_of_payments = frappe.get_list(
		"Mode of Payment",
		fields=["name"],
		order_by="name asc",
		limit_page_length=100,
	)
	cost_centers = frappe.get_list(
		"Cost Center",
		filters={"company": company, "is_group": 0},
		fields=["name", "cost_center_name"],
		order_by="cost_center_name asc",
		limit_page_length=100,
	)
	projects = frappe.get_list(
		"Project",
		filters={"company": company},
		fields=["name", "project_name"],
		order_by="modified desc",
		limit_page_length=100,
	)

	return {
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
		"bank_account": _bank_account_to_dto(bank_account),
		"settings": settings,
		"defaults": {
			"posting_date": transaction.date,
			"reference_date": transaction.date,
			"reference_number": _default_reference(transaction, {}),
			"party_type": transaction.party_type,
			"party": transaction.party,
		},
		"options": {
			"accounts": accounts,
			"mode_of_payments": mode_of_payments,
			"cost_centers": cost_centers,
			"projects": projects,
			**dimension_context,
		},
	}


@frappe.whitelist()
def create_voucher_from_transaction(bank_transaction_name, payload):
	try:
		return _create_voucher_from_transaction(bank_transaction_name, payload)
	except Exception as exc:
		log_unexpected_api_exception(
			exc, "Bank Rec create_voucher_from_transaction failed", rollback=True
		)
		raise


def _create_voucher_from_transaction(bank_transaction_name, payload):
	require_bank_rec_permission()
	payload = _parse_payload(payload)
	transaction = assert_bank_transaction_access(bank_transaction_name, ptype="write")
	_lock_bank_transaction(transaction.name)
	transaction.reload()

	if transaction.status == "Reconciled" or flt(transaction.unallocated_amount) <= 0:
		frappe.throw(_("This bank transaction is already reconciled."))
	_validate_rule_request(payload)

	before_keys = {
		(row.payment_document, row.payment_entry)
		for row in transaction.get("payment_entries", [])
		if row.payment_document and row.payment_entry
	}
	entry_type, updated_transaction = _build_voucher(transaction, payload, allow_edit=False)
	updated_transaction.reload()
	voucher_type, voucher_name = _new_linked_voucher(before_keys, updated_transaction)
	rule = _maybe_create_rule(transaction, payload, entry_type)

	return {
		"status": updated_transaction.status,
		"transaction": _transaction_to_dto(
			updated_transaction.as_dict(),
			status=updated_transaction.status,
		),
		"voucher_type": voucher_type,
		"voucher_name": voucher_name,
		"desk_url": _desk_url(voucher_type, voucher_name) if voucher_type and voucher_name else None,
		"linked_payments": _linked_payment_dto(updated_transaction),
		"rule": rule,
	}


@frappe.whitelist()
def create_voucher_draft_from_transaction(bank_transaction_name, payload):
	try:
		return _create_voucher_draft_from_transaction(bank_transaction_name, payload)
	except Exception as exc:
		log_unexpected_api_exception(
			exc, "Bank Rec create_voucher_draft_from_transaction failed", rollback=True
		)
		raise


def _create_voucher_draft_from_transaction(bank_transaction_name, payload):
	require_bank_rec_permission()
	payload = _parse_payload(payload)
	transaction = assert_bank_transaction_access(bank_transaction_name, ptype="write")
	_lock_bank_transaction(transaction.name)
	transaction.reload()

	if transaction.status == "Reconciled" or flt(transaction.unallocated_amount) <= 0:
		frappe.throw(_("This bank transaction is already reconciled."))

	voucher_type, voucher = _build_voucher(transaction, payload, allow_edit=True)
	voucher.insert()

	return {
		"voucher_type": voucher_type,
		"voucher_name": voucher.name,
		"desk_url": _desk_url(voucher_type, voucher.name),
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
	}
