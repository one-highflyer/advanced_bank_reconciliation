import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_payment_entries_for_invoices,
	get_linked_payments,
	reconcile_vouchers,
)
from advanced_bank_reconciliation.api.bank_rec import _transaction_to_dto
from advanced_bank_reconciliation.api.permission import (
	assert_party_access,
	assert_bank_transaction_access,
	assert_voucher_access,
	log_unexpected_api_exception,
	require_bank_rec_permission,
)


DEFAULT_MATCH_DOCUMENT_TYPES = [
	"payment_entry",
	"journal_entry",
	"sales_invoice",
	"purchase_invoice",
	"unpaid_sales_invoice",
	"unpaid_purchase_invoice",
]

UNPAID_INVOICE_SOURCE_TYPES = {
	"Unpaid Sales Invoice": "Sales Invoice",
	"Unpaid Purchase Invoice": "Purchase Invoice",
}


def as_bool(value):
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		return value.lower() in {"1", "true", "yes", "on"}
	return bool(value)


def _parse_json(value, fallback):
	if value is None or value == "":
		return fallback
	if isinstance(value, str):
		return frappe.parse_json(value)
	return value


def _date_or_default(value, fallback):
	return getdate(value) if value else fallback


def _match_key(voucher_type, voucher_name):
	return "{0}::{1}".format(voucher_type, voucher_name)


def _normalise_voucher_type(voucher_type):
	if voucher_type == "Unpaid Sales Invoice":
		return "Sales Invoice"
	if voucher_type == "Unpaid Purchase Invoice":
		return "Purchase Invoice"
	return voucher_type


def _candidate_reasons(candidate, transaction):
	reasons = []
	if candidate["reference_number"] and candidate["reference_number"] == transaction.reference_number:
		reasons.append("Reference")
	if abs(flt(candidate["amount"])) == abs(flt(transaction.unallocated_amount)):
		reasons.append("Amount")
	if (
		candidate["party_type"]
		and candidate["party"]
		and candidate["party_type"] == transaction.party_type
		and candidate["party"] == transaction.party
	):
		reasons.append("Party")
	if not reasons:
		reasons.append("Possible match")
	return reasons


def _candidate_confidence(rank, reasons):
	if rank >= 4 or {"Reference", "Amount"}.issubset(set(reasons)):
		return "high"
	if rank >= 3 or "Amount" in reasons:
		return "medium"
	return "low"


def _candidate_to_dto(row, transaction):
	voucher_type = _normalise_voucher_type(row[1])
	candidate = {
		"rank": int(row[0] or 0),
		"voucher_type": voucher_type,
		"source_type": row[1],
		"voucher_name": row[2],
		"amount": flt(row[3]),
		"reference_number": row[4],
		"reference_date": row[5],
		"party": row[6],
		"party_type": row[7],
		"posting_date": row[8],
		"currency": row[9],
		"party_name": row[10] if len(row) > 10 else row[6],
		"key": _match_key(voucher_type, row[2]),
	}
	candidate["reasons"] = _candidate_reasons(candidate, transaction)
	candidate["confidence"] = _candidate_confidence(candidate["rank"], candidate["reasons"])
	return candidate


def _normalise_document_types(document_types, exact_match=False):
	document_types = _parse_json(document_types, None) or list(DEFAULT_MATCH_DOCUMENT_TYPES)
	if isinstance(document_types, str):
		document_types = [document_types]
	if as_bool(exact_match) and "exact_match" not in document_types:
		document_types.append("exact_match")
	return document_types


def _normalise_vouchers(vouchers):
	vouchers = _parse_json(vouchers, [])
	if not isinstance(vouchers, list) or not vouchers:
		frappe.throw(_("Select at least one match before reconciling."))

	normalised = []
	for row in vouchers:
		voucher_type = row.get("voucher_type") or row.get("payment_doctype")
		source_type = row.get("source_type") or voucher_type
		voucher_type = _normalise_voucher_type(voucher_type)
		voucher_name = row.get("voucher_name") or row.get("payment_name")
		amount = flt(row.get("amount"))

		if not voucher_type or not voucher_name:
			frappe.throw(_("Each selected match must include a voucher type and name."))
		if amount <= 0:
			frappe.throw(_("Each selected match must include a positive amount."))
		if (
			source_type in UNPAID_INVOICE_SOURCE_TYPES
			and UNPAID_INVOICE_SOURCE_TYPES[source_type] != voucher_type
		):
			frappe.throw(_("The selected invoice type does not match its source type."))

		normalised.append(
			{
				"payment_doctype": voucher_type,
				"payment_name": voucher_name,
				"amount": amount,
				"source_type": source_type,
			}
		)

	return normalised


def _existing_match_keys(transaction):
	keys = {
		(row.payment_document, row.payment_entry)
		for row in transaction.get("payment_entries", [])
		if row.payment_document and row.payment_entry
	}
	payment_entries = [
		row.payment_entry
		for row in transaction.get("payment_entries", [])
		if row.payment_document == "Payment Entry" and row.payment_entry
	]
	if payment_entries:
		keys.update(
			(
				row.reference_doctype,
				row.reference_name,
			)
			for row in frappe.get_all(
				"Payment Entry Reference",
				filters={"parent": ["in", payment_entries]},
				fields=["reference_doctype", "reference_name"],
			)
			if row.reference_doctype and row.reference_name
		)
	return keys


def _prepare_reconciliation_vouchers(transaction, vouchers):
	unpaid_invoices = []
	regular_vouchers = []

	for row in vouchers:
		voucher_doc = assert_voucher_access(
			row["payment_doctype"],
			row["payment_name"],
		)
		source_type = row["source_type"]
		outstanding_amount = flt(voucher_doc.get("outstanding_amount"))

		if source_type not in UNPAID_INVOICE_SOURCE_TYPES:
			regular_vouchers.append(
				{
					"payment_doctype": row["payment_doctype"],
					"payment_name": row["payment_name"],
					"amount": row["amount"],
				}
			)
			continue

		if not outstanding_amount:
			frappe.throw(
				_("Invoice {0} no longer has an outstanding amount.").format(
					voucher_doc.name
				)
			)
		allocated_amount = abs(flt(row["amount"]))
		if outstanding_amount < 0:
			allocated_amount *= -1
		unpaid_invoices.append(
			{
				"doctype": source_type,
				"name": row["payment_name"],
				"allocated_amount": allocated_amount,
			}
		)

	if unpaid_invoices:
		created = create_payment_entries_for_invoices(
			transaction.name,
			unpaid_invoices,
			auto_reconcile=False,
		)
		regular_vouchers = created["vouchers"] + regular_vouchers

	return regular_vouchers


def _linked_payment_dto(transaction):
	return [
		{
			"payment_document": row.payment_document,
			"payment_entry": row.payment_entry,
			"allocated_amount": flt(row.allocated_amount),
		}
		for row in transaction.get("payment_entries", [])
	]


def _lock_bank_transaction(bank_transaction_name):
	frappe.db.sql(
		"select name from `tabBank Transaction` where name=%s for update",
		bank_transaction_name,
	)


@frappe.whitelist()
def get_match_candidates(
	bank_transaction_name,
	document_types=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
	exact_match=False,
):
	transaction = assert_bank_transaction_access(bank_transaction_name)
	bank_transaction_date = getdate(transaction.date)
	from_date = _date_or_default(from_date, add_days(bank_transaction_date, -90))
	to_date = _date_or_default(to_date, add_days(bank_transaction_date, 90))
	document_types = _normalise_document_types(document_types, exact_match=exact_match)

	rows = get_linked_payments(
		bank_transaction_name=transaction.name,
		document_types=document_types,
		from_date=from_date,
		to_date=to_date,
		filter_by_reference_date=filter_by_reference_date,
		from_reference_date=from_reference_date,
		to_reference_date=to_reference_date,
	)

	return {
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
		"candidates": [_candidate_to_dto(row, transaction) for row in rows],
		"filters": {
			"document_types": document_types,
			"from_date": from_date,
			"to_date": to_date,
		},
	}


@frappe.whitelist()
def submit_match(bank_transaction_name, vouchers):
	try:
		return _submit_match(bank_transaction_name, vouchers)
	except Exception as exc:
		log_unexpected_api_exception(exc, "Bank Rec submit_match failed", rollback=True)
		raise


def _submit_match(bank_transaction_name, vouchers):
	require_bank_rec_permission()
	transaction = assert_bank_transaction_access(bank_transaction_name, ptype="write")
	_lock_bank_transaction(transaction.name)
	transaction.reload()

	if transaction.status == "Reconciled" or flt(transaction.unallocated_amount) <= 0:
		requested_vouchers = _normalise_vouchers(vouchers)
		requested_keys = {
			(row["payment_doctype"], row["payment_name"])
			for row in requested_vouchers
		}
		if requested_keys.issubset(_existing_match_keys(transaction)):
			return {
				"status": transaction.status,
				"idempotent": True,
				"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
				"linked_payments": _linked_payment_dto(transaction),
			}
		frappe.throw(_("This bank transaction is already reconciled."))

	normalised_vouchers = _normalise_vouchers(vouchers)
	existing_keys = _existing_match_keys(transaction)
	requested_keys = {
		(row["payment_doctype"], row["payment_name"])
		for row in normalised_vouchers
	}
	if existing_keys.intersection(requested_keys):
		frappe.throw(_("One or more selected vouchers are already linked to this bank transaction."))

	total = sum(abs(flt(row["amount"])) for row in normalised_vouchers)
	if total - abs(flt(transaction.unallocated_amount)) > 0.01:
		frappe.throw(_("Selected amount exceeds the unallocated bank transaction amount."))

	reconciliation_vouchers = _prepare_reconciliation_vouchers(
		transaction,
		normalised_vouchers,
	)
	updated_transaction = reconcile_vouchers(
		transaction.name,
		json.dumps(reconciliation_vouchers),
	)
	return {
		"status": updated_transaction.status,
		"idempotent": False,
		"transaction": _transaction_to_dto(
			updated_transaction.as_dict(),
			status=updated_transaction.status,
		),
		"linked_payments": _linked_payment_dto(updated_transaction),
	}


@frappe.whitelist()
def update_transaction_metadata(
	bank_transaction_name,
	reference_number=None,
	party_type=None,
	party=None,
):
	transaction = assert_bank_transaction_access(bank_transaction_name, ptype="write")
	_lock_bank_transaction(transaction.name)
	transaction.reload()

	company = transaction.company or frappe.get_cached_value(
		"Bank Account",
		transaction.bank_account,
		"company",
	)
	assert_party_access(party_type, party, company=company)

	transaction.reference_number = reference_number or ""
	transaction.party_type = party_type or ""
	transaction.party = party or ""
	transaction.save()

	return {
		"transaction": _transaction_to_dto(
			transaction.as_dict(),
			status=transaction.status,
		)
	}
