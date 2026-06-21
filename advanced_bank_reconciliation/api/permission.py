import frappe
from frappe import _


ALLOWED_BANK_REC_ROLES = frozenset(
	{
		"System Manager",
		"Accounts Manager",
		"Accounts User",
	}
)

ALLOWED_VOUCHER_DOCTYPES = frozenset(
	{
		"Journal Entry",
		"Payment Entry",
		"Purchase Invoice",
		"Sales Invoice",
	}
)


def has_bank_rec_permission(user=None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True

	return bool(ALLOWED_BANK_REC_ROLES.intersection(frappe.get_roles(user)))


def require_bank_rec_permission(user=None):
	user = user or frappe.session.user
	if not has_bank_rec_permission(user):
		raise frappe.PermissionError(_("You are not permitted to use Bank Rec."))


def get_allowed_company_names(user=None):
	user = user or frappe.session.user
	require_bank_rec_permission(user)

	if user == "Administrator":
		return frappe.get_all("Company", pluck="name")

	user_permissions = frappe.permissions.get_user_permissions(user).get("Company", [])
	if user_permissions:
		return sorted({permission.doc for permission in user_permissions if permission.doc})

	return frappe.get_list("Company", pluck="name", order_by="name")


def assert_company_access(company, user=None):
	user = user or frappe.session.user
	require_bank_rec_permission(user)

	if not company:
		raise frappe.PermissionError(_("Company is required."))

	if company not in get_allowed_company_names(user):
		raise frappe.PermissionError(_("You are not permitted to access company {0}.").format(company))

	return company


def assert_bank_account_access(bank_account, user=None):
	user = user or frappe.session.user
	require_bank_rec_permission(user)

	if not bank_account:
		raise frappe.PermissionError(_("Bank Account is required."))

	doc = frappe.get_doc("Bank Account", bank_account)
	frappe.has_permission("Bank Account", "read", doc=doc, user=user, throw=True)
	assert_company_access(doc.company, user=user)
	return doc


def assert_bank_transaction_access(bank_transaction_name, bank_account=None, user=None, ptype="read"):
	user = user or frappe.session.user
	require_bank_rec_permission(user)

	if not bank_transaction_name:
		raise frappe.PermissionError(_("Bank Transaction is required."))

	doc = frappe.get_doc("Bank Transaction", bank_transaction_name)
	frappe.has_permission("Bank Transaction", ptype, doc=doc, user=user, throw=True)

	if bank_account and doc.bank_account != bank_account:
		raise frappe.PermissionError(
			_("Bank Transaction {0} does not belong to Bank Account {1}.").format(
				bank_transaction_name,
				bank_account,
			)
		)

	assert_bank_account_access(doc.bank_account, user=user)
	return doc


def assert_voucher_access(voucher_type, voucher_name, user=None, ptype="read"):
	user = user or frappe.session.user
	require_bank_rec_permission(user)

	if voucher_type not in ALLOWED_VOUCHER_DOCTYPES:
		raise frappe.PermissionError(_("Voucher type {0} is not supported.").format(voucher_type))
	if not voucher_name:
		raise frappe.PermissionError(_("Voucher name is required."))

	doc = frappe.get_doc(voucher_type, voucher_name)
	frappe.has_permission(voucher_type, ptype, doc=doc, user=user, throw=True)

	company = doc.get("company")
	if company:
		assert_company_access(company, user=user)

	return doc
