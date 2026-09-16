# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt

import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, getdate, nowdate
from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
    get_queries as get_standard_matching_queries,
)

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
    create_payment_entries_bulk,
    get_linked_payments,
    get_matching_queries,
    reconcile_vouchers,
)
from advanced_bank_reconciliation.advanced_bank_reconciliation.overrides.bank_transaction import (
    get_voucher_allocation_amount,
)
from advanced_bank_reconciliation.api.matching import get_match_candidates, submit_match

from .fixtures import (
    TEST_BANK,
    TEST_COMPANY,
    create_test_sales_invoice,
    ensure_erpnext_test_company,
    ensure_fiscal_year_for_company,
)


MATCHING_MODULE = (
    "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype."
    "advance_bank_reconciliation_tool.advance_bank_reconciliation_tool"
)


class TestInternalTransferMatching(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_erpnext_test_company()
        ensure_fiscal_year_for_company(TEST_COMPANY)
        if not frappe.db.exists("Bank", TEST_BANK):
            frappe.get_doc({"doctype": "Bank", "bank_name": TEST_BANK}).insert(
                ignore_permissions=True
            )
        cls.company_currency = frappe.db.get_value(
            "Company", TEST_COMPANY, "default_currency"
        )
        cls.foreign_currency = "USD" if cls.company_currency != "USD" else "EUR"
        cls.source_bank_account, cls.source_gl_account = cls._ensure_bank_account(
            "Transfer Source", cls.company_currency
        )
        cls.target_bank_account, cls.target_gl_account = cls._ensure_bank_account(
            "Transfer Target", cls.foreign_currency
        )
        cls.same_currency_bank_account, cls.same_currency_gl_account = (
            cls._ensure_bank_account("Transfer Same Currency", cls.company_currency)
        )
        frappe.db.commit()

    @classmethod
    def _ensure_bank_account(cls, suffix, currency):
        abbr = frappe.db.get_value("Company", TEST_COMPANY, "abbr")
        account_name = f"_ABR {suffix}"
        gl_account = f"{account_name} - {abbr}"

        if not frappe.db.exists("Account", gl_account):
            parent_account = frappe.db.get_value(
                "Account",
                {
                    "company": TEST_COMPANY,
                    "root_type": "Asset",
                    "is_group": 1,
                },
                "name",
            )
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": account_name,
                    "parent_account": parent_account,
                    "company": TEST_COMPANY,
                    "account_type": "Bank",
                    "account_currency": currency,
                    "is_group": 0,
                }
            ).insert(ignore_permissions=True)

        bank_account_name = f"_ABR {suffix} - {TEST_BANK}"
        if not frappe.db.exists("Bank Account", bank_account_name):
            bank_account = frappe.get_doc(
                {
                    "doctype": "Bank Account",
                    "account_name": f"_ABR {suffix}",
                    "bank": TEST_BANK,
                    "account": gl_account,
                    "is_company_account": 1,
                    "company": TEST_COMPANY,
                }
            ).insert(ignore_permissions=True)
            bank_account_name = bank_account.name

        return bank_account_name, gl_account

    def _create_internal_transfer(
        self, paid_amount=100, received_amount=90, target_gl_account=None
    ):
        payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Internal Transfer",
                "company": TEST_COMPANY,
                "posting_date": nowdate(),
                "paid_from": self.source_gl_account,
                "paid_to": target_gl_account or self.target_gl_account,
                "paid_amount": paid_amount,
                "received_amount": received_amount,
                "source_exchange_rate": 1,
                "target_exchange_rate": paid_amount / received_amount,
                "reference_no": "_ABR-INTERNAL-TRANSFER",
                "reference_date": nowdate(),
            }
        )
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        return payment_entry

    def _create_bank_transaction(self, bank_account, *, deposit=0, withdrawal=0):
        currency = frappe.db.get_value(
            "Account",
            frappe.db.get_value("Bank Account", bank_account, "account"),
            "account_currency",
        )
        bank_transaction = frappe.get_doc(
            {
                "doctype": "Bank Transaction",
                "date": nowdate(),
                "bank_account": bank_account,
                "deposit": deposit,
                "withdrawal": withdrawal,
                "currency": currency,
                "reference_number": "_ABR-INTERNAL-TRANSFER",
                "description": "_ABR Internal transfer test",
            }
        )
        bank_transaction.insert(ignore_permissions=True)
        bank_transaction.submit()
        return bank_transaction

    def _get_payment_entry_candidate(
        self, bank_transaction, payment_entry_name, exact_match=0
    ):
        document_types = ["payment_entry"]
        if exact_match:
            document_types.append("exact_match")

        matches = get_linked_payments(
            bank_transaction.name,
            document_types,
            add_days(nowdate(), -1),
            add_days(nowdate(), 1),
            0,
            None,
            None,
        )
        return next(row for row in matches if row[2] == payment_entry_name)

    def test_standard_hook_does_not_repeat_core_queries(self):
        transaction = SimpleNamespace(deposit=100, withdrawal=0)
        common_filters = frappe._dict(bank_account=self.source_gl_account)

        with (
            patch(
                f"{MATCHING_MODULE}.get_pe_matching_query", return_value="payment query"
            ) as payment_query,
            patch(
                f"{MATCHING_MODULE}.get_je_matching_query", return_value="journal query"
            ) as journal_query,
        ):
            queries = get_matching_queries(
                self.source_gl_account,
                TEST_COMPANY,
                transaction,
                ["payment_entry", "journal_entry"],
                False,
                "paid_to",
                nowdate(),
                nowdate(),
                False,
                None,
                None,
                common_filters,
            )

            self.assertEqual(queries, [])
            payment_query.assert_not_called()
            journal_query.assert_not_called()

        standard_transaction = frappe._dict(
            deposit=100,
            withdrawal=0,
            unallocated_amount=100,
            reference_number="_ABR-STANDARD-HOOK",
            party_type=None,
            party=None,
        )
        standard_queries = get_standard_matching_queries(
            self.source_gl_account,
            TEST_COMPANY,
            standard_transaction,
            ["payment_entry", "journal_entry"],
            nowdate(),
            nowdate(),
            False,
            None,
            None,
            False,
            common_filters,
        )

        self.assertEqual(len(standard_queries), 2)

    def test_advanced_matcher_keeps_payment_and_journal_queries(self):
        transaction = SimpleNamespace(deposit=100, withdrawal=0)

        with (
            patch(
                f"{MATCHING_MODULE}.get_pe_matching_query", return_value="payment query"
            ),
            patch(
                f"{MATCHING_MODULE}.get_je_matching_query", return_value="journal query"
            ),
        ):
            queries = get_matching_queries(
                self.source_gl_account,
                TEST_COMPANY,
                transaction,
                ["payment_entry", "journal_entry"],
                False,
                "paid_to",
                nowdate(),
                nowdate(),
                False,
                None,
                None,
            )

            self.assertEqual(queries, ["payment query", "journal query"])

    def test_non_transfer_payment_keeps_supplied_signed_amount(self):
        for payment_type, supplied_amount in (("Pay", -30.0), ("Receive", 30.0)):
            with self.subTest(payment_type=payment_type):
                voucher = {
                    "payment_doctype": "Payment Entry",
                    "payment_name": "_ABR-NORMAL-PAYMENT",
                    "amount": supplied_amount,
                }

                with patch("frappe.db.get_value", return_value=payment_type):
                    amount = get_voucher_allocation_amount(voucher, 2)

                self.assertEqual(amount, supplied_amount)

    def test_cross_currency_transfer_matches_each_bank_side(self):
        payment_entry = self._create_internal_transfer()
        source_transaction = self._create_bank_transaction(
            self.source_bank_account, withdrawal=100
        )
        target_transaction = self._create_bank_transaction(
            self.target_bank_account, deposit=90
        )

        source_candidate = self._get_payment_entry_candidate(
            source_transaction, payment_entry.name, exact_match=1
        )
        target_candidate = self._get_payment_entry_candidate(
            target_transaction, payment_entry.name, exact_match=1
        )

        self.assertAlmostEqual(flt(source_candidate[3]), 100, places=2)
        self.assertEqual(source_candidate[9], self.company_currency)
        self.assertAlmostEqual(flt(target_candidate[3]), 90, places=2)
        self.assertEqual(target_candidate[9], self.foreign_currency)

    def test_same_currency_transfer_matches_each_bank_side(self):
        payment_entry = self._create_internal_transfer(
            paid_amount=75,
            received_amount=75,
            target_gl_account=self.same_currency_gl_account,
        )
        source_transaction = self._create_bank_transaction(
            self.source_bank_account, withdrawal=75
        )
        target_transaction = self._create_bank_transaction(
            self.same_currency_bank_account, deposit=75
        )

        source_candidate = self._get_payment_entry_candidate(
            source_transaction, payment_entry.name
        )
        target_candidate = self._get_payment_entry_candidate(
            target_transaction, payment_entry.name
        )

        self.assertAlmostEqual(flt(source_candidate[3]), 75, places=2)
        self.assertEqual(source_candidate[9], self.company_currency)
        self.assertAlmostEqual(flt(target_candidate[3]), 75, places=2)
        self.assertEqual(target_candidate[9], self.company_currency)

        reconcile_vouchers(
            target_transaction.name,
            json.dumps(
                [
                    {
                        "payment_doctype": "Payment Entry",
                        "payment_name": payment_entry.name,
                        "amount": 999,
                    }
                ]
            ),
        )
        target_transaction.reload()
        payment_entry.reload()
        self.assertAlmostEqual(
            flt(target_transaction.payment_entries[0].allocated_amount), 75, places=2
        )
        self.assertAlmostEqual(flt(target_transaction.unallocated_amount), 0, places=2)
        self.assertFalse(payment_entry.clearance_date)

        reconcile_vouchers(
            source_transaction.name,
            json.dumps(
                [
                    {
                        "payment_doctype": "Payment Entry",
                        "payment_name": payment_entry.name,
                        "amount": 999,
                    }
                ]
            ),
        )
        source_transaction.reload()
        payment_entry.reload()
        self.assertAlmostEqual(
            flt(source_transaction.payment_entries[0].allocated_amount), 75, places=2
        )
        self.assertAlmostEqual(flt(source_transaction.unallocated_amount), 0, places=2)
        self.assertEqual(payment_entry.clearance_date, source_transaction.date)

    def test_reconciliation_uses_ledger_amount_and_clears_after_both_sides(self):
        payment_entry = self._create_internal_transfer()
        source_transaction = self._create_bank_transaction(
            self.source_bank_account, withdrawal=100
        )
        target_transaction = self._create_bank_transaction(
            self.target_bank_account, deposit=90
        )

        reconcile_vouchers(
            source_transaction.name,
            json.dumps(
                [
                    {
                        "payment_doctype": "Payment Entry",
                        "payment_name": payment_entry.name,
                        "amount": 999,
                    }
                ]
            ),
        )
        source_transaction.reload()
        payment_entry.reload()

        self.assertAlmostEqual(
            flt(source_transaction.payment_entries[0].allocated_amount), 100, places=2
        )
        self.assertAlmostEqual(flt(source_transaction.unallocated_amount), 0, places=2)
        self.assertGreaterEqual(flt(source_transaction.unallocated_amount), 0)
        self.assertFalse(payment_entry.clearance_date)

        reconcile_vouchers(
            target_transaction.name,
            json.dumps(
                [
                    {
                        "payment_doctype": "Payment Entry",
                        "payment_name": payment_entry.name,
                        "amount": 999,
                    }
                ]
            ),
        )
        target_transaction.reload()
        payment_entry.reload()

        self.assertAlmostEqual(
            flt(target_transaction.payment_entries[0].allocated_amount), 90, places=2
        )
        self.assertAlmostEqual(flt(target_transaction.unallocated_amount), 0, places=2)
        self.assertGreaterEqual(flt(target_transaction.unallocated_amount), 0)
        self.assertEqual(payment_entry.clearance_date, target_transaction.date)

    def _api_candidate(self, transaction, payment_entry):
        result = get_match_candidates(
            transaction.name,
            document_types=["payment_entry"],
            from_date=add_days(nowdate(), -1),
            to_date=add_days(nowdate(), 1),
        )
        return next(
            row
            for row in result["candidates"]
            if row["voucher_name"] == payment_entry.name
        )

    def test_new_ui_api_matches_both_currencies_and_ignores_edited_amounts(self):
        for same_currency in (False, True):
            with self.subTest(same_currency=same_currency):
                received = 100 if same_currency else 90
                target_bank = (
                    self.same_currency_bank_account
                    if same_currency
                    else self.target_bank_account
                )
                payment = self._create_internal_transfer(
                    received_amount=received,
                    target_gl_account=self.same_currency_gl_account
                    if same_currency
                    else None,
                )
                source = self._create_bank_transaction(
                    self.source_bank_account, withdrawal=100
                )
                target = self._create_bank_transaction(target_bank, deposit=received)
                transactions = (target, source) if same_currency else (source, target)
                for index, transaction in enumerate(transactions):
                    candidate = self._api_candidate(transaction, payment)
                    expected = transaction.deposit or transaction.withdrawal
                    self.assertTrue(candidate["is_internal_transfer"])
                    self.assertEqual(candidate["currency"], transaction.currency)
                    self.assertAlmostEqual(candidate["amount"], expected)
                    candidate["amount"] = 999 if index == 0 else 1
                    result = submit_match(transaction.name, [candidate])
                    self.assertEqual(result["status"], "Reconciled")
                    self.assertAlmostEqual(
                        result["linked_payments"][0]["allocated_amount"], expected
                    )
                    payment.reload()
                    self.assertEqual(bool(payment.clearance_date), index == 1)

    def test_new_ui_api_reserves_ordinary_amounts_and_supports_split_bank_legs(self):
        payment = self._create_internal_transfer()
        expense = frappe.db.get_value(
            "Account",
            {"company": TEST_COMPANY, "root_type": "Expense", "is_group": 0},
            "name",
        )
        journal = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "company": TEST_COMPANY,
                "posting_date": nowdate(),
                "accounts": [
                    {"account": expense, "debit_in_account_currency": 20},
                    {
                        "account": self.source_gl_account,
                        "credit_in_account_currency": 20,
                    },
                ],
            }
        ).insert()
        journal.submit()
        first = self._create_bank_transaction(self.source_bank_account, withdrawal=60)
        candidate = self._api_candidate(first, payment)
        result = submit_match(
            first.name,
            [
                candidate,
                {
                    "voucher_type": "Journal Entry",
                    "voucher_name": journal.name,
                    "amount": 20,
                },
            ],
        )
        amounts = {
            row["payment_entry"]: row["allocated_amount"]
            for row in result["linked_payments"]
        }
        self.assertEqual(amounts, {payment.name: 40, journal.name: 20})
        self.assertEqual(result["status"], "Reconciled")
        target = self._create_bank_transaction(self.target_bank_account, deposit=90)
        submit_match(target.name, [self._api_candidate(target, payment)])
        payment.reload()
        self.assertFalse(payment.clearance_date)
        second = self._create_bank_transaction(self.source_bank_account, withdrawal=60)
        candidate = self._api_candidate(second, payment)
        self.assertAlmostEqual(candidate["amount"], 60)
        exact_candidate = self._get_payment_entry_candidate(second, payment.name, exact_match=1)
        self.assertAlmostEqual(exact_candidate[3], 60)
        result = submit_match(second.name, [candidate])
        self.assertAlmostEqual(result["linked_payments"][0]["allocated_amount"], 60)
        self.assertEqual(result["status"], "Reconciled")
        payment.reload()
        self.assertEqual(payment.clearance_date, getdate(second.date))
        first.reload()
        first.remove_payment_entries()
        first.reload()
        payment.reload()
        self.assertFalse(first.payment_entries)
        self.assertEqual(first.unallocated_amount, 60)
        self.assertFalse(payment.clearance_date)

    def test_new_ui_api_rejects_wrong_bank_direction_and_exhausted_leg(self):
        payment = self._create_internal_transfer()
        voucher = {
            "voucher_type": "Payment Entry",
            "voucher_name": payment.name,
            "amount": 100,
        }
        wrong_direction = self._create_bank_transaction(
            self.source_bank_account, deposit=100
        )
        with self.assertRaises(frappe.ValidationError):
            submit_match(wrong_direction.name, [voucher])
        wrong_direction.reload()
        self.assertFalse(wrong_direction.payment_entries)
        source = self._create_bank_transaction(self.source_bank_account, withdrawal=100)
        submit_match(source.name, [voucher])
        exhausted = self._create_bank_transaction(
            self.source_bank_account, withdrawal=100
        )
        with self.assertRaises(frappe.ValidationError):
            submit_match(exhausted.name, [voucher])
        exhausted.reload()
        self.assertFalse(exhausted.payment_entries)
        with self.assertRaisesRegex(frappe.ValidationError, "No amount remains"):
            reconcile_vouchers(exhausted.name, json.dumps([{
                "payment_doctype": "Payment Entry", "payment_name": payment.name, "amount": 100,
            }]))
        exhausted.reload()
        self.assertFalse(exhausted.payment_entries)

    def test_new_ui_api_rejects_mixed_unpaid_return_before_creating_payment(self):
        payment = self._create_internal_transfer()
        group = frappe.get_doc(
            {
                "doctype": "Customer Group",
                "customer_group_name": "_ABR Transfer Return Group",
                "parent_customer_group": "All Customer Groups",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        territory = frappe.get_doc(
            {
                "doctype": "Territory",
                "territory_name": "_ABR Transfer Return Territory",
                "parent_territory": "All Territories",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "_ABR Transfer Return Customer",
                "customer_type": "Individual",
                "customer_group": group.name,
                "territory": territory.name,
            }
        ).insert(ignore_permissions=True)
        invoice = create_test_sales_invoice(
            outstanding=20, is_return=1, customer=customer.name
        )
        transaction = self._create_bank_transaction(
            self.source_bank_account, withdrawal=60
        )
        before = frappe.db.count("Payment Entry")
        for source_type in ("Unpaid Sales Invoice", "Sales Invoice"):
            with self.assertRaisesRegex(
                frappe.ValidationError, "separately from internal transfers"
            ):
                submit_match(
                    transaction.name,
                    [
                        {
                            "voucher_type": "Payment Entry",
                            "voucher_name": payment.name,
                            "amount": 40,
                        },
                        {
                            "voucher_type": "Sales Invoice",
                            "source_type": source_type,
                            "voucher_name": invoice.name,
                            "amount": 20,
                        },
                    ],
                )
        with patch("frappe.enqueue") as enqueue:
            with self.assertRaisesRegex(
                frappe.ValidationError, "separately from internal transfers"
            ):
                create_payment_entries_bulk(
                    transaction.name,
                    [
                        {
                            "doctype": "Unpaid Sales Invoice",
                            "name": invoice.name,
                            "allocated_amount": -20,
                        }
                    ],
                    [
                        {
                            "payment_doctype": "Payment Entry",
                            "payment_name": payment.name,
                            "amount": 40,
                        }
                    ],
                )
            enqueue.assert_not_called()
        transaction.reload()
        self.assertFalse(transaction.payment_entries)
        self.assertEqual(frappe.db.count("Payment Entry"), before)

    def test_existing_refund_blocks_internal_transfer_in_both_apis(self):
        payment = self._create_internal_transfer()
        transaction = self._create_bank_transaction(
            self.source_bank_account, withdrawal=100
        )
        expense = frappe.db.get_value(
            "Account",
            {"company": TEST_COMPANY, "root_type": "Expense", "is_group": 0},
            "name",
        )
        refund = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "company": TEST_COMPANY,
                "posting_date": nowdate(),
                "accounts": [
                    {
                        "account": self.source_gl_account,
                        "debit_in_account_currency": 20,
                    },
                    {"account": expense, "credit_in_account_currency": 20},
                ],
            }
        ).insert()
        refund.submit()
        reconcile_vouchers(
            transaction.name,
            json.dumps(
                [
                    {
                        "payment_doctype": "Journal Entry",
                        "payment_name": refund.name,
                        "amount": -20,
                    }
                ]
            ),
        )
        transaction.reload()
        self.assertEqual(transaction.unallocated_amount, 80)
        with self.assertRaisesRegex(
            frappe.ValidationError, "separately from internal transfers"
        ):
            submit_match(
                transaction.name,
                [
                    {
                        "voucher_type": "Payment Entry",
                        "voucher_name": payment.name,
                        "amount": 80,
                    }
                ],
            )
        with self.assertRaisesRegex(
            frappe.ValidationError, "separately from internal transfers"
        ):
            reconcile_vouchers(
                transaction.name,
                json.dumps(
                    [
                        {
                            "payment_doctype": "Payment Entry",
                            "payment_name": payment.name,
                            "amount": 80,
                        }
                    ]
                ),
            )
        transaction.reload()
        self.assertEqual(transaction.unallocated_amount, 80)
        self.assertEqual(len(transaction.payment_entries), 1)
        payment.reload()
        self.assertFalse(payment.clearance_date)

    def test_legacy_rejects_wrong_direction_draft_and_duplicate_selection(self):
        payment = self._create_internal_transfer()
        voucher = {
            "payment_doctype": "Payment Entry",
            "payment_name": payment.name,
            "amount": 100,
        }
        wrong = self._create_bank_transaction(self.source_bank_account, deposit=100)
        with self.assertRaisesRegex(frappe.ValidationError, "account and direction"):
            reconcile_vouchers(wrong.name, json.dumps([voucher]))
        source = self._create_bank_transaction(self.source_bank_account, withdrawal=200)
        with self.assertRaisesRegex(frappe.ValidationError, "only once"):
            reconcile_vouchers(source.name, json.dumps([voucher, voucher]))
        draft = frappe.copy_doc(source)
        draft.docstatus = 0
        draft.insert()
        self.assertEqual(draft.docstatus, 0)
        with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
            reconcile_vouchers(draft.name, json.dumps([voucher]))
        for transaction in (wrong, source, draft):
            transaction.reload()
            self.assertFalse(transaction.payment_entries)
        payment.reload()
        self.assertFalse(payment.clearance_date)
