import frappe
from frappe import _

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	unreconcile_bank_transaction,
)
from advanced_bank_reconciliation.api.bank_rec import _get_filtered_transactions, _transaction_to_dto
from advanced_bank_reconciliation.api.matching import as_bool, _linked_payment_dto, _lock_bank_transaction
from advanced_bank_reconciliation.api.permission import (
	assert_bank_account_access,
	assert_bank_transaction_access,
	log_unexpected_api_exception,
	require_bank_rec_permission,
)


@frappe.whitelist()
def get_matched_transactions(bank_account, from_date=None, to_date=None):
	assert_bank_account_access(bank_account)
	rows = _get_filtered_transactions(
		bank_account=bank_account,
		from_date=from_date,
		to_date=to_date,
		status="reconciled",
	)

	return {"rows": rows}


@frappe.whitelist()
def unreconcile_transaction(bank_transaction_name, cancel_linked_documents=False):
	try:
		return _unreconcile_transaction(bank_transaction_name, cancel_linked_documents)
	except Exception as exc:
		log_unexpected_api_exception(exc, "Bank Rec unreconcile_transaction failed")
		raise


def _unreconcile_transaction(bank_transaction_name, cancel_linked_documents=False):
	require_bank_rec_permission()
	cancel_linked_documents = as_bool(cancel_linked_documents)
	transaction = assert_bank_transaction_access(bank_transaction_name, ptype="write")
	_lock_bank_transaction(transaction.name)
	transaction.reload()

	if not transaction.get("payment_entries"):
		frappe.throw(_("This bank transaction has no linked payments to unreconcile."))

	unreconcile_bank_transaction(
		bank_transaction_name=transaction.name,
		cancel_linked_documents=cancel_linked_documents,
	)
	transaction.reload()

	return {
		"transaction": _transaction_to_dto(transaction.as_dict(), status=transaction.status),
		"linked_payments": _linked_payment_dto(transaction),
		"cancel_linked_documents": cancel_linked_documents,
	}
