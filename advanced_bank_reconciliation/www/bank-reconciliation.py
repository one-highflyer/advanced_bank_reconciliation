import frappe


def get_context(context):
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token
    context.no_cache = 1
