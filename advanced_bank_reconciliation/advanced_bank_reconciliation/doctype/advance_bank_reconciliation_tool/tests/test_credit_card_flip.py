# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Tests for the credit-card amount flip applied at Bank Transaction before_insert.

The flip_amount_for_credit_card hook swaps deposit and withdrawal on the
document when the target Bank Account has is_credit_card=1. This ensures
credit-card statements (where positive amounts represent charges) land in
withdrawal rather than deposit so they reconcile correctly against accounts
treated as Bank/Asset.
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from .fixtures import (
    TEST_BANK,
    TEST_BANK_ACCOUNT_NAME,
    TEST_BANK_GL_ACCOUNT,
    TEST_COMPANY,
    _get_parent_bank_account,
    create_test_bank_transaction,
    setup_abr_test_data,
)

TEST_CREDIT_CARD_ACCOUNT_NAME = "_ABR Test Credit Card Account"
TEST_CREDIT_CARD_GL_ACCOUNT = "_ABR Test Credit Card Account - _TC"
TEST_CREDIT_CARD_BANK_ACCOUNT = f"{TEST_CREDIT_CARD_ACCOUNT_NAME} - {TEST_BANK}"


def ensure_credit_card_bank_account(company=TEST_COMPANY):
    """Create a Bank Account with is_credit_card=1. Idempotent."""
    if not frappe.db.exists("Bank", TEST_BANK):
        frappe.get_doc({"doctype": "Bank", "bank_name": TEST_BANK}).insert(
            ignore_permissions=True, ignore_if_duplicate=True
        )

    if not frappe.db.exists("Account", TEST_CREDIT_CARD_GL_ACCOUNT):
        parent = _get_parent_bank_account(company)
        frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": TEST_CREDIT_CARD_ACCOUNT_NAME,
                "parent_account": parent,
                "company": company,
                "account_type": "Bank",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True, ignore_if_duplicate=True)

    if not frappe.db.exists("Bank Account", TEST_CREDIT_CARD_BANK_ACCOUNT):
        ba = frappe.get_doc(
            {
                "doctype": "Bank Account",
                "account_name": TEST_CREDIT_CARD_ACCOUNT_NAME,
                "bank": TEST_BANK,
                "account": TEST_CREDIT_CARD_GL_ACCOUNT,
                "is_company_account": 1,
                "is_credit_card": 1,
                "company": company,
            }
        )
        ba.insert(ignore_permissions=True, ignore_if_duplicate=True)
    else:
        # Ensure the flag is set in case the account was created before this
        # field existed (e.g. a previous partial test run).
        frappe.db.set_value(
            "Bank Account", TEST_CREDIT_CARD_BANK_ACCOUNT, "is_credit_card", 1
        )

    return TEST_CREDIT_CARD_BANK_ACCOUNT


class TestCreditCardAmountFlip(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.normal_bank_account = setup_abr_test_data(TEST_COMPANY)
        cls.cc_bank_account = ensure_credit_card_bank_account(TEST_COMPANY)
        frappe.db.commit()

    def test_flip_swaps_deposit_to_withdrawal(self):
        """BT inserted with deposit=100 on a credit-card account: after insert
        deposit must be 0 and withdrawal must be 100.
        """
        bt = create_test_bank_transaction(
            self.cc_bank_account,
            deposit=100.0,
            withdrawal=0.0,
        )
        bt.reload()
        self.assertAlmostEqual(flt(bt.deposit), 0.0, places=2)
        self.assertAlmostEqual(flt(bt.withdrawal), 100.0, places=2)

    def test_flip_swaps_withdrawal_to_deposit(self):
        """BT inserted with withdrawal=50 on a credit-card account: after insert
        withdrawal must be 0 and deposit must be 50.
        """
        bt = create_test_bank_transaction(
            self.cc_bank_account,
            deposit=0.0,
            withdrawal=50.0,
        )
        bt.reload()
        self.assertAlmostEqual(flt(bt.deposit), 50.0, places=2)
        self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2)

    def test_no_flip_for_normal_bank_account(self):
        """BT inserted on a normal (non-credit-card) account with deposit=100
        must remain deposit=100 after insert.
        """
        bt = create_test_bank_transaction(
            self.normal_bank_account,
            deposit=100.0,
            withdrawal=0.0,
        )
        bt.reload()
        self.assertAlmostEqual(flt(bt.deposit), 100.0, places=2)
        self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2)

    def test_no_flip_when_both_zero(self):
        """BT with both deposit=0 and withdrawal=0 on a credit-card account:
        the hook must be a no-op and not produce an error.
        """
        gl_account = frappe.db.get_value(
            "Bank Account", self.cc_bank_account, "account"
        )
        account_currency = frappe.db.get_value(
            "Account", gl_account, "account_currency"
        )
        bt = frappe.get_doc(
            {
                "doctype": "Bank Transaction",
                "date": nowdate(),
                "bank_account": self.cc_bank_account,
                "deposit": 0.0,
                "withdrawal": 0.0,
                "reference_number": "_ABR-CC-ZERO",
                "description": "_ABR Test zero flip",
                "currency": account_currency,
            }
        )
        bt.insert(ignore_permissions=True)
        bt.submit()
        bt.reload()
        self.assertAlmostEqual(flt(bt.deposit), 0.0, places=2)
        self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2)

    def test_flip_only_on_insert_not_on_update(self):
        """Flip occurs on insert only; subsequent saves do not re-flip.

        Creates a draft BT on a credit-card account, verifies the flip on insert,
        then saves again (still draft) and asserts the values are unchanged.
        A second save on the same draft must NOT re-flip deposit back to 75.
        """
        gl_account = frappe.db.get_value(
            "Bank Account", self.cc_bank_account, "account"
        )
        account_currency = frappe.db.get_value(
            "Account", gl_account, "account_currency"
        )
        bt = frappe.get_doc(
            {
                "doctype": "Bank Transaction",
                "date": nowdate(),
                "bank_account": self.cc_bank_account,
                "deposit": 75.0,
                "withdrawal": 0.0,
                "reference_number": "_ABR-CC-NOREFLIP",
                "description": "_ABR Test no re-flip",
                "currency": account_currency,
            }
        )
        bt.insert(ignore_permissions=True)
        # After insert: flip must have occurred.
        self.assertAlmostEqual(flt(bt.deposit), 0.0, places=2,
                               msg="deposit should be 0 after credit-card flip on insert")
        self.assertAlmostEqual(flt(bt.withdrawal), 75.0, places=2,
                               msg="withdrawal should be 75 after credit-card flip on insert")

        # Save again (still draft). The before_insert hook must NOT fire on save().
        bt.description = "_ABR Test no re-flip (updated)"
        bt.save(ignore_permissions=True)
        bt.reload()

        # Values must remain as set by the first insert — no re-flip.
        self.assertAlmostEqual(flt(bt.deposit), 0.0, places=2,
                               msg="deposit must stay 0 after subsequent save; re-flip must not occur")
        self.assertAlmostEqual(flt(bt.withdrawal), 75.0, places=2,
                               msg="withdrawal must stay 75 after subsequent save; re-flip must not occur")

    def test_toggle_flag_does_not_re_flip_existing_bts(self):
        """Enabling is_credit_card on a Bank Account after BTs already exist
        must not flip those existing BTs on subsequent save.

        Creates a draft BT on a non-credit-card account (deposit=200, no flip).
        Then enables is_credit_card on that account and saves the BT again.
        The before_insert hook must not fire on save(), so deposit stays 200.
        """
        gl_account = frappe.db.get_value(
            "Bank Account", self.normal_bank_account, "account"
        )
        account_currency = frappe.db.get_value(
            "Account", gl_account, "account_currency"
        )
        bt = frappe.get_doc(
            {
                "doctype": "Bank Transaction",
                "date": nowdate(),
                "bank_account": self.normal_bank_account,
                "deposit": 200.0,
                "withdrawal": 0.0,
                "reference_number": "_ABR-CC-TOGGLE",
                "description": "_ABR Test toggle no re-flip",
                "currency": account_currency,
            }
        )
        bt.insert(ignore_permissions=True)
        # No flip on insert (account is not credit card).
        self.assertAlmostEqual(flt(bt.deposit), 200.0, places=2,
                               msg="deposit should remain 200 (no flip on non-credit-card account)")
        self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2)

        # Enable is_credit_card on the normal bank account temporarily.
        frappe.db.set_value(
            "Bank Account", self.normal_bank_account, "is_credit_card", 1
        )
        try:
            # Save the existing BT (before_insert will NOT fire).
            bt.description = "_ABR Test toggle no re-flip (updated)"
            bt.save(ignore_permissions=True)
            bt.reload()

            # Values must be unchanged: the save must not trigger a flip.
            self.assertAlmostEqual(flt(bt.deposit), 200.0, places=2,
                                   msg="deposit must remain 200 after save with flag enabled; no re-flip")
            self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2,
                                   msg="withdrawal must remain 0 after save with flag enabled")
        finally:
            frappe.db.set_value(
                "Bank Account", self.normal_bank_account, "is_credit_card", 0
            )

    def test_flip_happens_via_bank_statement_importer(self):
        """Route a row through ABR's bank_statement_importer publish_records
        path and verify the flip was applied. publish_records calls
        frappe.new_doc + insert() + submit() which fires before_insert.
        """
        import json

        from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.bank_statement_importer.bank_statement_importer import (
            publish_records,
        )

        gl_account = frappe.db.get_value(
            "Bank Account", self.cc_bank_account, "account"
        )
        account_currency = frappe.db.get_value(
            "Account", gl_account, "account_currency"
        )

        # Build the dataset format expected by publish_records:
        # [header_row, data_row, ...]
        # data row: [date, deposit, withdrawal, description, reference_number,
        #            bank_account, currency, is_duplicated]
        dataset = [
            ["Date", "Deposit", "Withdrawal", "Description", "Reference",
             "Bank Account", "Currency", "Is Duplicated"],
            [
                nowdate(),
                120.0,         # deposit (will be flipped to withdrawal)
                0.0,           # withdrawal
                "_ABR BSI flip test",
                "_ABR-BSI-CC-001",
                self.cc_bank_account,
                account_currency,
                0,
            ],
        ]

        publish_records(json.dumps(dataset), importer_data=None)

        bt = frappe.get_all(
            "Bank Transaction",
            filters={
                "bank_account": self.cc_bank_account,
                "reference_number": "_ABR-BSI-CC-001",
            },
            fields=["name", "deposit", "withdrawal"],
            limit=1,
        )
        self.assertEqual(len(bt), 1, "Bank Transaction not created via BSI")
        self.assertAlmostEqual(flt(bt[0]["deposit"]), 0.0, places=2,
                               msg="deposit should be 0 after credit-card flip")
        self.assertAlmostEqual(flt(bt[0]["withdrawal"]), 120.0, places=2,
                               msg="withdrawal should be 120 after credit-card flip")
