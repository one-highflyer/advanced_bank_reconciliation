import frappe
from frappe.utils import getdate


def get_internal_transfer_clearance_date(payment_entry_name, current_date=None):
	"""Return the latest submitted Bank Transaction date linked to a transfer.

	An Internal Transfer has two bank GL legs but only one clearance date. The
	date must therefore include allocations on both legs. ``current_date`` is a
	fallback for callers that invoke this helper before the current allocation is
	visible to a normal database read.
	"""
	result = frappe.db.sql(
		"""
		SELECT MAX(bt.date)
		FROM `tabBank Transaction Payments` btp
		INNER JOIN `tabBank Transaction` bt ON bt.name = btp.parent
		WHERE btp.payment_document = 'Payment Entry'
		  AND btp.payment_entry = %s
		  AND bt.docstatus = 1
		""",
		payment_entry_name,
	)

	dates = []
	if current_date:
		dates.append(getdate(current_date))
	if result and result[0][0]:
		dates.append(getdate(result[0][0]))

	return max(dates) if dates else None
