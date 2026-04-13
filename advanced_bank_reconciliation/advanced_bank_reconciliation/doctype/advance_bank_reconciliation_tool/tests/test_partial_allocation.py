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
from frappe.utils import flt

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	_normalise_pe_to_target_invoice,
	_signed_cap,
	create_payment_entry_for_invoice,
	reconcile_vouchers,
)

from .fixtures import (
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
