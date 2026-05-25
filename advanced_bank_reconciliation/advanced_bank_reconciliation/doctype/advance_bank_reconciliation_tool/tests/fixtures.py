# Copyright (c) 2024, HighFlyer and contributors
# For license information, please see license.txt
"""Self-contained fixtures for advance_bank_reconciliation_tool partial
allocation tests. Helpers are idempotent and safe to call from setUpClass
on a fresh CI site that has ERPNext installed. setup_abr_test_data() also
triggers ERPNext's test setup if _Test Company is missing, so individual
test modules can run without relying on the before_tests hook firing.
"""
import frappe
from frappe.utils import add_days, flt, nowdate

TEST_COMPANY = "_Test Company"
TEST_COMPANY_2 = "_Test Company 1"
TEST_BANK = "_ABR Test Bank"
TEST_BANK_ACCOUNT_NAME = "_ABR Test Bank Account"
TEST_BANK_GL_ACCOUNT = "_ABR Test Bank Account - _TC"
TEST_CUSTOMER = "_ABR Test Customer"
TEST_SUPPLIER = "_ABR Test Supplier"
TEST_ITEM = "_ABR Test Item"


def _get_parent_bank_account(company):
	"""Return an existing group 'Bank Accounts' parent or any group bank account."""
	parent = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Bank", "is_group": 1},
		"name",
	)
	if parent:
		return parent
	return frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Asset", "is_group": 1},
		"name",
	)


def ensure_bank_and_bank_account(company=TEST_COMPANY):
	"""Create a Bank, a bank GL account, and a Bank Account doc.

	Returns the Bank Account document name.
	"""
	if not frappe.db.exists("Bank", TEST_BANK):
		bank = frappe.get_doc({"doctype": "Bank", "bank_name": TEST_BANK})
		bank.insert(ignore_permissions=True, ignore_if_duplicate=True)

	if not frappe.db.exists("Account", TEST_BANK_GL_ACCOUNT):
		parent = _get_parent_bank_account(company)
		acc = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_ABR Test Bank Account",
				"parent_account": parent,
				"company": company,
				"account_type": "Bank",
				"is_group": 0,
			}
		)
		acc.insert(ignore_permissions=True, ignore_if_duplicate=True)

	ba_name = f"{TEST_BANK_ACCOUNT_NAME} - {TEST_BANK}"
	if not frappe.db.exists("Bank Account", ba_name):
		ba = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": TEST_BANK_ACCOUNT_NAME,
				"bank": TEST_BANK,
				"account": TEST_BANK_GL_ACCOUNT,
				"is_company_account": 1,
				"company": company,
			}
		)
		ba.insert(ignore_permissions=True, ignore_if_duplicate=True)
		ba_name = ba.name

	return ba_name


def ensure_fiscal_year_for_company(company):
	"""Link the company to an existing fiscal year that covers today.

	On ERPNext test sites the global fiscal years are created by the
	erpnext before_tests hook, but the Fiscal Year Company links are only
	written for the primary _Test Company. When tests create invoices for
	a second company, ERPNext's get_fiscal_years() raises FiscalYearError
	unless the company also appears in the fiscal year's companies list.
	"""
	from frappe.utils import getdate

	today = getdate()
	fy = frappe.db.get_value(
		"Fiscal Year",
		{
			"year_start_date": ["<=", today],
			"year_end_date": [">=", today],
			"disabled": 0,
		},
		"name",
	)
	if not fy:
		return

	already_linked = frappe.db.exists(
		"Fiscal Year Company", {"parent": fy, "company": company}
	)
	if already_linked:
		return

	fy_doc = frappe.get_doc("Fiscal Year", fy)
	fy_doc.append("companies", {"company": company})
	fy_doc.save(ignore_permissions=True)


def ensure_bank_account_for_company(company):
	"""Create a bank GL account and Bank Account doc for the given company.

	Uses the company's abbreviation to build unique names so each company
	in a multi-company test site gets its own isolated bank account.
	Returns the Bank Account document name.
	"""
	ensure_fiscal_year_for_company(company)
	abbr = frappe.db.get_value("Company", company, "abbr")
	acct_name = f"_ABR Test Bank Account {abbr}"
	gl_account_name = f"{acct_name} - {abbr}"

	if not frappe.db.exists("Bank", TEST_BANK):
		frappe.get_doc({"doctype": "Bank", "bank_name": TEST_BANK}).insert(
			ignore_permissions=True, ignore_if_duplicate=True
		)

	if not frappe.db.exists("Account", gl_account_name):
		parent = _get_parent_bank_account(company)
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": acct_name,
				"parent_account": parent,
				"company": company,
				"account_type": "Bank",
				"is_group": 0,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	ba_name = f"{acct_name} - {TEST_BANK}"
	if not frappe.db.exists("Bank Account", ba_name):
		ba = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": acct_name,
				"bank": TEST_BANK,
				"account": gl_account_name,
				"is_company_account": 1,
				"company": company,
			}
		)
		ba.insert(ignore_permissions=True, ignore_if_duplicate=True)
		ba_name = ba.name

	return ba_name


def ensure_customer():
	if not frappe.db.exists("Customer", TEST_CUSTOMER):
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": TEST_CUSTOMER,
				"customer_type": "Individual",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return TEST_CUSTOMER


def ensure_supplier():
	if not frappe.db.exists("Supplier", TEST_SUPPLIER):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": TEST_SUPPLIER,
				"supplier_type": "Individual",
				"supplier_group": "_Test Supplier Group",
			}
		)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return TEST_SUPPLIER


def ensure_item():
	if not frappe.db.exists("Item", TEST_ITEM):
		doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": TEST_ITEM,
				"item_name": TEST_ITEM,
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 1,
			}
		)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return TEST_ITEM


def ensure_erpnext_test_company():
	"""Ensure _Test Company and its prerequisite standard records exist.

	On a fresh site invoked via bench run-tests, the before_tests hook runs
	ERPNext's setup wizard which creates these. When tests are invoked in
	isolation (e.g. a single module via --module flag on a site that has
	not yet been bootstrapped), this helper makes the fixtures truly
	self-contained by triggering the same setup path on demand.
	"""
	if frappe.db.exists("Company", TEST_COMPANY):
		return

	from erpnext.setup.utils import before_tests as erpnext_before_tests

	erpnext_before_tests()


def setup_abr_test_data(company=TEST_COMPANY):
	"""Idempotent top-level setup. Call from setUpClass and commit after."""
	ensure_erpnext_test_company()
	ensure_customer()
	ensure_supplier()
	ensure_item()
	return ensure_bank_and_bank_account(company)


def create_payment_terms_template(name, splits):
	"""Create a Payment Terms Template with allocate_payment_based_on_payment_terms=1.

	splits: list of dicts with keys 'invoice_portion' (percent) and
	        optional 'credit_days' (defaults to 0, 30, 60 ...).
	"""
	if frappe.db.exists("Payment Terms Template", name):
		return name

	terms = []
	for idx, split in enumerate(splits):
		term_name = f"{name} - Term {idx + 1}"
		if not frappe.db.exists("Payment Term", term_name):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": term_name,
					"invoice_portion": flt(split.get("invoice_portion")),
					"credit_days": int(split.get("credit_days", idx * 30)),
					"due_date_based_on": "Day(s) after invoice date",
				}
			).insert(ignore_permissions=True, ignore_if_duplicate=True)
		terms.append(
			{
				"payment_term": term_name,
				"invoice_portion": flt(split.get("invoice_portion")),
				"credit_days": int(split.get("credit_days", idx * 30)),
				"due_date_based_on": "Day(s) after invoice date",
			}
		)

	doc = frappe.get_doc(
		{
			"doctype": "Payment Terms Template",
			"template_name": name,
			"allocate_payment_based_on_payment_terms": 1,
			"terms": terms,
		}
	)
	doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return name


def create_test_sales_invoice(
	outstanding=100.0,
	payment_terms_template=None,
	currency=None,
	customer=None,
	company=TEST_COMPANY,
	is_return=0,
	do_not_submit=False,
	posting_date=None,
	payments=None,
):
	"""Create and submit a Sales Invoice with the requested grand total.

	Insert always uses today's date to dodge ERPNext's due_date / posting
	validation. If the caller wants a historical posting_date, we rewrite
	it via db_set after submit so the field reflects the requested date
	without going through validation again.

	payments: optional list of dicts with keys 'account' and 'amount' (signed).
	          Use this to add Sales Invoice Payment rows (e.g. for paid refund SIs
	          where the SIP row carries a negative amount). When supplied, each dict
	          must include 'account' (GL account name). 'mode_of_payment' defaults
	          to 'Cash' if not provided.
	"""
	item_code = ensure_item()
	customer = customer or ensure_customer()

	qty = -1 if is_return else 1
	rate = abs(flt(outstanding))

	doc_data = {
		"doctype": "Sales Invoice",
		"customer": customer,
		"company": company,
		"posting_date": nowdate(),
		"due_date": add_days(nowdate(), 30),
		"currency": currency or frappe.db.get_value("Company", company, "default_currency"),
		"is_return": 1 if is_return else 0,
		"update_stock": 0,
		"payment_terms_template": payment_terms_template,
		"items": [
			{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"income_account": frappe.db.get_value("Company", company, "default_income_account")
				or "Sales - _TC",
				"cost_center": frappe.db.get_value("Company", company, "cost_center")
				or "Main - _TC",
			}
		],
	}

	if payments:
		doc_data["payments"] = [
			{
				"mode_of_payment": p.get("mode_of_payment", "Cash"),
				"account": p["account"],
				"amount": flt(p["amount"]),
			}
			for p in payments
		]

	doc = frappe.get_doc(doc_data)
	doc.insert(ignore_permissions=True)
	if not do_not_submit:
		doc.submit()
	if posting_date and posting_date != nowdate():
		doc.db_set("posting_date", posting_date, update_modified=False)
		doc.reload()
	return doc


def create_test_purchase_invoice(
	outstanding=150.0,
	currency=None,
	supplier=None,
	company=TEST_COMPANY,
	do_not_submit=False,
	posting_date=None,
	is_paid=0,
	is_return=0,
	cash_bank_account=None,
	mode_of_payment=None,
	paid_amount=None,
):
	"""Create and submit a Purchase Invoice with the requested grand total.

	Insert always uses today's date; see create_test_sales_invoice for
	the rationale around historical posting_date handling.

	For is_paid=1 invoices:
	  - cash_bank_account is required (GL Account name, not Bank Account doc name).
	    Raises frappe.ValidationError if omitted.
	  - mode_of_payment defaults to 'Cash' if not provided.
	  - For is_return=1 invoices, ERPNext's calculate_paid_amount does not auto-set
	    paid_amount for negative grand_totals. The caller should supply paid_amount
	    explicitly (e.g. paid_amount=-31.27) so the GL entry to the bank account is
	    created. If omitted for a return invoice, paid_amount remains 0 and no bank
	    GL entry is posted.
	"""
	if is_paid and not cash_bank_account:
		frappe.throw(
			"cash_bank_account is required when creating a paid Purchase Invoice (is_paid=1). "
			"Supply the GL Account name (e.g. TEST_BANK_GL_ACCOUNT).",
			frappe.ValidationError,
		)

	item_code = ensure_item()
	supplier = supplier or ensure_supplier()

	qty = -1 if is_return else 1
	rate = abs(flt(outstanding))

	doc_data = {
		"doctype": "Purchase Invoice",
		"supplier": supplier,
		"company": company,
		"posting_date": nowdate(),
		"due_date": add_days(nowdate(), 30),
		"currency": currency or frappe.db.get_value("Company", company, "default_currency"),
		"update_stock": 0,
		"is_paid": 1 if is_paid else 0,
		"is_return": 1 if is_return else 0,
		"items": [
			{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"expense_account": frappe.db.get_value(
					"Company", company, "default_expense_account"
				)
				or "Cost of Goods Sold - _TC",
				"cost_center": frappe.db.get_value("Company", company, "cost_center")
				or "Main - _TC",
			}
		],
	}

	if is_paid:
		doc_data["cash_bank_account"] = cash_bank_account
		doc_data["mode_of_payment"] = mode_of_payment or "Cash"
		if paid_amount is not None:
			doc_data["paid_amount"] = flt(paid_amount)

	doc = frappe.get_doc(doc_data)
	doc.insert(ignore_permissions=True)
	if not do_not_submit:
		doc.submit()
	if posting_date and posting_date != nowdate():
		doc.db_set("posting_date", posting_date, update_modified=False)
		doc.reload()
	return doc


def create_test_bank_transaction(
	bank_account,
	deposit=0.0,
	withdrawal=0.0,
	date=None,
	reference_number=None,
	description="_ABR Test Bank Transaction",
	currency=None,
	do_not_submit=False,
):
	"""Create and submit a Bank Transaction.

	Bank Transaction currency must match the Bank Account's GL currency.
	We default to the GL account's currency so fixtures work on any site
	regardless of system default currency.
	"""
	gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
	account_currency = frappe.db.get_value("Account", gl_account, "account_currency")

	doc = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"date": date or nowdate(),
			"bank_account": bank_account,
			"deposit": flt(deposit),
			"withdrawal": flt(withdrawal),
			"reference_number": reference_number or "_ABR-REF",
			"description": description,
			"currency": currency or account_currency,
		}
	)
	doc.insert(ignore_permissions=True)
	if not do_not_submit:
		doc.submit()
	return doc
