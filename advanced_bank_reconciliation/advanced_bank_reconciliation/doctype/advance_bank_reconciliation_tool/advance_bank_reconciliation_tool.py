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
		fieldname=["name", "deposit", "withdrawal", "bank_account", "currency"],
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

	accounts = []
	second_account_dict = {
		"account": second_account,
		"account_currency": second_account_currency,
		"credit_in_account_currency": bank_transaction.deposit,
		"debit_in_account_currency": bank_transaction.withdrawal,
		"party_type": party_type,
		"party": party,
		"cost_center": get_default_cost_center(company),
	}

	company_account_dict = {
		"account": company_account,
		"account_currency": company_account_currency,
		"bank_account": bank_transaction.bank_account,
		"credit_in_account_currency": bank_transaction.withdrawal,
		"debit_in_account_currency": bank_transaction.deposit,
		"cost_center": get_default_cost_center(company),
	}

	# convert transaction amount to company currency
	if is_multi_currency:
		exc_rate = get_exchange_rate(bank_transaction.currency, company_default_currency, posting_date)
		withdrawal_in_company_currency = flt(exc_rate * abs(bank_transaction.withdrawal))
		deposit_in_company_currency = flt(exc_rate * abs(bank_transaction.deposit))
	else:
		withdrawal_in_company_currency = bank_transaction.withdrawal
		deposit_in_company_currency = bank_transaction.deposit

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

	if bank_transaction.deposit > 0.0:
		paid_amount = bank_transaction.deposit
	else:
		paid_amount = bank_transaction.withdrawal

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

	if transaction.withdrawal > 0.0:
		if "purchase_invoice" in document_types:
			query = get_pi_matching_query(exact_match)
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
	if transaction.deposit > 0.0:
		currency_field = "paid_to_account_currency as currency"
	else:
		currency_field = "paid_from_account_currency as currency"
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
			+ CASE WHEN paid_amount = %(amount)s THEN 1 ELSE 0 END
			+ 1 ) AS rank,
			'Payment Entry' as doctype,
			name,
			IF(payment_type = 'Pay', {'-paid_amount' if transaction.deposit > 0.0 else 'paid_amount'}, {'paid_amount' if transaction.deposit > 0.0 else '-paid_amount'}) AS paid_amount,
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
			AND paid_amount {'= %(amount)s' if exact_match else '> 0.0'}
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
			if(pe.paid_to=%(account)s, pe.received_amount, 0) as debit,
			if(pe.paid_from=%(account)s, pe.paid_amount, 0) as credit,
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

	query = (
		frappe.qb.from_(bank_transaction)
		.select(
			bank_transaction.name,
			bank_transaction.date,
			bank_transaction.deposit,
			bank_transaction.withdrawal,
			bank_transaction.unallocated_amount,
			bank_transaction.party_type,
			bank_transaction.party,
			bt_payment.payment_document,
			bt_payment.payment_entry,
			bt_payment.allocated_amount,
			payment_entry.paid_amount,
			payment_entry.payment_type
		)
		.inner_join(bt_payment).on(bank_transaction.name == bt_payment.parent)
		.inner_join(payment_entry).on(bt_payment.payment_entry == payment_entry.name)
		.where(bank_transaction.company == company)
		.where(bank_transaction.bank_account == bank_account)
		.where(bank_transaction.date >= from_date)
		.where(bank_transaction.date <= to_date)
		.where(bank_transaction.docstatus == 1)
		.where(bt_payment.payment_document == "Payment Entry")
		.where(payment_entry.clearance_date.isnull() | (payment_entry.clearance_date != bank_transaction.date))
		.orderby(bank_transaction.date)
	)

	entries = query.run(as_dict=True)
	logger.info(f"Found {len(entries)} entries with incorrect clearance date")
	for entry in entries:
		if entry.deposit > 0.0:
			if entry.payment_type == "Receive" and entry.allocated_amount == entry.paid_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Paid amount {entry.paid_amount}, Deposit {entry.deposit}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
			elif entry.payment_type == "Pay" and entry.allocated_amount == -entry.paid_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Paid amount {entry.paid_amount}, Deposit {entry.deposit}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
		else:
			if entry.payment_type == "Receive" and entry.allocated_amount == -entry.paid_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Paid amount {entry.paid_amount}, Withdrawal {entry.withdrawal}")
				frappe.db.set_value("Payment Entry", entry.payment_entry, "clearance_date", entry.date)
			elif entry.payment_type == "Pay" and entry.allocated_amount == entry.paid_amount:
				logger.info(f"Setting clearance date for {entry.payment_entry}. Payment type {entry.payment_type}, Allocated amount {entry.allocated_amount}, Paid amount {entry.paid_amount}, Withdrawal {entry.withdrawal}")
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

	# jle_entries = frappe.db.sql(
	# 	"""
	# 	select 
	# 				bt.name,
	# 				btp.payment_entry,
	# 				IF(bt.deposit > 0.0, btp.allocated_amount, -btp.allocated_amount) as allocated_amount
	# 		from `tabBank Transaction` as bt
	# 				inner join `tabBank Transaction Payments` as btp on bt.name = btp.parent
	# 		where btp.payment_document = "Journal Entry"
	# 						and bt.bank_account = %(bank_account)s
	# 						and bt.docstatus = 1
	# 						and bt.unallocated_amount = 0.0
	# 						and bt.date <= %(to_date)s
	# 						and bt.date >= %(from_date)s
	# 	""",
	# 	{
	# 		"bank_account": bank_account,
	# 		"from_date": from_date,
	# 		"to_date": to_date
	# 	},
	# 	as_dict=True
	# )

	# # Get all the reconciled payment entries
	# query = (
	# 	frappe.qb.from_(bt_payment)
	# 		.select(
	# 			bt_payment.payment_entry
	# 		)
	# 		.inner_join(bank_transaction).on(bt_payment.parent == bank_transaction.name)
	# 		.where(bt_payment.payment_document == "Payment Entry")
	# 		.where(bank_transaction.company == company)
	# 		.where(bank_transaction.bank_account == bank_account)
	# 		.where(bank_transaction.unallocated_amount == 0.0)
	# 		.where(bank_transaction.docstatus == 1)
	# )
	# reconciled_payment_entries = [d.payment_entry for d in query.run(as_dict=True)]
	# logger.info(f"Found {len(reconciled_payment_entries)} reconciled entries")

	# bank_gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
	# # Get incorrectly cleared payment entries
	# query = (
	# 	frappe.qb.from_(payment_entry)
	# 		.select(
	# 			payment_entry.name
	# 		)
	# 		.where(payment_entry.clearance_date.notnull())
	# 		.where((payment_entry.paid_from == bank_gl_account) | (payment_entry.paid_to == bank_gl_account))
	# 		.where(payment_entry.company == company)
	# 		.where(payment_entry.docstatus == 1)
	# )

	# if len(reconciled_payment_entries) > 0:
	# 		query = query.where(payment_entry.name.notin(reconciled_payment_entries))

	# incorrectly_cleared_entries = [d.name for d in query.run(as_dict=True)]
	# logger.info(f"Found {len(incorrectly_cleared_entries)} incorrectly cleared entries")
	
	# for entry in incorrectly_cleared_entries:
	# 	frappe.db.set_value("Payment Entry", entry, "clearance_date", None)
	# 	logger.info(f"Resetting clearance date for {entry}")

	return {"success": True}

def clear_journal_entry(journal_entry_name):
	# First we need to get the allocations for this payment entry in the bank transactions	
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
			logger.warning(f"Bank reconciliation is not enabled for account {acc.account} in {journal_entry_name}. Skipping...")
			continue

		if acc.account in clearance_status:
			logger.warn(f"Account {acc.account} found twice in the same journal entry. Skipping...")
			skip = True
			break

		clearance_status[acc.account] = False

		allocated_amount = 0.0
		for bt in bt_payments:
			if bt.account == acc.account:
				allocated_amount += bt.allocated_amount

		clearance_date = bt.date
		if acc.debit_in_account_currency > 0 and allocated_amount == acc.debit_in_account_currency:
			clearance_status[acc.account] = True
		elif acc.credit_in_account_currency > 0 and allocated_amount == -acc.credit_in_account_currency:
			clearance_status[acc.account] = True
	
	if skip:
		logger.info(f"Skipping journal entry {journal_entry_name}")
		return
	
	if all(clearance_status.values()):
		if not journal_entry.clearance_date or getdate(journal_entry.clearance_date) != getdate(clearance_date):
			logger.info(f"Clearing Journal entry {journal_entry.name}: {clearance_date}")
			frappe.db.set_value("Journal Entry", journal_entry.name, "clearance_date", clearance_date)
		else:
			logger.info(f"Journal entry {journal_entry.name} is already cleared")
	elif journal_entry.clearance_date:
			logger.info(f"Resetting clearance date for {journal_entry.name}: {clearance_date}")
			frappe.db.set_value("Journal Entry", journal_entry.name, "clearance_date", None)
	else:
		logger.info(f"Some accounts are not cleared for {journal_entry_name}: {clearance_date}")
		logger.info(f"Allocated amounts {bt_payments}")

