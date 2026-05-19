# Copyright (c) 2024, HighFlyer and contributors
# For license information, please see license.txt
"""Tests for partial-allocation behaviour in
create_payment_entry_for_invoice() and its helper
_normalise_pe_to_target_invoice().
"""
import json
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	_normalise_pe_to_target_invoice,
	_signed_cap,
	create_payment_entry_for_invoice,
	get_linked_payments,
	reconcile_vouchers,
	unreconcile_bank_transaction,
)

from .fixtures import (
	TEST_BANK_GL_ACCOUNT,
	TEST_COMPANY,
	create_payment_terms_template,
	create_test_bank_transaction,
	create_test_purchase_invoice,
	create_test_sales_invoice,
	setup_abr_test_data,
)


def _reconcile(bank_transaction_name, payment_entry_name, amount):
	vouchers = [
		{
			"payment_doctype": "Payment Entry",
			"payment_name": payment_entry_name,
			"amount": flt(amount),
		}
	]
	return reconcile_vouchers(bank_transaction_name, json.dumps(vouchers))


class TestPartialAllocation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(TEST_COMPANY)
		frappe.db.commit()

	# 1
	def test_partial_sales_invoice_allocation(self):
		si = create_test_sales_invoice(outstanding=100)
		bt = create_test_bank_transaction(self.bank_account, deposit=30)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=30,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		self.assertEqual(flt(pe.paid_amount), 30.0)
		self.assertEqual(flt(pe.received_amount), 30.0)
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(flt(pe.references[0].allocated_amount), 30.0)
		self.assertEqual(pe.references[0].reference_name, si.name)
		self.assertEqual(pe.deductions, [])

		_reconcile(bt.name, pe.name, 30)
		si.reload()
		bt.reload()
		self.assertEqual(flt(si.outstanding_amount), 70.0)
		self.assertEqual(flt(bt.allocated_amount), 30.0)
		self.assertEqual(flt(bt.unallocated_amount), 0.0)

	# 2
	def test_exact_sales_invoice_allocation(self):
		si = create_test_sales_invoice(outstanding=100)
		bt = create_test_bank_transaction(self.bank_account, deposit=100)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=100,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		self.assertEqual(flt(pe.paid_amount), 100.0)
		self.assertEqual(len(pe.references), 1)

		_reconcile(bt.name, pe.name, 100)
		si.reload()
		self.assertEqual(flt(si.outstanding_amount), 0.0)
		self.assertEqual(si.status, "Paid")

	# 3
	def test_partial_allocation_ignores_other_open_invoices(self):
		si_target = create_test_sales_invoice(outstanding=100)
		si_other = create_test_sales_invoice(outstanding=200)
		bt = create_test_bank_transaction(self.bank_account, deposit=40)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si_target,
			bank_transaction=bt,
			allocated_amount=40,
			payment_type="Receive",
			party_type="Customer",
			party=si_target.customer,
		)

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].reference_name, si_target.name)
		self.assertEqual(flt(pe.references[0].allocated_amount), 40.0)

		# Other invoice must be untouched
		si_other.reload()
		self.assertEqual(flt(si_other.outstanding_amount), 200.0)

	# 4
	def test_partial_allocation_with_payment_terms_template(self):
		ptt_name = create_payment_terms_template(
			"_ABR Test PTT 50-50",
			[
				{"invoice_portion": 50, "credit_days": 0},
				{"invoice_portion": 50, "credit_days": 30},
			],
		)
		si = create_test_sales_invoice(outstanding=100, payment_terms_template=ptt_name)

		# Sanity check: the SI has two payment schedule rows
		self.assertEqual(len(si.payment_schedule), 2)

		bt = create_test_bank_transaction(self.bank_account, deposit=30)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=30,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		# Regression guard for Defect A: must collapse multi-term refs to one
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(flt(pe.references[0].allocated_amount), 30.0)
		self.assertEqual(flt(pe.paid_amount), 30.0)

		_reconcile(bt.name, pe.name, 30)
		si.reload()
		bt.reload()
		self.assertEqual(flt(si.outstanding_amount), 70.0)
		self.assertEqual(flt(bt.unallocated_amount), 0.0)

	# 5
	def test_partial_allocation_drops_deductions(self):
		si = create_test_sales_invoice(outstanding=100)
		bt = create_test_bank_transaction(self.bank_account, deposit=30)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=30,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		# Regression guard for Defect B: deductions unconditionally cleared
		self.assertEqual(pe.deductions, [])
		self.assertEqual(flt(pe.paid_amount), 30.0)
		self.assertEqual(flt(pe.received_amount), 30.0)

	# 6
	def test_partial_purchase_invoice_allocation_withdrawal(self):
		pi = create_test_purchase_invoice(outstanding=150)
		bt = create_test_bank_transaction(self.bank_account, withdrawal=40)

		pe = create_payment_entry_for_invoice(
			invoice_doc=pi,
			bank_transaction=bt,
			allocated_amount=40,
			payment_type="Pay",
			party_type="Supplier",
			party=pi.supplier,
		)

		self.assertEqual(pe.payment_type, "Pay")
		self.assertEqual(flt(pe.paid_amount), 40.0)
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(flt(pe.references[0].allocated_amount), 40.0)

		_reconcile(bt.name, pe.name, 40)
		pi.reload()
		bt.reload()
		self.assertEqual(flt(pi.outstanding_amount), 110.0)
		self.assertEqual(flt(bt.unallocated_amount), 0.0)

	# 7
	def test_second_partial_clears_invoice(self):
		si = create_test_sales_invoice(outstanding=100)

		bt1 = create_test_bank_transaction(self.bank_account, deposit=30)
		pe1 = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt1,
			allocated_amount=30,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)
		_reconcile(bt1.name, pe1.name, 30)

		si.reload()
		self.assertEqual(flt(si.outstanding_amount), 70.0)

		bt2 = create_test_bank_transaction(self.bank_account, deposit=70)
		pe2 = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt2,
			allocated_amount=70,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)
		_reconcile(bt2.name, pe2.name, 70)

		si.reload()
		self.assertEqual(flt(si.outstanding_amount), 0.0)

	# 8
	def test_cancel_partial_pe_restores_outstanding(self):
		si = create_test_sales_invoice(outstanding=100)
		bt = create_test_bank_transaction(self.bank_account, deposit=30)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=30,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)
		_reconcile(bt.name, pe.name, 30)

		si.reload()
		self.assertEqual(flt(si.outstanding_amount), 70.0)

		# Cancel the PE; ERPNext reverses the allocation
		pe_doc = frappe.get_doc("Payment Entry", pe.name)
		pe_doc.cancel()

		si.reload()
		bt.reload()
		self.assertEqual(flt(si.outstanding_amount), 100.0)
		# After cancellation the BT should regain its full unallocated amount
		self.assertEqual(flt(bt.unallocated_amount), 30.0)

	# 9
	def test_credit_note_negative_allocation(self):
		si = create_test_sales_invoice(outstanding=50, is_return=1)
		# Credit notes carry negative outstanding
		self.assertLess(flt(si.outstanding_amount), 0)
		# Withdrawal represents money going out to refund the customer
		bt = create_test_bank_transaction(self.bank_account, withdrawal=20)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=-20,
			payment_type="Pay",
			party_type="Customer",
			party=si.customer,
		)

		# The fix under test is PE construction; end-to-end reconcile sign
		# handling for withdrawal + credit note is orthogonal to partial
		# allocation and lives in the ABR reconcile path.
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(flt(pe.references[0].allocated_amount), -20.0)
		self.assertEqual(flt(pe.paid_amount), 20.0)

	def _build_unit_pe(self):
		"""Stray row placed BEFORE target rows to confirm the filter
		does not rely on list position; two PTT split rows follow.
		"""
		return SimpleNamespace(
			references=[
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-OTHER",
					outstanding_amount=75,
					allocated_amount=75,
					payment_term="Other-Term-1",
					payment_term_outstanding=75,
				),
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-001",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-1",
					payment_term_outstanding=50,
				),
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-001",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-2",
					payment_term_outstanding=50,
				),
			],
			deductions=[SimpleNamespace(amount=5, description="early-payment")],
			paid_amount=100,
			received_amount=100,
		)

	# 10a
	def test_normalise_helper_within_first_term(self):
		invoice = SimpleNamespace(doctype="Sales Invoice", name="_ABR-SI-UNIT-001")
		pe = self._build_unit_pe()

		_normalise_pe_to_target_invoice(pe, invoice, allocated_amount=30)

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].reference_name, "_ABR-SI-UNIT-001")
		self.assertEqual(pe.references[0].payment_term, "Term-1")
		self.assertEqual(flt(pe.references[0].allocated_amount), 30.0)
		self.assertEqual(pe.deductions, [])
		self.assertEqual(flt(pe.paid_amount), 30.0)
		self.assertEqual(flt(pe.received_amount), 30.0)

	# 10b
	def test_normalise_helper_cascades_across_terms(self):
		invoice = SimpleNamespace(doctype="Sales Invoice", name="_ABR-SI-UNIT-001")
		pe = self._build_unit_pe()

		# Allocation 75 exceeds first term (50) but fits within invoice total (100)
		_normalise_pe_to_target_invoice(pe, invoice, allocated_amount=75)

		self.assertEqual(len(pe.references), 2)
		self.assertEqual(pe.references[0].payment_term, "Term-1")
		self.assertEqual(flt(pe.references[0].allocated_amount), 50.0)
		self.assertEqual(pe.references[1].payment_term, "Term-2")
		self.assertEqual(flt(pe.references[1].allocated_amount), 25.0)
		self.assertEqual(flt(pe.paid_amount), 75.0)

	def test_partial_allocation_exceeds_first_payment_term_outstanding(self):
		"""Allocating more than the first payment term's outstanding but
		less than the full invoice must succeed. The helper cascades the
		allocation across terms so ERPNext's PTT validator is satisfied.
		"""
		ptt_name = create_payment_terms_template(
			"_ABR Test PTT 50-50 Overflow",
			[
				{"invoice_portion": 50, "credit_days": 0},
				{"invoice_portion": 50, "credit_days": 30},
			],
		)
		si = create_test_sales_invoice(outstanding=100, payment_terms_template=ptt_name)
		self.assertEqual(len(si.payment_schedule), 2)

		bt = create_test_bank_transaction(self.bank_account, deposit=75)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=75,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
		)

		# Cascade: first term fills to 50, second term takes the remaining 25
		self.assertEqual(len(pe.references), 2)
		self.assertEqual(flt(pe.references[0].allocated_amount), 50.0)
		self.assertEqual(flt(pe.references[1].allocated_amount), 25.0)
		self.assertEqual(flt(pe.paid_amount), 75.0)

		_reconcile(bt.name, pe.name, 75)
		si.reload()
		bt.reload()
		self.assertAlmostEqual(flt(si.outstanding_amount), 25.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)

	def test_signed_cap_positive(self):
		self.assertEqual(_signed_cap(30, 100), 30)
		self.assertEqual(_signed_cap(150, 100), 100)

	def test_signed_cap_negative(self):
		# When both negative, cap must keep allocation within outstanding
		self.assertEqual(_signed_cap(-20, -50), -20)
		self.assertEqual(_signed_cap(-80, -50), -50)

	def test_normalise_helper_throws_on_over_allocation(self):
		invoice = SimpleNamespace(doctype="Sales Invoice", name="_ABR-SI-UNIT-002")
		pe = SimpleNamespace(
			references=[
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-002",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-1",
					payment_term_outstanding=50,
				),
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-002",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-2",
					payment_term_outstanding=50,
				),
			],
			deductions=[],
			paid_amount=0,
			received_amount=0,
		)
		with self.assertRaises(frappe.ValidationError):
			_normalise_pe_to_target_invoice(pe, invoice, allocated_amount=150)

	def test_normalise_helper_skips_fully_paid_term(self):
		invoice = SimpleNamespace(doctype="Sales Invoice", name="_ABR-SI-UNIT-003")
		# First term is fully paid (payment_term_outstanding=0); second still open.
		pe = SimpleNamespace(
			references=[
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-003",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-1",
					payment_term_outstanding=0,
				),
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-003",
					outstanding_amount=50,
					allocated_amount=50,
					payment_term="Term-2",
					payment_term_outstanding=50,
				),
			],
			deductions=[],
			paid_amount=0,
			received_amount=0,
		)
		_normalise_pe_to_target_invoice(pe, invoice, allocated_amount=30)

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].payment_term, "Term-2")
		self.assertEqual(flt(pe.references[0].allocated_amount), 30.0)

	def test_normalise_helper_cascade_negative_credit_note(self):
		invoice = SimpleNamespace(doctype="Sales Invoice", name="_ABR-SI-UNIT-004")
		# Credit note split across two payment terms, both negative.
		pe = SimpleNamespace(
			references=[
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-004",
					outstanding_amount=-50,
					allocated_amount=-50,
					payment_term="Term-1",
					payment_term_outstanding=-50,
				),
				SimpleNamespace(
					reference_doctype="Sales Invoice",
					reference_name="_ABR-SI-UNIT-004",
					outstanding_amount=-50,
					allocated_amount=-50,
					payment_term="Term-2",
					payment_term_outstanding=-50,
				),
			],
			deductions=[],
			paid_amount=0,
			received_amount=0,
		)
		_normalise_pe_to_target_invoice(pe, invoice, allocated_amount=-75)

		self.assertEqual(len(pe.references), 2)
		self.assertEqual(flt(pe.references[0].allocated_amount), -50.0)
		self.assertEqual(flt(pe.references[1].allocated_amount), -25.0)
		self.assertEqual(flt(pe.paid_amount), 75.0)
		self.assertEqual(flt(pe.received_amount), 75.0)


class TestRefundMatchingAndAllocation(FrappeTestCase):
	"""End-to-end and unit tests for paid/unpaid refund invoice matching and
	the signed-allocation unallocated_amount fix.

	Tests 1-4 use the full ABR reconcile flow (create PE or direct voucher).
	Tests 5-11 directly set BT payment_entries rows and call bt.save() to
	isolate the update_allocated_amount override behaviour.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(TEST_COMPANY)
		frappe.db.commit()

	# -----------------------------------------------------------------------
	# Helper: directly invoke update_allocated_amount with synthetic rows
	# -----------------------------------------------------------------------

	def _bt_with_synthetic_rows(self, deposit=0.0, withdrawal=0.0, rows=None):
		"""Create a submitted BT, inject synthetic payment_entry child rows
		directly via frappe.db.sql to bypass Dynamic Link validation, and invoke
		update_allocated_amount + set_status explicitly.

		This isolates the update_allocated_amount formula from the PE creation
		and link-validation layers. rows: list of floats (allocated_amount values).
		"""
		bt = create_test_bank_transaction(self.bank_account, deposit=deposit, withdrawal=withdrawal)

		if rows:
			import random
			import string

			for amount in rows:
				# Use a synthetic but unique child row name
				row_name = "ABR-TEST-" + "".join(random.choices(string.ascii_lowercase, k=8))
				# Insert child row directly, bypassing link validation
				frappe.db.sql(
					"""
					INSERT INTO `tabBank Transaction Payments`
					    (name, parent, parenttype, parentfield,
					     payment_document, payment_entry, allocated_amount)
					VALUES (%s, %s, 'Bank Transaction', 'payment_entries',
					        'Payment Entry', %s, %s)
					""",
					(row_name, bt.name, row_name, flt(amount)),
				)

			# Reload so the Python object has the rows
			bt.reload()
			# Now call update_allocated_amount and set_status directly
			bt.update_allocated_amount()
			bt.set_status()
			# Persist the computed values
			frappe.db.set_value(
				"Bank Transaction",
				bt.name,
				{
					"allocated_amount": bt.allocated_amount,
					"unallocated_amount": bt.unallocated_amount,
				},
			)
			bt.reload()

		return bt

	# -----------------------------------------------------------------------
	# Test 1 — standalone unpaid refund SI on deposit (PE path)
	# -----------------------------------------------------------------------

	def test_standalone_unpaid_refund_si_on_deposit(self):
		"""Unpaid SI return (outstanding=-31.22) reconciled against BT deposit=31.22.
		After match, BT must be fully reconciled with signed allocated_amount.
		"""
		si = create_test_sales_invoice(outstanding=31.22, is_return=1)
		self.assertLess(flt(si.outstanding_amount), 0)

		bt = create_test_bank_transaction(self.bank_account, deposit=31.22)

		pe = create_payment_entry_for_invoice(
			invoice_doc=si,
			bank_transaction=bt,
			allocated_amount=-31.22,
			payment_type="Pay",
			party_type="Customer",
			party=si.customer,
		)

		_reconcile(bt.name, pe.name, -31.22)
		bt.reload()

		self.assertAlmostEqual(flt(bt.allocated_amount), -31.22, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 2 — standalone unpaid refund PI on deposit (PE path)
	# -----------------------------------------------------------------------

	def test_standalone_unpaid_refund_pi_on_deposit(self):
		"""Unpaid PI return (outstanding=-31.22) reconciled against BT deposit=31.22.
		After match, BT must be fully reconciled with signed allocated_amount.
		"""
		pi = create_test_purchase_invoice(outstanding=31.22, is_return=1)
		self.assertLess(flt(pi.outstanding_amount), 0)

		bt = create_test_bank_transaction(self.bank_account, deposit=31.22)

		pe = create_payment_entry_for_invoice(
			invoice_doc=pi,
			bank_transaction=bt,
			allocated_amount=-31.22,
			payment_type="Receive",
			party_type="Supplier",
			party=pi.supplier,
		)

		_reconcile(bt.name, pe.name, -31.22)
		bt.reload()
		pi.reload()

		self.assertAlmostEqual(flt(bt.allocated_amount), -31.22, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 3 — standalone paid refund PI on deposit (new PR-1 path)
	# -----------------------------------------------------------------------

	def test_standalone_paid_refund_pi_on_deposit(self):
		"""PI is_paid=1, is_return=1 matched directly as a regular voucher against
		BT deposit=31.22. Tests the new for_deposit=True query branch.
		paid_amount=-31.27 is supplied explicitly because ERPNext's
		calculate_paid_amount does not auto-set negative paid_amount for returns.
		"""
		pi = create_test_purchase_invoice(
			outstanding=31.27,
			is_paid=1,
			is_return=1,
			cash_bank_account=TEST_BANK_GL_ACCOUNT,
			paid_amount=-31.27,
		)
		# Verify the paid_amount is negative as expected for a refund
		self.assertLess(flt(pi.paid_amount), 0)

		bt = create_test_bank_transaction(self.bank_account, deposit=31.22)

		# Direct regular-voucher reconcile (no PE created)
		reconcile_vouchers(bt.name, json.dumps([
			{
				"payment_doctype": "Purchase Invoice",
				"payment_name": pi.name,
				"amount": -31.22,
			}
		]))
		bt.reload()
		pi.reload()

		self.assertAlmostEqual(flt(bt.allocated_amount), -31.22, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 4 — standalone paid refund SI on withdrawal (new symmetric path)
	# -----------------------------------------------------------------------

	def test_standalone_paid_refund_si_on_withdrawal(self):
		"""SI with SIP row account=bank_gl, amount=-50 matched directly as a
		regular voucher against BT withdrawal=50.
		Tests the new for_withdrawal=True query branch.
		"""
		# Create a return SI. We will patch the SIP row after creation to point
		# at the test bank GL account, because set_account_for_mode_of_payment
		# overrides the account from mode_of_payment during validate.
		si = create_test_sales_invoice(outstanding=50, is_return=1)

		# Patch the SIP row: set account to test bank GL and amount to -50.
		# Use a direct SIP insert since submit clears unallocated SIP rows.
		frappe.get_doc({
			"doctype": "Sales Invoice Payment",
			"parent": si.name,
			"parenttype": "Sales Invoice",
			"parentfield": "payments",
			"mode_of_payment": "Cash",
			"account": TEST_BANK_GL_ACCOUNT,
			"amount": -50.0,
			"base_amount": -50.0,
		}).insert(ignore_permissions=True)

		bt = create_test_bank_transaction(self.bank_account, withdrawal=50)

		# Direct regular-voucher reconcile (no PE created)
		reconcile_vouchers(bt.name, json.dumps([
			{
				"payment_doctype": "Sales Invoice",
				"payment_name": si.name,
				"amount": -50,
			}
		]))
		bt.reload()

		self.assertAlmostEqual(flt(bt.allocated_amount), -50.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 5 — batched mixed deposit (Venerdi-style regression guard)
	# -----------------------------------------------------------------------

	def test_batched_mixed_deposit_regression(self):
		"""BT deposit=1000, two rows: +1031.27 and -31.27 (net 1000).
		BT must show allocated_amount=1000, unallocated_amount=0.
		"""
		bt = self._bt_with_synthetic_rows(deposit=1000.0, rows=[1031.27, -31.27])

		self.assertAlmostEqual(flt(bt.allocated_amount), 1000.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 6 — all-positive partial allocation (regression guard)
	# -----------------------------------------------------------------------

	def test_all_positive_partial_allocation_regression(self):
		"""BT deposit=100, single row allocated=60. Must remain Unreconciled."""
		bt = self._bt_with_synthetic_rows(deposit=100.0, rows=[60.0])

		self.assertAlmostEqual(flt(bt.allocated_amount), 60.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 40.0, places=2)
		self.assertEqual(bt.status, "Unreconciled")

	# -----------------------------------------------------------------------
	# Test 7 — all-negative partial refund (previously broken)
	# -----------------------------------------------------------------------

	def test_all_negative_partial_refund(self):
		"""BT deposit=100, single refund row allocated=-60.
		abs(100) - abs(-60) = 40 unallocated. Previously this gave 160.
		"""
		bt = self._bt_with_synthetic_rows(deposit=100.0, rows=[-60.0])

		self.assertAlmostEqual(flt(bt.allocated_amount), -60.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 40.0, places=2)
		self.assertEqual(bt.status, "Unreconciled")

	# -----------------------------------------------------------------------
	# Test 8 — mixed partial allocation
	# -----------------------------------------------------------------------

	def test_mixed_partial_allocation(self):
		"""BT deposit=100, two rows: +50, -20 (signed sum=30).
		unallocated = abs(100) - abs(30) = 70.
		"""
		bt = self._bt_with_synthetic_rows(deposit=100.0, rows=[50.0, -20.0])

		self.assertAlmostEqual(flt(bt.allocated_amount), 30.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 70.0, places=2)
		self.assertEqual(bt.status, "Unreconciled")

	# -----------------------------------------------------------------------
	# Test 9 — unreconcile after standalone refund match (round trip)
	# -----------------------------------------------------------------------

	def test_unreconcile_after_standalone_refund_match(self):
		"""After reconciling a paid refund PI (test 3 scenario), unreconcile
		must restore BT to its original unallocated state.
		"""
		pi = create_test_purchase_invoice(
			outstanding=31.22,
			is_paid=1,
			is_return=1,
			cash_bank_account=TEST_BANK_GL_ACCOUNT,
			paid_amount=-31.22,
		)
		bt = create_test_bank_transaction(self.bank_account, deposit=31.22)

		reconcile_vouchers(bt.name, json.dumps([
			{
				"payment_doctype": "Purchase Invoice",
				"payment_name": pi.name,
				"amount": -31.22,
			}
		]))
		bt.reload()
		self.assertEqual(bt.status, "Reconciled")

		# Unreconcile
		unreconcile_bank_transaction(bt.name)
		bt.reload()
		pi.reload()

		self.assertAlmostEqual(flt(bt.allocated_amount), 0.0, places=2)
		self.assertAlmostEqual(flt(bt.unallocated_amount), 31.22, places=2)
		self.assertEqual(bt.status, "Unreconciled")
		self.assertFalse(pi.clearance_date)

	# -----------------------------------------------------------------------
	# Test 10 — exact match threshold boundary
	# -----------------------------------------------------------------------

	def test_exact_match_threshold_boundary(self):
		"""BT deposit=100, allocate exactly 100. Must become Reconciled."""
		bt = self._bt_with_synthetic_rows(deposit=100.0, rows=[100.0])

		self.assertAlmostEqual(flt(bt.unallocated_amount), 0.0, places=2)
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Test 11 — overallocation rounding
	# -----------------------------------------------------------------------

	def test_overallocation_rounding(self):
		"""BT deposit=100.00, signed sum=100.01 (overallocated by 0.01).
		unallocated = 100 - 100.01 = -0.01; set_status treats <=0 as Reconciled.
		"""
		bt = self._bt_with_synthetic_rows(deposit=100.0, rows=[100.01])

		# unallocated_amount will be slightly negative due to overallocation
		self.assertAlmostEqual(flt(bt.unallocated_amount), -0.01, places=2)
		# set_status uses unallocated_amount <= 0 → Reconciled
		self.assertEqual(bt.status, "Reconciled")

	# -----------------------------------------------------------------------
	# Helpers for matching-query coverage (tests 12+)
	# -----------------------------------------------------------------------

	@staticmethod
	def _match_rows_for_doctype(matches, doctype, name):
		"""Filter matching tuples to a specific (doctype, name) pair.

		check_matching returns tuples shaped like
		(rank, doctype, name, paid_amount, reference_no, reference_date,
		 party, party_type, posting_date, currency, party_name).
		"""
		return [row for row in matches if row[1] == doctype and row[2] == name]

	# -----------------------------------------------------------------------
	# Test 12 — get_linked_payments returns paid refund PI for deposit BT
	# -----------------------------------------------------------------------

	def test_get_linked_payments_returns_paid_refund_pi_for_deposit(self):
		"""A paid refund PI (is_paid=1, is_return=1, paid_amount<0) must appear
		as a matching candidate for a deposit BT when document_types includes
		'purchase_invoice'. Covers the new get_pi_matching_query(for_deposit=True)
		branch end-to-end through the whitelisted get_linked_payments API.
		"""
		pi = create_test_purchase_invoice(
			outstanding=31.27,
			is_paid=1,
			is_return=1,
			cash_bank_account=TEST_BANK_GL_ACCOUNT,
			paid_amount=-31.27,
		)
		self.assertLess(flt(pi.paid_amount), 0)

		# Non-exact-match deposit; amount does not have to equal paid_amount
		bt = create_test_bank_transaction(self.bank_account, deposit=99.99)

		matches = get_linked_payments(
			bank_transaction_name=bt.name,
			document_types=["purchase_invoice"],
			from_date=add_days(nowdate(), -30),
			to_date=add_days(nowdate(), 1),
		)

		rows = self._match_rows_for_doctype(matches, "Purchase Invoice", pi.name)
		self.assertEqual(len(rows), 1, f"Expected 1 match for paid refund PI, got {len(rows)}: {rows}")

		row = rows[0]
		# rank >= 1 (the matching query always adds +1 to the rank)
		self.assertGreaterEqual(int(row[0]), 1)
		# paid_amount is returned signed (negative for refund PIs)
		self.assertAlmostEqual(flt(row[3]), -31.27, places=2)

	# -----------------------------------------------------------------------
	# Test 13 — get_linked_payments returns paid refund SI for withdrawal BT
	# -----------------------------------------------------------------------

	def test_get_linked_payments_returns_paid_refund_si_for_withdrawal(self):
		"""A paid refund SI (Sales Invoice Payment row with negative amount
		against the bank GL) must appear as a matching candidate for a
		withdrawal BT when document_types includes 'sales_invoice'. Covers the
		new get_si_matching_query(for_withdrawal=True) branch end-to-end through
		the whitelisted get_linked_payments API.
		"""
		si = create_test_sales_invoice(outstanding=50, is_return=1)

		# Insert the SIP row pointing at the test bank GL with a negative amount.
		# This is the same fixture pattern used by test 4 to bypass
		# set_account_for_mode_of_payment which would overwrite the account
		# from the Mode of Payment configuration during validate.
		frappe.get_doc({
			"doctype": "Sales Invoice Payment",
			"parent": si.name,
			"parenttype": "Sales Invoice",
			"parentfield": "payments",
			"mode_of_payment": "Cash",
			"account": TEST_BANK_GL_ACCOUNT,
			"amount": -50.0,
			"base_amount": -50.0,
		}).insert(ignore_permissions=True)

		bt = create_test_bank_transaction(self.bank_account, withdrawal=99.99)

		matches = get_linked_payments(
			bank_transaction_name=bt.name,
			document_types=["sales_invoice"],
			from_date=add_days(nowdate(), -30),
			to_date=add_days(nowdate(), 1),
		)

		rows = self._match_rows_for_doctype(matches, "Sales Invoice", si.name)
		self.assertEqual(len(rows), 1, f"Expected 1 match for paid refund SI, got {len(rows)}: {rows}")

		row = rows[0]
		self.assertGreaterEqual(int(row[0]), 1)
		# paid_amount comes from sip.amount which is negative for refunds
		self.assertAlmostEqual(flt(row[3]), -50.0, places=2)

	# -----------------------------------------------------------------------
	# Test 14 — exact match: BT amount matches |paid_amount|
	# -----------------------------------------------------------------------

	def test_pi_matching_exact_match_for_deposit_amount_match(self):
		"""With 'exact_match' in document_types and BT.deposit=31.27, a paid
		refund PI of paid_amount=-31.27 MUST appear (ABS(-31.27) == ABS(31.27)).
		Guards the for_deposit=True ABS-equality branch in get_pi_matching_query.
		"""
		pi = create_test_purchase_invoice(
			outstanding=31.27,
			is_paid=1,
			is_return=1,
			cash_bank_account=TEST_BANK_GL_ACCOUNT,
			paid_amount=-31.27,
		)
		bt = create_test_bank_transaction(self.bank_account, deposit=31.27)

		matches = get_linked_payments(
			bank_transaction_name=bt.name,
			document_types=["purchase_invoice", "exact_match"],
			from_date=add_days(nowdate(), -30),
			to_date=add_days(nowdate(), 1),
		)

		rows = self._match_rows_for_doctype(matches, "Purchase Invoice", pi.name)
		self.assertEqual(len(rows), 1, f"Expected exact-match hit, got {len(rows)}: {rows}")
		self.assertAlmostEqual(flt(rows[0][3]), -31.27, places=2)

	# -----------------------------------------------------------------------
	# Test 15 — exact match miss: BT amount does NOT match |paid_amount|
	# -----------------------------------------------------------------------

	def test_pi_matching_exact_match_for_deposit_amount_mismatch(self):
		"""With 'exact_match' and BT.deposit=31.22 but PI paid_amount=-31.27,
		the PI MUST NOT appear because ABS(-31.27) != ABS(31.22). Guards
		against the exact-match SQL branch accidentally accepting near-misses.
		"""
		pi = create_test_purchase_invoice(
			outstanding=31.27,
			is_paid=1,
			is_return=1,
			cash_bank_account=TEST_BANK_GL_ACCOUNT,
			paid_amount=-31.27,
		)
		bt = create_test_bank_transaction(self.bank_account, deposit=31.22)

		matches = get_linked_payments(
			bank_transaction_name=bt.name,
			document_types=["purchase_invoice", "exact_match"],
			from_date=add_days(nowdate(), -30),
			to_date=add_days(nowdate(), 1),
		)

		rows = self._match_rows_for_doctype(matches, "Purchase Invoice", pi.name)
		self.assertEqual(len(rows), 0, f"Expected no exact-match for mismatched amount, got: {rows}")
