def before_tests():
	"""Prepare the site for app tests.

	Runs ERPNext's own setup (creates _Test Company with Warehouse Types,
	Fiscal Year, Chart of Accounts, and the rest of the standard fixtures)
	and pre-creates global test dependencies in an order that sidesteps
	the Item/BOM circular dependency seen in the Frappe v15 test runner.
	"""
	import frappe
	from erpnext.setup.utils import before_tests as erpnext_before_tests

	erpnext_before_tests()

	from frappe.test_runner import make_test_records

	if not hasattr(frappe.local, "test_objects") or frappe.local.test_objects is None:
		frappe.local.test_objects = {}

	try:
		frappe.local.test_objects["BOM"] = []
		for doctype in ["User", "Company", "Customer", "Supplier", "Item"]:
			make_test_records(doctype, commit=True)
	finally:
		frappe.local.test_objects.pop("BOM", None)

	frappe.db.commit()
