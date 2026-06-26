import frappe
from frappe import _
from frappe.utils import flt

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_journal_entry_bts,
	get_abr_default_settings,
)
from advanced_bank_reconciliation.api.accounting_dimensions import get_accounting_dimension_context
from advanced_bank_reconciliation.api.bank_rec import _transaction_to_dto, get_transactions
from advanced_bank_reconciliation.api.matching import _lock_bank_transaction
from advanced_bank_reconciliation.api.permission import (
	assert_party_access,
	assert_bank_account_access,
	assert_bank_transaction_access,
	assert_company_access,
	require_bank_rec_permission,
)


def _parse_rows(rows):
	if isinstance(rows, str):
		return frappe.parse_json(rows)
	return rows or []


def _assert_account(account, company):
	if not account:
		frappe.throw(_("Account is required."))

	doc = frappe.get_doc("Account", account)
	frappe.has_permission("Account", "read", doc=doc, throw=True)
	if doc.company != company:
		raise frappe.PermissionError(_("Account {0} is not in company {1}.").format(account, company))
	if doc.is_group:
		frappe.throw(_("Select a ledger account, not a group account."))
	return doc


def _row_error(row, message):
	return {
		"bank_transaction": row.get("bank_transaction_name"),
		"status": "error",
		"message": message,
	}


def _is_expected_row_exception(exc):
	expected = (frappe.ValidationError, frappe.PermissionError, frappe.DoesNotExistError)
	link_validation_error = getattr(frappe, "LinkValidationError", None)
	if link_validation_error:
		expected = expected + (link_validation_error,)
	return isinstance(exc, expected)


def _row_exception_error(row, exc, title):
	if _is_expected_row_exception(exc):
		return _row_error(row, str(exc) or _("Unable to process this row."))

	frappe.log_error(title=title, message=frappe.get_traceback())
	return _row_error(row, _("Unexpected server error. Please try again."))


def _row_success(row, transaction):
	transaction.reload()
	if (
		transaction.status != "Reconciled"
		or abs(flt(transaction.unallocated_amount)) > 0.01
		or not transaction.get("payment_entries")
	):
		frappe.throw(_("Cash coding did not reconcile the bank transaction."))

	voucher = None
	for payment in transaction.get("payment_entries", []):
		voucher = {
			"voucher_type": payment.payment_document,
			"voucher_name": payment.payment_entry,
		}

	return {
		"bank_transaction": row.get("bank_transaction_name"),
		"status": "success",
		"message": _("Reconciled"),
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
		"voucher": voucher,
	}


@frappe.whitelist()
def get_cash_coding_rows(bank_account, from_date=None, to_date=None):
	bank_account_doc = assert_bank_account_access(bank_account)
	company = bank_account_doc.company
	dimension_context = get_accounting_dimension_context(company)
	rows = get_transactions(
		bank_account=bank_account,
		from_date=from_date,
		to_date=to_date,
		status="unreconciled",
	)
	return {
		"rows": [
			{
				"transaction": row,
				"account": "",
				"party_type": row.get("party_type") or "",
				"party": row.get("party") or "",
				"cost_center": "",
				"project": "",
				"dimensions": {},
				"reference_number": row.get("reference_number") or "",
				"notes": "",
				"suggested_rule": None,
			}
			for row in rows
		],
		"options": {
			"accounts": frappe.get_list(
				"Account",
				filters={"company": company, "is_group": 0, "disabled": 0},
				fields=["name", "account_name", "account_type", "root_type"],
				order_by="account_name asc",
				limit_page_length=200,
			),
			"cost_centers": frappe.get_list(
				"Cost Center",
				filters={"company": company, "is_group": 0},
				fields=["name", "cost_center_name"],
				order_by="cost_center_name asc",
				limit_page_length=100,
			),
			"projects": frappe.get_list(
				"Project",
				filters={"company": company},
				fields=["name", "project_name"],
				order_by="modified desc",
				limit_page_length=100,
			),
			**dimension_context,
		},
	}


@frappe.whitelist()
def preview_cash_coding(rows):
	require_bank_rec_permission()
	rows = _parse_rows(rows)
	results = []

	for row in rows:
		try:
			transaction = assert_bank_transaction_access(row.get("bank_transaction_name"))
			transaction.reload()
			if transaction.status == "Reconciled" or flt(transaction.unallocated_amount) <= 0:
				frappe.throw(_("This bank transaction is already reconciled."))
			company = transaction.company or frappe.get_cached_value(
				"Bank Account",
				transaction.bank_account,
				"company",
			)
			assert_company_access(company)
			assert_party_access(row.get("party_type"), row.get("party"))
			account = _assert_account(row.get("account"), company)
			if account.account_type in ["Receivable", "Payable"] and (
				not row.get("party_type") or not row.get("party")
			):
				frappe.throw(_("Contact is required for receivable or payable accounts."))
			results.append(
				{
					"bank_transaction": transaction.name,
					"status": "valid",
					"message": _("Ready"),
				}
			)
		except Exception as exc:
			results.append(_row_exception_error(row, exc, "Bank Rec cash coding preview failed"))

	return {"results": results}


@frappe.whitelist()
def submit_cash_coding(rows):
	require_bank_rec_permission()
	rows = _parse_rows(rows)
	if not rows:
		frappe.throw(_("Select at least one row."))

	settings = get_abr_default_settings()
	entry_type = settings.get("default_journal_entry_type") or "Bank Entry"
	results = []

	for index, row in enumerate(rows):
		savepoint = "cash_coding_row_{0}".format(index)
		frappe.db.savepoint(savepoint)
		try:
			transaction = assert_bank_transaction_access(
				row.get("bank_transaction_name"),
				ptype="write",
			)
			_lock_bank_transaction(transaction.name)
			transaction.reload()
			if transaction.status == "Reconciled" or flt(transaction.unallocated_amount) <= 0:
				frappe.throw(_("This bank transaction is already reconciled."))

			company = transaction.company or frappe.get_cached_value(
				"Bank Account",
				transaction.bank_account,
				"company",
			)
			assert_company_access(company)
			assert_party_access(row.get("party_type"), row.get("party"))
			account = _assert_account(row.get("account"), company)
			if account.account_type in ["Receivable", "Payable"] and (
				not row.get("party_type") or not row.get("party")
			):
				frappe.throw(_("Contact is required for receivable or payable accounts."))

			updated_transaction = create_journal_entry_bts(
				bank_transaction_name=transaction.name,
				reference_number=row.get("reference_number") or transaction.reference_number or transaction.name,
				reference_date=row.get("reference_date") or transaction.date,
				posting_date=row.get("posting_date") or transaction.date,
				entry_type=entry_type,
				second_account=account.name,
				party_type=row.get("party_type"),
				party=row.get("party"),
				cost_center=row.get("cost_center"),
				project=row.get("project"),
				dimensions=row.get("dimensions"),
			)
			results.append(_row_success(row, updated_transaction))
			frappe.db.release_savepoint(savepoint)
		except Exception as exc:
			frappe.db.rollback(save_point=savepoint)
			results.append(_row_exception_error(row, exc, "Bank Rec cash coding submit failed"))

	return {
		"results": results,
		"summary": {
			"total": len(results),
			"success": len([row for row in results if row["status"] == "success"]),
			"error": len([row for row in results if row["status"] == "error"]),
		},
	}
