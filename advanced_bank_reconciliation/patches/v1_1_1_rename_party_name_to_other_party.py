import frappe


def execute():
    frappe.db.sql("""
        UPDATE `tabABR Bank Rule Condition`
        SET field_name = 'Other Party'
        WHERE field_name = 'Party Name'
    """)
