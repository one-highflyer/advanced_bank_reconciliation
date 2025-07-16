# Copyright (c) 2024, High Flyer and contributors
# For license information, please see license.txt
import json

import logging
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import cint, flt, getdate

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.bank_transaction.bank_transaction import get_total_allocated_amount
from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	get_amounts_not_reflected_in_system,
	get_entries,
)
from erpnext.accounts.utils import get_balance_on
from erpnext.setup.utils import get_exchange_rate

logger = frappe.logger("bank_rec", allow_site=True)
logger.setLevel(logging.INFO)

class AdvanceBankReconciliationTool(Document):
	pass


@frappe.whitelist()
def get_doctypes_for_bank_reconciliation():
	"""Return available document types for bank reconciliation."""
	return [
		"Payment Entry",
		"Journal Entry", 
		"Sales Invoice",
		"Purchase Invoice",
		"Unpaid Sales Invoice",
		"Unpaid Purchase Invoice",
		"Bank Transaction"
	]


@frappe.whitelist()
def get_bank_transactions(bank_account, from_date=None, to_date=None):
	# returns bank transactions for a bank account
	filters = []
	filters.append(["bank_account", "=", bank_account])
	filters.append(["docstatus", "=", 1])
	filters.append(["unallocated_amount", ">", 0.0])
	if to_date:
		filters.append(["date", "<=", to_date])
	if from_date:
		filters.append(["date", ">=", from_date])
	transactions = frappe.get_all(
		"Bank Transaction",
		fields=[
			"date",
			"deposit",
			"withdrawal",
			"currency",
			"description",
			"name",
			"bank_account",
			"company",
			"unallocated_amount",
			"reference_number",
			"party_type",
			"party",
		],
		filters=filters,
		order_by="date",
	)
	return transactions

@frappe.whitelist()
def get_reconciled_bank_transactions(bank_account, from_date=None, to_date=None):
	bank_transaction = frappe.qb.DocType("Bank Transaction")
	bt_payments = frappe.qb.DocType("Bank Transaction Payments")

	query = (
		frappe.qb.from_(bank_transaction)
		.select(
			bank_transaction.name,
			bank_transaction.date,
			bank_transaction.deposit,
			bank_transaction.withdrawal,
			bank_transaction.currency,
			bank_transaction.description,
			bank_transaction.bank_account,
			bank_transaction.company,
			bank_transaction.unallocated_amount,
			bank_transaction.reference_number,
			bank_transaction.party_type,
			bank_transaction.party,
			bt_payments.payment_document,
			bt_payments.payment_entry,
			bt_payments.allocated_amount,
		)
		.left_join(bt_payments).on(bank_transaction.name == bt_payments.parent)
		.where(bank_transaction.bank_account == bank_account)
		.where(bank_transaction.docstatus == 1)
		.where(bank_transaction.unallocated_amount == 0.0)
		.orderby(bank_transaction.date)
	)

	if to_date:
		query = query.where(bank_transaction.date <= to_date)
	if from_date:
		query = query.where(bank_transaction.date >= from_date)

	transactions = query.run(as_dict=True)
	return transactions

@frappe.whitelist()
def get_account_balance(bank_account, till_date):
	# returns account balance till the specified date
	account = frappe.db.get_value("Bank Account", bank_account, "account")
	filters = frappe._dict({"account": account, "report_date": till_date, "include_pos_transactions": 1})
	data = get_entries(filters)

	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0.0, 0.0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = get_amounts_not_reflected_in_system(filters)

	bank_bal = (
		flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) + amounts_not_reflected_in_system
	)

	return bank_bal


@frappe.whitelist()
def update_bank_transaction(bank_transaction_name, reference_number, party_type=None, party=None):
	# updates bank transaction based on the new parameters provided by the user from Vouchers
	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	bank_transaction.reference_number = reference_number
	bank_transaction.party_type = party_type
	bank_transaction.party = party
	bank_transaction.save()
	return frappe.db.get_all(
		"Bank Transaction",
		filters={"name": bank_transaction_name},
		fields=[
			"date",
			"deposit",
			"withdrawal",
			"currency",
			"description",
			"name",
			"bank_account",
			"company",
			"unallocated_amount",
			"reference_number",
			"party_type",
			"party",
		],
	)[0]


@frappe.whitelist()
def create_journal_entry_bts(
	bank_transaction_name,
	reference_number=None,
	reference_date=None,
	posting_date=None,
	entry_type=None,
	second_account=None,
	mode_of_payment=None,
	party_type=None,
	party=None,
	allow_edit=None,
):
	# Create a new journal entry based on the bank transaction
	bank_transaction = frappe.db.get_values(
		"Bank Transaction",
		bank_transaction_name,
		fieldname=["name", "deposit", "withdrawal", "bank_account", "currency", "unallocated_amount"],
		as_dict=True,
	)[0]
	company_account = frappe.get_value("Bank Account", bank_transaction.bank_account, "account")
	account_type = frappe.db.get_value("Account", second_account, "account_type")
	if account_type in ["Receivable", "Payable"]:
		if not (party_type and party):
			frappe.throw(
				_("Party Type and Party is required for Receivable / Payable account {0}").format(
					second_account
				)
			)

	company = frappe.get_value("Account", company_account, "company")
	company_default_currency = frappe.get_cached_value("Company", company, "default_currency")
	company_account_currency = frappe.get_cached_value("Account", company_account, "account_currency")
	second_account_currency = frappe.get_cached_value("Account", second_account, "account_currency")

	# determine if multi-currency Journal or not
	is_multi_currency = (
		True
		if company_default_currency != company_account_currency
		or company_default_currency != second_account_currency
		or company_default_currency != bank_transaction.currency
		else False
	)

	# Use unallocated_amount for the journal entry
	unallocated_amount = bank_transaction.unallocated_amount
	# Determine direction (deposit or withdrawal)
	if bank_transaction.deposit > 0.0:
		deposit = unallocated_amount
		withdrawal = 0.0
	else:
		deposit = 0.0
		withdrawal = unallocated_amount

	accounts = []
	second_account_dict = {
		"account": second_account,
		"account_currency": second_account_currency,
		"credit_in_account_currency": deposit,
		"debit_in_account_currency": withdrawal,
		"party_type": party_type,
		"party": party,
		"cost_center": get_default_cost_center(company),
	}

	company_account_dict = {
		"account": company_account,
		"account_currency": company_account_currency,
		"bank_account": bank_transaction.bank_account,
		"credit_in_account_currency": withdrawal,
		"debit_in_account_currency": deposit,
		"cost_center": get_default_cost_center(company),
	}

	# convert transaction amount to company currency
	if is_multi_currency:
		exc_rate = get_exchange_rate(bank_transaction.currency, company_default_currency, posting_date)
		withdrawal_in_company_currency = flt(exc_rate * abs(withdrawal))
		deposit_in_company_currency = flt(exc_rate * abs(deposit))
	else:
		withdrawal_in_company_currency = withdrawal
		deposit_in_company_currency = deposit

	# if second account is of foreign currency, convert and set debit and credit fields.
	if second_account_currency != company_default_currency:
		exc_rate = get_exchange_rate(second_account_currency, company_default_currency, posting_date)
		second_account_dict.update(
			{
				"exchange_rate": exc_rate,
				"credit": deposit_in_company_currency,
				"debit": withdrawal_in_company_currency,
				"credit_in_account_currency": flt(deposit_in_company_currency / exc_rate) or 0,
				"debit_in_account_currency": flt(withdrawal_in_company_currency / exc_rate) or 0,
			}
		)
	else:
		second_account_dict.update(
			{
				"exchange_rate": 1,
				"credit": deposit_in_company_currency,
				"debit": withdrawal_in_company_currency,
				"credit_in_account_currency": deposit_in_company_currency,
				"debit_in_account_currency": withdrawal_in_company_currency,
			}
		)

	# if company account is of foreign currency, convert and set debit and credit fields.
	if company_account_currency != company_default_currency:
		exc_rate = get_exchange_rate(company_account_currency, company_default_currency, posting_date)
		company_account_dict.update(
			{
				"exchange_rate": exc_rate,
				"credit": withdrawal_in_company_currency,
				"debit": deposit_in_company_currency,
			}
		)
	else:
		company_account_dict.update(
			{
				"exchange_rate": 1,
				"credit": withdrawal_in_company_currency,
				"debit": deposit_in_company_currency,
				"credit_in_account_currency": withdrawal_in_company_currency,
				"debit_in_account_currency": deposit_in_company_currency,
			}
		)

	accounts.append(second_account_dict)
	accounts.append(company_account_dict)

	journal_entry_dict = {
		"voucher_type": entry_type,
		"company": company,
		"posting_date": posting_date,
		"cheque_date": reference_date,
		"cheque_no": reference_number,
		"mode_of_payment": mode_of_payment,
	}
	if is_multi_currency:
		journal_entry_dict.update({"multi_currency": True})

	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.update(journal_entry_dict)
	journal_entry.set("accounts", accounts)

	if allow_edit:
		return journal_entry

	journal_entry.insert()
	journal_entry.submit()

	paid_amount = unallocated_amount

	vouchers = json.dumps(
		[
			{
				"payment_doctype": "Journal Entry",
				"payment_name": journal_entry.name,
				"amount": paid_amount,
			}
		]
	)

	return reconcile_vouchers(bank_transaction_name, vouchers)


@frappe.whitelist()
def create_payment_entry_bts(
	bank_transaction_name,
	reference_number=None,
	reference_date=None,
	party_type=None,
	party=None,
	posting_date=None,
	mode_of_payment=None,
	project=None,
	cost_center=None,
	allow_edit=None,
):
	# Create a new payment entry based on the bank transaction
	bank_transaction = frappe.db.get_values(
		"Bank Transaction",
		bank_transaction_name,
		fieldname=["name", "unallocated_amount", "deposit", "bank_account"],
		as_dict=True,
	)[0]
	paid_amount = bank_transaction.unallocated_amount
	payment_type = "Receive" if bank_transaction.deposit > 0.0 else "Pay"

	company_account = frappe.get_value("Bank Account", bank_transaction.bank_account, "account")
	company = frappe.get_value("Account", company_account, "company")
	payment_entry_dict = {
		"company": company,
		"payment_type": payment_type,
		"reference_no": reference_number,
		"reference_date": reference_date,
		"party_type": party_type,
		"party": party,
		"posting_date": posting_date,
		"paid_amount": paid_amount,
		"received_amount": paid_amount,
	}
	payment_entry = frappe.new_doc("Payment Entry")

	payment_entry.update(payment_entry_dict)

	if mode_of_payment:
		payment_entry.mode_of_payment = mode_of_payment
	if project:
		payment_entry.project = project
	if cost_center:
		payment_entry.cost_center = cost_center
	if payment_type == "Receive":
		payment_entry.paid_to = company_account
	else:
		payment_entry.paid_from = company_account

	payment_entry.validate()

	if allow_edit:
		return payment_entry

	payment_entry.insert()

	payment_entry.submit()
	vouchers = json.dumps(
		[
			{
				"payment_doctype": "Payment Entry",
				"payment_name": payment_entry.name,
				"amount": paid_amount,
			}
		]
	)
	return reconcile_vouchers(bank_transaction_name, vouchers)


@frappe.whitelist()
def auto_reconcile_vouchers(
	bank_account,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
):
	frappe.flags.auto_reconcile_vouchers = True
	document_types = ["payment_entry", "journal_entry"]
	bank_transactions = get_bank_transactions(bank_account)
	matched_transaction = []
	for transaction in bank_transactions:
		linked_payments = get_linked_payments(
			transaction.name,
			document_types,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
		)
		vouchers = []
		for r in linked_payments:
			vouchers.append(
				{
					"payment_doctype": r[1],
					"payment_name": r[2],
					"amount": r[4],
				}
			)
		transaction = frappe.get_doc("Bank Transaction", transaction.name)
		account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
		for voucher in vouchers:
			gl_entry = frappe.db.get_value(
				"GL Entry",
				dict(
					account=account,
					voucher_type=voucher["payment_doctype"],
					voucher_no=voucher["payment_name"],
				),
				["credit", "debit"],
				as_dict=1,
			)
			gl_amount, transaction_amount = (
				(gl_entry.credit, transaction.deposit)
				if gl_entry.credit > 0
				else (gl_entry.debit, transaction.withdrawal)
			)
			allocated_amount = gl_amount if gl_amount >= transaction_amount else transaction_amount
			transaction.append(
				"payment_entries",
				{
					"payment_document": voucher["payment_doctype"],
					"payment_entry": voucher["payment_name"],
					"allocated_amount": allocated_amount,
				},
			)
			matched_transaction.append(str(transaction.name))
		transaction.save()
		transaction.update_allocations()
	matched_transaction_len = len(set(matched_transaction))
	if matched_transaction_len == 0:
		frappe.msgprint(_("No matching references found for auto reconciliation"))
	elif matched_transaction_len == 1:
		frappe.msgprint(_("{0} transaction is reconcilied").format(matched_transaction_len))
	else:
		frappe.msgprint(_("{0} transactions are reconcilied").format(matched_transaction_len))

	frappe.flags.auto_reconcile_vouchers = False

	return frappe.get_doc("Bank Transaction", transaction.name)


@frappe.whitelist()
def reconcile_vouchers(bank_transaction_name, vouchers):
	# updated clear date of all the vouchers based on the bank transaction
	vouchers = json.loads(vouchers)
	transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	transaction.add_payment_entries(vouchers)
	return frappe.get_doc("Bank Transaction", bank_transaction_name)


@frappe.whitelist()
def get_linked_payments(
	bank_transaction_name,
	document_types=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
):
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	print(f"Getting payment entries from {from_date} to {to_date} with bank account")
	# get all matching payments for a bank transaction
	transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	bank_account = frappe.db.get_values(
		"Bank Account", transaction.bank_account, ["account", "company"], as_dict=True
	)[0]
	(gl_account, company) = (bank_account.account, bank_account.company)
	matching = check_matching(
		gl_account,
		company,
		transaction,
		document_types,
		from_date,
		to_date,
		filter_by_reference_date,
		from_reference_date,
		to_reference_date,
	)
	return subtract_allocations(gl_account, matching)


def subtract_allocations(gl_account, vouchers):
	"Look up & subtract any existing Bank Transaction allocations"
	copied = []

	voucher_docs = [(voucher[1], voucher[2]) for voucher in vouchers]
	voucher_allocated_amounts = get_total_allocated_amount(voucher_docs)

	for voucher in vouchers:
		rows = voucher_allocated_amounts.get((voucher[1], voucher[2])) or []
		amount = None
		for row in rows:
			if row["gl_account"] == gl_account:
				amount = row["total"]
				break

		if amount:
			l = list(voucher)
			l[3] -= amount
			copied.append(tuple(l))
		else:
			copied.append(voucher)
	return copied


def check_matching(
	bank_account,
	company,
	transaction,
	document_types,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
):
	exact_match = True if "exact_match" in document_types else False
	# combine all types of vouchers
	subquery = get_queries(
		bank_account,
		company,
		transaction,
		document_types,
		from_date,
		to_date,
		filter_by_reference_date,
		from_reference_date,
		to_reference_date,
		exact_match,
	)
	filters = {
		"amount": transaction.unallocated_amount,
		# "payment_type": ["Receive", "Pay"],
		"reference_no": transaction.reference_number,
		"party_type": transaction.party_type,
		"party": transaction.party,
		"bank_account": bank_account,
	}

	matching_vouchers = []

	matching_vouchers.extend(
		get_loan_vouchers(bank_account, transaction, document_types, filters, exact_match)
	)

	for query in subquery:
		matching_vouchers.extend(
			frappe.db.sql(
				query,
				filters,
			)
		)
	return sorted(matching_vouchers, key=lambda x: x[0], reverse=True) if matching_vouchers else []


def get_queries(
	bank_account,
	company,
	transaction,
	document_types,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
	exact_match,
):
	# get queries to get matching vouchers
	account_from_to = "paid_to" if transaction.deposit > 0.0 else "paid_from"
	queries = []

	# get matching queries from all the apps
	for method_name in frappe.get_hooks("get_matching_queries", app_name="advanced_bank_reconciliation"):
		print(f"Matching queries: {method_name}")
		queries.extend(
			frappe.get_attr(method_name)(
				bank_account,
				company,
				transaction,
				document_types,
				exact_match,
				account_from_to,
				from_date,
				to_date,
				filter_by_reference_date,
				from_reference_date,
				to_reference_date,
			)
			or []
		)

	return queries


def get_matching_queries(
	bank_account,
	company,
	transaction,
	document_types,
	exact_match,
	account_from_to,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
):
	queries = []
	if "payment_entry" in document_types:
		query = get_pe_matching_query(
			exact_match,
			account_from_to,
			transaction,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
		)
		queries.append(query)

	if "journal_entry" in document_types:
		query = get_je_matching_query(
			exact_match,
			transaction,
			from_date,
			to_date,
			filter_by_reference_date,
			from_reference_date,
			to_reference_date,
		)
		queries.append(query)

	if transaction.deposit > 0.0 and "sales_invoice" in document_types:
		query = get_si_matching_query(exact_match)
		queries.append(query)
	
	if transaction.deposit > 0.0 and "unpaid_sales_invoice" in document_types:
		query = get_unpaid_si_matching_query(exact_match)
		queries.append(query)

	if transaction.withdrawal > 0.0:
		if "purchase_invoice" in document_types:
			query = get_pi_matching_query(exact_match)
			queries.append(query)
		
		if "unpaid_purchase_invoice" in document_types:
			query = get_unpaid_pi_matching_query(exact_match)
			queries.append(query)

	if "bank_transaction" in document_types:
		query = get_bt_matching_query(exact_match, transaction)
		queries.append(query)

	return queries


def get_loan_vouchers(bank_account, transaction, document_types, filters, exact_match):
	vouchers = []

	if transaction.withdrawal > 0.0 and "loan_disbursement" in document_types:
		vouchers.extend(get_ld_matching_query(bank_account, exact_match, filters))

	if transaction.deposit > 0.0 and "loan_repayment" in document_types:
		vouchers.extend(get_lr_matching_query(bank_account, exact_match, filters))

	return vouchers


def get_bt_matching_query(exact_match, transaction):
	# get matching bank transaction query
	# find bank transactions in the same bank account with opposite sign
	# same bank account must have same company and currency
	field = "deposit" if transaction.withdrawal > 0.0 else "withdrawal"

	return f"""

		SELECT
			(CASE WHEN reference_number = %(reference_no)s THEN 1 ELSE 0 END
			+ CASE WHEN {field} = %(amount)s THEN 1 ELSE 0 END
			+ CASE WHEN ( party_type = %(party_type)s AND party = %(party)s ) THEN 1 ELSE 0 END
			+ CASE WHEN unallocated_amount = %(amount)s THEN 1 ELSE 0 END
			+ 1) AS rank,
			'Bank Transaction' AS doctype,
			name,
			unallocated_amount AS paid_amount,
			reference_number AS reference_no,
			date AS reference_date,
			party,
			party_type,
			date AS posting_date,
			currency
		FROM
			`tabBank Transaction`
		WHERE
			status != 'Reconciled'
			AND name != '{transaction.name}'
			AND bank_account = '{transaction.bank_account}'
			AND {field} {'= %(amount)s' if exact_match else '> 0.0'}
	"""


def get_ld_matching_query(bank_account, exact_match, filters):
	loan_disbursement = frappe.qb.DocType("Loan Disbursement")
	matching_reference = loan_disbursement.reference_number == filters.get("reference_number")
	matching_party = loan_disbursement.applicant_type == filters.get(
		"party_type"
	) and loan_disbursement.applicant == filters.get("party")

	rank = frappe.qb.terms.Case().when(matching_reference, 1).else_(0)

	rank1 = frappe.qb.terms.Case().when(matching_party, 1).else_(0)

	query = (
		frappe.qb.from_(loan_disbursement)
		.select(
			rank + rank1 + 1,
			ConstantColumn("Loan Disbursement").as_("doctype"),
			loan_disbursement.name,
			loan_disbursement.disbursed_amount,
			loan_disbursement.reference_number,
			loan_disbursement.reference_date,
			loan_disbursement.applicant_type,
			loan_disbursement.disbursement_date,
		)
		.where(loan_disbursement.docstatus == 1)
		.where(loan_disbursement.clearance_date.isnull())
		.where(loan_disbursement.disbursement_account == bank_account)
	)

	if exact_match:
		query.where(loan_disbursement.disbursed_amount == filters.get("amount"))
	else:
		query.where(loan_disbursement.disbursed_amount > 0.0)

	vouchers = query.run(as_list=True)

	return vouchers


def get_lr_matching_query(bank_account, exact_match, filters):
	loan_repayment = frappe.qb.DocType("Loan Repayment")
	matching_reference = loan_repayment.reference_number == filters.get("reference_number")
	matching_party = loan_repayment.applicant_type == filters.get(
		"party_type"
	) and loan_repayment.applicant == filters.get("party")

	rank = frappe.qb.terms.Case().when(matching_reference, 1).else_(0)

	rank1 = frappe.qb.terms.Case().when(matching_party, 1).else_(0)

	query = (
		frappe.qb.from_(loan_repayment)
		.select(
			rank + rank1 + 1,
			ConstantColumn("Loan Repayment").as_("doctype"),
			loan_repayment.name,
			loan_repayment.amount_paid,
			loan_repayment.reference_number,
			loan_repayment.reference_date,
			loan_repayment.applicant_type,
			loan_repayment.posting_date,
		)
		.where(loan_repayment.docstatus == 1)
		.where(loan_repayment.clearance_date.isnull())
		.where(loan_repayment.payment_account == bank_account)
	)

	if frappe.db.has_column("Loan Repayment", "repay_from_salary"):
		query = query.where(loan_repayment.repay_from_salary == 0)

	if exact_match:
		query.where(loan_repayment.amount_paid == filters.get("amount"))
	else:
		query.where(loan_repayment.amount_paid > 0.0)

	vouchers = query.run()

	return vouchers


def get_pe_matching_query(
	exact_match,
	account_from_to,
	transaction,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
):
	# get matching payment entries query
	# Handle multi-currency scenarios by calculating amounts in bank account currency
	
	# Simplified logic: 
	# - For Receive payments: use received_amount (already in bank account currency)
	# - For Pay payments: use paid_amount (already in bank account currency)
	if transaction.deposit > 0.0:
		# For deposits (bank transaction deposits), we want Receive payments where bank is paid_to
		currency_field = "paid_to_account_currency as currency"
		amount_field = "CASE WHEN payment_type = 'Receive' AND paid_to = %(bank_account)s THEN received_amount ELSE 0 END"
		amount_comparison = amount_field
	else:
		# For withdrawals (bank transaction withdrawals), we want Pay payments where bank is paid_from
		currency_field = "paid_from_account_currency as currency"
		amount_field = "CASE WHEN payment_type = 'Pay' AND paid_from = %(bank_account)s THEN paid_amount ELSE 0 END"
		amount_comparison = amount_field
	
	filter_by_date = f"AND posting_date between '{from_date}' and '{to_date}'"
	order_by = " posting_date"
	filter_by_reference_no = ""
	if cint(filter_by_reference_date):
		filter_by_date = f"AND reference_date between '{from_reference_date}' and '{to_reference_date}'"
		order_by = " reference_date"
	if frappe.flags.auto_reconcile_vouchers is True:
		filter_by_reference_no = f"AND reference_no = '{transaction.reference_number}'"
	return f"""
		SELECT
			(CASE WHEN reference_no=%(reference_no)s THEN 1 ELSE 0 END
			+ CASE WHEN (party_type = %(party_type)s AND party = %(party)s ) THEN 1 ELSE 0 END
			+ CASE WHEN ABS(({amount_comparison}) - %(amount)s) < 0.01 THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Payment Entry' as doctype,
			name,
			IF(payment_type = 'Pay', 
				{f'-({amount_field})' if transaction.deposit > 0.0 else f'({amount_field})'},
				{f'({amount_field})' if transaction.deposit > 0.0 else f'-({amount_field})'}
			) AS paid_amount,
			reference_no,
			reference_date,
			party,
			party_type,
			posting_date,
			{currency_field}
		FROM
			`tabPayment Entry`
		WHERE
			docstatus = 1
			AND payment_type IN ('Pay', 'Receive', 'Internal Transfer')
			AND ifnull(clearance_date, '') = ""
			AND (paid_from = %(bank_account)s OR paid_to = %(bank_account)s) 
			AND {f'({amount_comparison}) {"= %(amount)s" if exact_match else "> 0.0"}'}
			{filter_by_date}
			{filter_by_reference_no}
		order by{order_by}
	"""


def get_je_matching_query(
	exact_match,
	transaction,
	from_date,
	to_date,
	filter_by_reference_date,
	from_reference_date,
	to_reference_date,
):
	# get matching journal entry query
	# We have mapping at the bank level
	# So one bank could have both types of bank accounts like asset and liability
	# So cr_or_dr should be judged only on basis of withdrawal and deposit and not account type
	filter_by_date = f"AND je.posting_date between '{from_date}' and '{to_date}'"
	order_by = " je.posting_date"
	filter_by_reference_no = ""
	if cint(filter_by_reference_date):
		filter_by_date = f"AND je.cheque_date between '{from_reference_date}' and '{to_reference_date}'"
		order_by = " je.cheque_date"
	if frappe.flags.auto_reconcile_vouchers is True:
		filter_by_reference_no = f"AND je.cheque_no = '{transaction.reference_number}'"
	return f"""
		SELECT
			(CASE WHEN je.cheque_no=%(reference_no)s THEN 1 ELSE 0 END
			+ CASE WHEN jea.debit_in_account_currency = %(amount)s THEN 1 ELSE 0 END
            + CASE WHEN jea.credit_in_account_currency = %(amount)s THEN 1 ELSE 0 END
            + 1) AS rank ,
			'Journal Entry' AS doctype,
			je.name,
			IF(jea.debit_in_account_currency > 0, 
                IF({transaction.deposit} > 0, jea.debit_in_account_currency, -jea.debit_in_account_currency), 
                IF({transaction.deposit} > 0, -jea.credit_in_account_currency, jea.credit_in_account_currency)
            ) AS paid_amount,
			je.cheque_no AS reference_no,
			je.cheque_date AS reference_date,
			je.pay_to_recd_from AS party,
			jea.party_type,
			je.posting_date,
			jea.account_currency AS currency
		FROM
			`tabJournal Entry Account` AS jea
		JOIN
			`tabJournal Entry` AS je
		ON
			jea.parent = je.name
		WHERE
			je.docstatus = 1
			AND je.voucher_type NOT IN ('Opening Entry')
			AND (je.clearance_date IS NULL OR je.clearance_date='0000-00-00')
			AND jea.account = %(bank_account)s
			AND (jea.debit_in_account_currency {'= %(amount)s' if exact_match else '> 0.0'}
            OR jea.credit_in_account_currency {'= %(amount)s' if exact_match else '> 0.0'})
			AND je.docstatus = 1
			{filter_by_date}
			{filter_by_reference_no}
			order by {order_by}
	"""


def get_si_matching_query(exact_match):
	# get matching sales invoice query
	return f"""
		SELECT
			( CASE WHEN si.customer = %(party)s  THEN 1 ELSE 0 END
			+ CASE WHEN sip.amount = %(amount)s THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Sales Invoice' as doctype,
			si.name,
			sip.amount as paid_amount,
			'' as reference_no,
			'' as reference_date,
			si.customer as party,
			'Customer' as party_type,
			si.posting_date,
			si.currency

		FROM
			`tabSales Invoice Payment` as sip
		JOIN
			`tabSales Invoice` as si
		ON
			sip.parent = si.name
		WHERE
			si.docstatus = 1
			AND (sip.clearance_date is null or sip.clearance_date='0000-00-00')
			AND sip.account = %(bank_account)s
			AND sip.amount {'= %(amount)s' if exact_match else '> 0.0'}
	"""


def get_pi_matching_query(exact_match):
	# get matching purchase invoice query when they are also used as payment entries (is_paid)
	return f"""
		SELECT
			( CASE WHEN supplier = %(party)s THEN 1 ELSE 0 END
			+ CASE WHEN paid_amount = %(amount)s THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Purchase Invoice' as doctype,
			name,
			paid_amount,
			'' as reference_no,
			'' as reference_date,
			supplier as party,
			'Supplier' as party_type,
			posting_date,
			currency
		FROM
			`tabPurchase Invoice`
		WHERE
			docstatus = 1
			AND is_paid = 1
			AND ifnull(clearance_date, '') = ""
			AND cash_bank_account = %(bank_account)s
			AND paid_amount {'= %(amount)s' if exact_match else '> 0.0'}
	"""


def get_unpaid_si_matching_query(exact_match):
	# get matching unpaid sales invoice query
	return f"""
		SELECT
			( CASE WHEN customer = %(party)s THEN 1 ELSE 0 END
			+ CASE WHEN outstanding_amount = %(amount)s THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Unpaid Sales Invoice' as doctype,
			name,
			outstanding_amount as paid_amount,
			'' as reference_no,
			posting_date as reference_date,
			customer as party,
			'Customer' as party_type,
			posting_date,
			currency
		FROM
			`tabSales Invoice`
		WHERE
			docstatus = 1
			AND status NOT IN ('Paid', 'Cancelled', 'Credit Note Issued')
			AND outstanding_amount {'= %(amount)s' if exact_match else '> 0.0'}
		ORDER BY posting_date DESC
	"""


def get_unpaid_pi_matching_query(exact_match):
	# get matching unpaid purchase invoice query
	return f"""
		SELECT
			( CASE WHEN supplier = %(party)s THEN 1 ELSE 0 END
			+ CASE WHEN outstanding_amount = %(amount)s THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Unpaid Purchase Invoice' as doctype,
			name,
			outstanding_amount as paid_amount,
			'' as reference_no,
			posting_date as reference_date,
			supplier as party,
			'Supplier' as party_type,
			posting_date,
			currency
		FROM
			`tabPurchase Invoice`
		WHERE
			docstatus = 1
			AND status NOT IN ('Paid', 'Cancelled', 'Debit Note Issued')
			AND outstanding_amount {'= %(amount)s' if exact_match else '> 0.0'}
		ORDER BY posting_date DESC
	"""


@frappe.whitelist()
def create_payment_entries_for_invoices(bank_transaction_name, invoices, auto_reconcile=True):
	"""Create payment entries for unpaid invoices and optionally reconcile them with the bank transaction."""
	import json
	
	if isinstance(invoices, str):
		invoices = json.loads(invoices)
	
	if isinstance(auto_reconcile, str):
		auto_reconcile = auto_reconcile.lower() in ['true', '1', 'yes']
	
	bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
	
	if not invoices:
		frappe.throw(_("No invoices selected for payment entry creation"))
	
	vouchers = []
	created_payment_entries = []
	
	for invoice_data in invoices:
		invoice_name = invoice_data.get("name")
		invoice_type = invoice_data.get("doctype")
		allocated_amount = flt(invoice_data.get("allocated_amount", 0))
		
		if not invoice_name or not invoice_type or allocated_amount <= 0:
			continue
			
		# Determine the actual doctype (remove 'Unpaid ' prefix)
		actual_doctype = invoice_type.replace("Unpaid ", "")
		
		# Get the invoice document
		invoice_doc = frappe.get_doc(actual_doctype, invoice_name)
		
		# Determine payment type based on invoice type
		if actual_doctype == "Sales Invoice":
			payment_type = "Receive"
			party_type = "Customer"
			party = invoice_doc.customer
		else:  # Purchase Invoice
			payment_type = "Pay"
			party_type = "Supplier"
			party = invoice_doc.supplier
		
		# Create payment entry
		payment_entry = create_payment_entry_for_invoice(
			invoice_doc,
			bank_transaction,
			allocated_amount,
			payment_type,
			party_type,
			party
		)
		
		created_payment_entries.append(payment_entry.name)
		
		vouchers.append({
			"payment_doctype": "Payment Entry",
			"payment_name": payment_entry.name,
			"amount": allocated_amount
		})
	
	if not vouchers:
		frappe.throw(_("No valid payment entries created"))
	
	# Optionally reconcile the vouchers with the bank transaction
	if auto_reconcile:
		return reconcile_vouchers(bank_transaction_name, json.dumps(vouchers))
	else:
		# Return the created payment entries for further processing
		return {
			"payment_entries": created_payment_entries,
			"vouchers": vouchers
		}


def create_payment_entry_for_invoice(invoice_doc, bank_transaction, allocated_amount, payment_type, party_type, party):
	"""Create a payment entry for an unpaid invoice."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	
	# Get the bank account from bank transaction
	bank_account_doc = frappe.get_doc("Bank Account", bank_transaction.bank_account)
	bank_gl_account = bank_account_doc.account
	
	# Get payment entry template from the invoice
	payment_entry = get_payment_entry(invoice_doc.doctype, invoice_doc.name)
	
	# Set the correct bank account based on payment type
	if payment_type == "Receive":
		payment_entry.paid_to = bank_gl_account
	else:  # Pay
		payment_entry.paid_from = bank_gl_account
	
	# Set the payment amount to the allocated amount
	payment_entry.paid_amount = allocated_amount
	payment_entry.received_amount = allocated_amount
	
	# Set reference details from bank transaction
	payment_entry.reference_no = bank_transaction.reference_number or bank_transaction.description
	payment_entry.reference_date = bank_transaction.date
	payment_entry.posting_date = bank_transaction.date
	
	# Update the references table to allocate only the specified amount
	if payment_entry.references:
		for ref in payment_entry.references:
			if ref.reference_name == invoice_doc.name:
				ref.allocated_amount = min(allocated_amount, ref.outstanding_amount)
				break
	
	# Validate the payment entry
	payment_entry.validate()
	
	# Save and submit the payment entry
	payment_entry.insert()
	payment_entry.submit()
	
	return payment_entry


@frappe.whitelist()
def get_cleared_balance(bank_account, from_date, till_date):
	print("Calculating cleared balance", bank_account, from_date, till_date)
	opening_balance = get_account_balance(bank_account, from_date)

	bank_transaction = frappe.qb.DocType("Bank Transaction")
	bt_payments = frappe.qb.DocType("Bank Transaction Payments")
	payment_entry = frappe.qb.DocType("Payment Entry")

	payment_entries = frappe.db.sql(
		"""
		select
			btp.payment_document,
			pe.name as payment_entry,
			CASE 
				WHEN pe.payment_type = 'Receive' AND pe.paid_to = %(account)s THEN pe.received_amount
				ELSE 0 
			END as debit,
			CASE 
				WHEN pe.payment_type = 'Pay' AND pe.paid_from = %(account)s THEN pe.paid_amount
				ELSE 0 
			END as credit,
			pe.posting_date, 
			ifnull(pe.party,if(pe.paid_from=%(account)s,pe.paid_to,pe.paid_from)) as against_account, 
			pe.clearance_date,
			if(pe.paid_to=%(account)s, pe.paid_to_account_currency, pe.paid_from_account_currency) as account_currency
		from `tabBank Transaction` as bt
		inner join `tabBank Transaction Payments` as btp on bt.name = btp.parent
		inner join `tabPayment Entry` as pe on btp.payment_entry = pe.name
		where
			bt.bank_account = %(account)s
			and bt.docstatus = 1
			and bt.unallocated_amount = 0.0
			and bt.date <= %(till_date)s
			and bt.date >= %(from_date)s
			and btp.payment_document = "Payment Entry"
		""",
		{
			"account": bank_account,
			"from_date": from_date,
			"till_date": till_date,
		},
		as_dict=True
	)

	journal_entries = frappe.db.sql(
		"""
		select
			btp.payment_document,
			je.name as payment_entry,
			jea.debit_in_account_currency as debit,
			jea.credit_in_account_currency as credit,
			je.cheque_no as reference_no, 
			je.cheque_date as ref_date, 
			je.clearance_date, 
			jea.account_currency

		from `tabBank Transaction` as bt
		inner join `tabBank Transaction Payments` as btp on bt.name = btp.parent
		inner join `tabJournal Entry` as je on btp.payment_entry = je.name
		inner join `tabJournal Entry Account` as jea on je.name = jea.parent
		where
			bt.bank_account = %(account)s
			and bt.docstatus = 1
			and bt.unallocated_amount = 0.0
			and bt.date <= %(till_date)s
			and bt.date >= %(from_date)s
			and btp.payment_document = "Journal Entry"
			and jea.account = %(account)s
			and ifnull(je.is_opening, 'No') = 'No'
		""",
		{
			"account": bank_account,
			"from_date": from_date,
			"till_date": till_date,
		},
		as_dict=True
	)

	# query = (
	# 	frappe.qb.from_(bank_transaction)
	# 	.select(
			
	# 	)
	# 	.inner_join(bt_payments).on(bank_transaction.name == bt_payments.parent)
	# 	.inner_join(payment_entry).on(bt_payments.payment_entry == payment_entry.name)
	# 	.where(bank_transaction.bank_account == bank_account)
	# 	.where(bank_transaction.docstatus == 1)
	# 	.where(bank_transaction.unallocated_amount == 0.0)
	# 	.where(bank_transaction.date <= till_date)
	# 	.where(bank_transaction.date >= from_date)
	# 	.where(bt_payments.payment_document == "Payment Entry")
	# )
 
	total_debit, total_credit = 0.0, 0.0
	for d in payment_entries:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)
	
	for d in journal_entries:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	print("debit and credit", total_debit, total_credit)
	
	cleared_balance = opening_balance + total_debit - total_credit
	return cleared_balance


@frappe.whitelist()
def validate_bank_transactions(from_date, to_date, company, bank_account):
	logger.info(f"Validating bank transactions from {from_date} to {to_date} for {company} and {bank_account}")

	bank_transaction = frappe.qb.DocType("Bank Transaction")
	bt_payment = frappe.qb.DocType("Bank Transaction Payments")
	payment_entry = frappe.qb.DocType("Payment Entry")

	# Get the bank account's GL account for filtering
	bank_gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
	
	# Use SQL query to get the correct payment amount based on payment type
	entries = frappe.db.sql(
		"""
		SELECT 
			bt.name,
			bt.date,
			bt.deposit,
			bt.withdrawal,
			bt.unallocated_amount,
			bt.party_type,
			bt.party,
			btp.payment_document,
			btp.payment_entry,
			btp.allocated_amount,
			pe.payment_type,
			CASE 
				WHEN pe.payment_type = 'Receive' AND pe.paid_to = %(bank_gl_account)s THEN pe.received_amount
				WHEN pe.payment_type = 'Pay' AND pe.paid_from = %(bank_gl_account)s THEN pe.paid_amount
				ELSE 0 
			END as payment_amount
		FROM `tabBank Transaction` as bt
		INNER JOIN `tabBank Transaction Payments` as btp ON bt.name = btp.parent
		INNER JOIN `tabPayment Entry` as pe ON btp.payment_entry = pe.name
		WHERE 
			bt.company = %(company)s
			AND bt.bank_account = %(bank_account)s
			AND bt.date >= %(from_date)s
			AND bt.date <= %(to_date)s
			AND bt.docstatus = 1
			AND btp.payment_document = 'Payment Entry'
			AND (pe.clearance_date IS NULL OR pe.clearance_date != bt.date)
		ORDER BY bt.date
		""",
		{
			"bank_gl_account": bank_gl_account,
			"company": company,
			"bank_account": bank_account,
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=True
	)

	logger.info(f"Found {len(entries)} entries with incorrect clearance date")
	for entry in entries:
		if entry.deposit > 0.0:
			if entry.payment_type == "Receive" and entry.allocated_amount == entry.payment_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Payment amount {entry.payment_amount}, Deposit {entry.deposit}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
			elif entry.payment_type == "Pay" and entry.allocated_amount == -entry.payment_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Payment amount {entry.payment_amount}, Deposit {entry.deposit}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
		else:
			if entry.payment_type == "Receive" and entry.allocated_amount == -entry.payment_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Payment amount {entry.payment_amount}, Withdrawal {entry.withdrawal}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
			elif entry.payment_type == "Pay" and entry.allocated_amount == entry.payment_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Payment amount {entry.payment_amount}, Withdrawal {entry.withdrawal}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)

	jle_allocations = frappe.db.sql(
		"""
		select 
					bt.name,
					btp.payment_entry,
					IF(bt.deposit > 0.0, btp.allocated_amount, -btp.allocated_amount) as allocated_amount
			from `tabBank Transaction` as bt
					inner join `tabBank Transaction Payments` as btp on bt.name = btp.parent
			where btp.payment_document = "Journal Entry"
							and bt.bank_account = %(bank_account)s
							and bt.docstatus = 1
							and bt.date <= %(to_date)s
							and bt.date >= %(from_date)s
		""",
		{
			"bank_account": bank_account,
			"from_date": from_date,
			"to_date": to_date
		},
		as_dict=True
	)
	logger.info(f"Found {len(jle_allocations)} journal entry allocations")

	jle_names = [d.payment_entry for d in jle_allocations]
	for jle_name in jle_names:
		clear_journal_entry(jle_name)

	return {"success": True}


@frappe.whitelist()
def validate_bank_transaction_async(bank_transaction_name):
	"""
	Validate a single bank transaction asynchronously using frappe.enqueue
	"""
	try:
		frappe.enqueue(
			"advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.validate_single_bank_transaction",
			bank_transaction_name=bank_transaction_name,
			queue='long',
			timeout=300,
			job_name="validate_bank_transaction_%s" % bank_transaction_name
		)
		logger.info("Enqueued validation job for bank transaction %s", bank_transaction_name)
		return {"success": True, "message": "Validation queued for bank transaction %s" % bank_transaction_name}
	except Exception as e:
		logger.error("Failed to enqueue validation for bank transaction %s: %s", bank_transaction_name, str(e), exc_info=True)
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def batch_validate_unvalidated_transactions(bank_account, from_date=None, to_date=None, limit=50):
	"""
	Find and validate bank transactions that might have missed automatic validation
	This is useful for maintenance and catching up on transactions that weren't validated
	"""
	try:
		try:
			limit = int(limit)
		except (ValueError, TypeError):
			limit = 50
		logger.info("Starting batch validation for bank account %s", bank_account)
		
		# Get company for the bank account
		company = frappe.db.get_value("Bank Account", bank_account, "company")
		bank_gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
		
		if not company or not bank_gl_account:
			return {"success": False, "error": "Invalid bank account %s" % bank_account}
		
		# Set default date range if not provided
		if not from_date:
			from_date = frappe.utils.add_days(frappe.utils.today(), -30)  # Last 30 days
		if not to_date:
			to_date = frappe.utils.today()
		
		# Find bank transactions with payment entries that don't have clearance dates set
		unvalidated_transactions = frappe.db.sql(
			f"""
			SELECT DISTINCT bt.name
			FROM `tabBank Transaction` bt
			INNER JOIN `tabBank Transaction Payments` btp ON bt.name = btp.parent
			INNER JOIN `tabPayment Entry` pe ON btp.payment_entry = pe.name
			WHERE 
				bt.bank_account = %(bank_account)s
				AND bt.company = %(company)s
				AND bt.docstatus = 1
				AND bt.unallocated_amount = 0.0
				AND bt.date >= %(from_date)s
				AND bt.date <= %(to_date)s
				AND btp.payment_document = 'Payment Entry'
				AND (pe.clearance_date IS NULL OR pe.clearance_date != bt.date)
				AND ((bt.deposit > 0 AND pe.payment_type = 'Receive' AND pe.paid_to = %(bank_gl_account)s)
					OR (bt.withdrawal > 0 AND pe.payment_type = 'Pay' AND pe.paid_from = %(bank_gl_account)s))
			LIMIT {limit}
			""",
			{
				"bank_account": bank_account,
				"company": company,
				"bank_gl_account": bank_gl_account,
				"from_date": from_date,
				"to_date": to_date,
			},
			as_dict=True
		)
		
		# Also find journal entry transactions that might need validation
		unvalidated_je_transactions = frappe.db.sql(
			f"""
			SELECT DISTINCT bt.name
			FROM `tabBank Transaction` bt
			INNER JOIN `tabBank Transaction Payments` btp ON bt.name = btp.parent
			INNER JOIN `tabJournal Entry` je ON btp.payment_entry = je.name
			WHERE 
				bt.bank_account = %(bank_account)s
				AND bt.company = %(company)s
				AND bt.docstatus = 1
				AND bt.unallocated_amount = 0.0
				AND bt.date >= %(from_date)s
				AND bt.date <= %(to_date)s
				AND btp.payment_document = 'Journal Entry'
				AND (je.clearance_date IS NULL OR je.clearance_date != bt.date)
			LIMIT {limit}
			""",
			{
				"bank_account": bank_account,
				"company": company,
				"from_date": from_date,
				"to_date": to_date,
			},
			as_dict=True
		)
		
		# Find invoice transactions that might need validation
		unvalidated_invoice_transactions = frappe.db.sql(
			f"""
			SELECT DISTINCT bt.name
			FROM `tabBank Transaction` bt
			INNER JOIN `tabBank Transaction Payments` btp ON bt.name = btp.parent
			WHERE 
				bt.bank_account = %(bank_account)s
				AND bt.company = %(company)s
				AND bt.docstatus = 1
				AND bt.unallocated_amount = 0.0
				AND bt.date >= %(from_date)s
				AND bt.date <= %(to_date)s
				AND btp.payment_document IN ('Sales Invoice', 'Purchase Invoice')
			LIMIT {limit}
			""",
			{
				"bank_account": bank_account,
				"company": company,
				"from_date": from_date,
				"to_date": to_date,
			},
			as_dict=True
		)
		
		# Combine all lists and remove duplicates
		all_transactions = list({t['name']: t for t in (unvalidated_transactions + unvalidated_je_transactions + unvalidated_invoice_transactions)}.values())
		
		logger.info("Found %s unvalidated transactions for batch processing", len(all_transactions))
		
		if not all_transactions:
			return {"success": True, "message": "No unvalidated transactions found", "processed_count": 0}
		
		# Process transactions in batches using frappe.enqueue
		processed_count = 0
		for transaction in all_transactions:
			try:
				result = validate_bank_transaction_async(transaction['name'])
				if result.get("success"):
					processed_count += 1
				else:
					logger.error("Failed to queue validation for transaction %s", transaction['name'])
			except Exception as e:
				logger.error("Error processing transaction %s: %s", transaction['name'], str(e), exc_info=True)
				continue
		
		return {
			"success": True, 
			"message": "Queued validation for %s transactions" % processed_count, 
			"processed_count": processed_count,
			"total_found": len(all_transactions)
		}
		
	except Exception as e:
		logger.error("Error in batch validation: %s", str(e), exc_info=True)
		return {"success": False, "error": str(e)}



def validate_single_bank_transaction(bank_transaction_name):
	"""
	Validate and set clearance dates for a single bank transaction
	This function is designed to be called asynchronously via frappe.enqueue
	"""
	try:
		logger.info("Starting validation for bank transaction: %s", bank_transaction_name)
		
		# Load the bank transaction document
		bank_transaction = frappe.get_doc("Bank Transaction", bank_transaction_name)
		
		if bank_transaction.docstatus != 1:
			logger.info("Bank transaction %s is not submitted, skipping validation", bank_transaction_name)
			return
			
		# Get bank account's GL account for Sales Invoice validation
		bank_gl_account = frappe.db.get_value("Bank Account", bank_transaction.bank_account, "account")
		
		clearance_date_set = False
		
		# Iterate through all payment entries in the bank transaction
		for payment_entry in bank_transaction.payment_entries:
			try:
				logger.debug("Processing %s: %s", payment_entry.payment_document, payment_entry.payment_entry)
				
				# Load the actual payment document
				payment_doc = frappe.get_doc(payment_entry.payment_document, payment_entry.payment_entry)
				
				if payment_entry.payment_document == "Payment Entry":
					# Validate payment entry clearance logic
					should_set_clearance = validate_payment_entry_clearance(
						bank_transaction, payment_entry, payment_doc, bank_gl_account
					)
					
					if should_set_clearance and (not payment_doc.clearance_date or getdate(payment_doc.clearance_date) != getdate(bank_transaction.date)):
						payment_doc.db_set("clearance_date", bank_transaction.date)
						logger.info("Set clearance date for Payment Entry %s to %s", payment_doc.name, bank_transaction.date)
						clearance_date_set = True
				
				elif payment_entry.payment_document == "Journal Entry":
					# Handle journal entry clearance
					clear_journal_entry(payment_doc.name)
					clearance_date_set = True
				
				elif payment_entry.payment_document == "Sales Invoice":
					# Handle Sales Invoice - set clearance date on Sales Invoice Payment child table
					for sales_payment in payment_doc.payments:
						if sales_payment.account == bank_gl_account:
							if not sales_payment.clearance_date or getdate(sales_payment.clearance_date) != getdate(bank_transaction.date):
								frappe.db.set_value("Sales Invoice Payment", sales_payment.name, "clearance_date", bank_transaction.date)
								logger.info("Set clearance date for Sales Invoice Payment %s to %s", sales_payment.name, bank_transaction.date)
								clearance_date_set = True
				
				elif payment_entry.payment_document == "Purchase Invoice":
					# Handle Purchase Invoice - set clearance date directly on the document
					if hasattr(payment_doc, 'clearance_date'):
						if not payment_doc.clearance_date or getdate(payment_doc.clearance_date) != getdate(bank_transaction.date):
							payment_doc.db_set("clearance_date", bank_transaction.date)
							logger.info("Set clearance date for Purchase Invoice %s to %s", payment_doc.name, bank_transaction.date)
							clearance_date_set = True
			
			except Exception as e:
				logger.error("Error processing %s %s: %s", payment_entry.payment_document, payment_entry.payment_entry, str(e), exc_info=True)
				continue
		
		if clearance_date_set:
			logger.info("Successfully validated bank transaction %s", bank_transaction_name)
		else:
			logger.info("No clearance dates needed to be set for bank transaction %s", bank_transaction_name)
			
		# Commit the changes
		frappe.db.commit()
		
	except Exception as e:
		logger.error("Error validating bank transaction %s: %s", bank_transaction_name, str(e), exc_info=True)
		frappe.db.rollback()
		raise


def validate_payment_entry_clearance(bank_transaction, payment_entry, payment_doc, bank_gl_account):
	"""
	Validate whether a payment entry should have its clearance date set
	Based on payment type, direction, and allocated vs payment amounts
	"""
	try:
		# Get the payment amount based on payment type and bank account
		if payment_doc.payment_type == "Receive" and payment_doc.paid_to == bank_gl_account:
			payment_amount = payment_doc.received_amount
		elif payment_doc.payment_type == "Pay" and payment_doc.paid_from == bank_gl_account:
			payment_amount = payment_doc.paid_amount
		else:
			return False
		
		# Check if allocated amount matches payment amount and direction
		if bank_transaction.deposit > 0.0:
			# Bank deposit (money coming in)
			if payment_doc.payment_type == "Receive" and payment_entry.allocated_amount == payment_amount:
				return True
			elif payment_doc.payment_type == "Pay" and payment_entry.allocated_amount == -payment_amount:
				return True
		else:
			# Bank withdrawal (money going out)  
			if payment_doc.payment_type == "Receive" and payment_entry.allocated_amount == -payment_amount:
				return True
			elif payment_doc.payment_type == "Pay" and payment_entry.allocated_amount == payment_amount:
				return True
		
		return False
		
	except Exception as e:
		logger.error("Error validating payment entry clearance for %s: %s", payment_doc.name, str(e), exc_info=True)
		return False




def clear_journal_entry(journal_entry_name):
	# First we need to get the allocations for this payment entry in the bank transactions	
	try:
		bt_payments = frappe.db.sql(
			"""
			select 
						bt.date,
						ba.account,
						IF(bt.deposit > 0.0, btp.allocated_amount, -btp.allocated_amount) as allocated_amount
				from `tabBank Transaction` as bt
						inner join `tabBank Account` as ba on bt.bank_account = ba.name 
						inner join `tabBank Transaction Payments` as btp on bt.name = btp.parent
				where btp.payment_document = "Journal Entry"
							and btp.payment_entry = %(journal_entry)s
							and bt.docstatus = 1
				order by bt.date asc
			""",
			{
				"journal_entry": journal_entry_name
			},
			as_dict=True
		)
		
		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		clearance_status = {}
		clearance_date = None
		skip = False
		for acc in journal_entry.accounts:
			account_type = frappe.get_value("Account", acc.account, "account_type")
			if account_type != "Bank":
				continue

			# check if the account is a bank account for do the reconciliation
			bank_account = frappe.db.count("Bank Account", {"account": acc.account, "company": journal_entry.company})
			if bank_account == 0:
				logger.warning("Bank reconciliation is not enabled for account %s in %s. Skipping...", acc.account, journal_entry_name)
				continue

			if acc.account in clearance_status:
				logger.warn("Account %s found twice in the same journal entry. Skipping...", acc.account)
				skip = True
				break

			clearance_status[acc.account] = False

			allocated_amount = 0.0
			for bt in bt_payments:
				if bt.account == acc.account:
					allocated_amount += bt.allocated_amount
					if not clearance_date or getdate(bt.date) > getdate(clearance_date):
						clearance_date = bt.date

			if acc.debit_in_account_currency > 0 and allocated_amount == acc.debit_in_account_currency:
				clearance_status[acc.account] = True
			elif acc.credit_in_account_currency > 0 and allocated_amount == -acc.credit_in_account_currency:
				clearance_status[acc.account] = True
		
		if skip:
			logger.info("Skipping journal entry %s", journal_entry_name)
			return
		
		if all(clearance_status.values()):
			if not journal_entry.clearance_date or getdate(journal_entry.clearance_date) != getdate(clearance_date):
				logger.info("Clearing Journal entry %s: %s", journal_entry.name, clearance_date)
				frappe.db.set_value("Journal Entry", journal_entry.name, "clearance_date", clearance_date)
			else:
				logger.info("Journal entry %s is already cleared", journal_entry.name)
		elif journal_entry.clearance_date:
				logger.info("Resetting clearance date for %s: %s", journal_entry.name, clearance_date)
				frappe.db.set_value("Journal Entry", journal_entry.name, "clearance_date", None)
		else:
			logger.info("Some accounts are not cleared for %s: %s", journal_entry_name, clearance_date)
			logger.info("Allocated amounts %s", bt_payments)
			
	except Exception as e:
		logger.error("Error clearing journal entry %s: %s", journal_entry_name, str(e), exc_info=True)
		raise

