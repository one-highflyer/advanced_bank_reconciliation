# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Regression tests for float-precision handling in bulk reconciliation.

A JS client computing "remaining" via subtraction (e.g. 760 - 649.71) can
send an allocated amount like 110.28999999999996 to reconcile_vouchers.
The payment_entries child row's allocated_amount must be rounded to the
field's precision on append; otherwise the second save() inside
reconcile_vouchers trips UpdateAfterSubmitError — the in-memory value is
the unrounded float while the DB value is already rounded.
"""
import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_payment_entry_for_invoice,
	reconcile_vouchers,
)

from .fixtures import (
	TEST_COMPANY,
	create_test_bank_transaction,
	create_test_sales_invoice,
	setup_abr_test_data,
)


class TestBulkReconcilePrecision(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(TEST_COMPANY)
		frappe.db.commit()

	def test_unrounded_float_allocation_does_not_raise(self):
		"""Regression: an unrounded float from JS arithmetic must round to
		the field precision before append, so the second save() inside
		reconcile_vouchers doesn't trip UpdateAfterSubmitError.

		Invoices are created with round outstanding amounts large enough to
		cover the partial allocations. The float quirk is in the allocation
		amounts passed to reconcile_vouchers (what the UI sends), not in
		the invoice totals — which can differ slightly on CI vs local if
		tax/rounding defaults change grand_total.
		"""
		si1 = create_test_sales_invoice(outstanding=1000)
		si2 = create_test_sales_invoice(outstanding=1000)
		bt = create_test_bank_transaction(self.bank_account, deposit=760)

		pe1 = create_payment_entry_for_invoice(
			invoice_doc=si1,
			bank_transaction=bt,
			allocated_amount=649.71,
			payment_type="Receive",
			party_type="Customer",
			party=si1.customer,
		)
		pe2 = create_payment_entry_for_invoice(
			invoice_doc=si2,
			bank_transaction=bt,
			allocated_amount=110.29,
			payment_type="Receive",
			party_type="Customer",
			party=si2.customer,
		)

		# Simulate what the bulk reconciliation UI sends: the second amount
		# is computed as deposit - first_amount and carries a JS float error.
		second_amount = 760 - 649.71
		self.assertNotEqual(second_amount, 110.29)
		self.assertAlmostEqual(second_amount, 110.29, places=2)

		vouchers = [
			{"payment_doctype": "Payment Entry", "payment_name": pe1.name, "amount": 649.71},
			{"payment_doctype": "Payment Entry", "payment_name": pe2.name, "amount": second_amount},
		]

		reconcile_vouchers(bt.name, json.dumps(vouchers))

		bt.reload()
		self.assertEqual(flt(bt.allocated_amount), 760.0)
		self.assertEqual(flt(bt.unallocated_amount), 0.0)
		self.assertEqual(len(bt.payment_entries), 2)

		# Match by payment_entry name so the assertion is independent of row order
		by_name = {row.payment_entry: row for row in bt.payment_entries}
		self.assertEqual(flt(by_name[pe1.name].allocated_amount), 649.71)
		self.assertEqual(flt(by_name[pe2.name].allocated_amount), 110.29)
