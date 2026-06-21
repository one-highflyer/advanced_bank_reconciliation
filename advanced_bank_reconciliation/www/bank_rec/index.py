import frappe
from frappe import _

from advanced_bank_reconciliation.api.bank_rec import get_boot


no_cache = 1


def get_context(context):
	context.boot = get_boot()
	return context


@frappe.whitelist(methods=["POST"])
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()
