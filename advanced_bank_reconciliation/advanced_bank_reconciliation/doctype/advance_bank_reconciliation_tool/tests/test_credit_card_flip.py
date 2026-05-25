# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt
"""Tests for the credit-card deposit/withdrawal flip applied during bank
statement import.

The flip is scoped to the ABR Bank Statement Importer (``publish_records``)
path only. Credit-card statements typically expose charges and payments on a
single "Amount" column; for accounts flagged ``is_credit_card=1`` the importer
swaps deposit and withdrawal so charges land in withdrawal (the correct side
for an asset-treated card).

Manual Bank Transaction creation and direct API insertions are NOT flipped;
the caller is expected to provide values already in the correct orientation.
"""
import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.bank_statement_importer.bank_statement_importer import (
    publish_records,
)

from .fixtures import (
    TEST_BANK,
    TEST_COMPANY,
    _get_parent_bank_account,
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


def _build_importer_dataset(bank_account, deposit, withdrawal, reference, currency):
    """Build the [header, data_row] dataset shape expected by publish_records."""
    return [
        ["Date", "Deposit", "Withdrawal", "Description", "Reference",
         "Bank Account", "Currency", "Is Duplicated"],
        [
            nowdate(),
            deposit,
            withdrawal,
            "_ABR BSI flip test",
            reference,
            bank_account,
            currency,
            0,
        ],
    ]


def _import_one_row(bank_account, deposit, withdrawal, reference=None):
    """Helper to push a single row through publish_records and return the
    resulting Bank Transaction's deposit/withdrawal values.
    """
    if reference is None:
        reference = f"_ABR-BSI-CC-{frappe.generate_hash(length=8)}"

    gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
    currency = frappe.db.get_value("Account", gl_account, "account_currency")

    dataset = _build_importer_dataset(
        bank_account, deposit, withdrawal, reference, currency
    )
    import_success = publish_records(json.dumps(dataset), importer_data=None)

    bt = frappe.get_all(
        "Bank Transaction",
        filters={"bank_account": bank_account, "reference_number": reference},
        fields=["name", "deposit", "withdrawal"],
        limit=1,
    )
    return import_success, bt[0] if bt else None


class TestCreditCardAmountFlip(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.normal_bank_account = setup_abr_test_data(TEST_COMPANY)
        cls.cc_bank_account = ensure_credit_card_bank_account(TEST_COMPANY)
        frappe.db.commit()

    # ------------------------------------------------------------------
    # Flip is scoped to the importer path
    # ------------------------------------------------------------------

    def test_manual_insert_on_credit_card_account_does_not_flip(self):
        """A manually inserted BT on a credit-card account must NOT be flipped.

        The user is expected to enter values in the correct orientation when
        creating BTs by hand or via the REST API. Only statement-import flows
        invert the sign.
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
                "withdrawal": 100.0,
                "reference_number": "_ABR-CC-MANUAL",
                "description": "_ABR Test manual insert no flip",
                "currency": account_currency,
            }
        )
        bt.insert(ignore_permissions=True)
        bt.reload()
        self.assertAlmostEqual(flt(bt.deposit), 0.0, places=2,
                               msg="manual insert must not flip deposit")
        self.assertAlmostEqual(flt(bt.withdrawal), 100.0, places=2,
                               msg="manual insert must not flip withdrawal")

    # ------------------------------------------------------------------
    # Flip via the bank statement importer
    # ------------------------------------------------------------------

    def test_flip_via_importer_swaps_deposit_to_withdrawal(self):
        """Row imported with deposit=120 on a credit-card account: after import
        deposit must be 0 and withdrawal must be 120.
        """
        success, bt = _import_one_row(self.cc_bank_account, 120.0, 0.0)
        self.assertTrue(success, "publish_records did not report success")
        self.assertIsNotNone(bt, "Bank Transaction not created via importer")
        self.assertAlmostEqual(flt(bt["deposit"]), 0.0, places=2,
                               msg="deposit should be 0 after credit-card flip")
        self.assertAlmostEqual(flt(bt["withdrawal"]), 120.0, places=2,
                               msg="withdrawal should be 120 after credit-card flip")

    def test_flip_via_importer_swaps_withdrawal_to_deposit(self):
        """Row imported with withdrawal=50 on a credit-card account: after
        import withdrawal must be 0 and deposit must be 50.
        """
        success, bt = _import_one_row(self.cc_bank_account, 0.0, 50.0)
        self.assertTrue(success, "publish_records did not report success")
        self.assertIsNotNone(bt, "Bank Transaction not created via importer")
        self.assertAlmostEqual(flt(bt["deposit"]), 50.0, places=2,
                               msg="deposit should be 50 after credit-card flip")
        self.assertAlmostEqual(flt(bt["withdrawal"]), 0.0, places=2,
                               msg="withdrawal should be 0 after credit-card flip")

    def test_no_flip_via_importer_for_normal_account(self):
        """Row imported on a non-credit-card account with deposit=100 must
        remain deposit=100 after import.
        """
        success, bt = _import_one_row(self.normal_bank_account, 100.0, 0.0)
        self.assertTrue(success, "publish_records did not report success")
        self.assertIsNotNone(bt, "Bank Transaction not created via importer")
        self.assertAlmostEqual(flt(bt["deposit"]), 100.0, places=2,
                               msg="deposit should remain 100 (no flip on non-credit-card)")
        self.assertAlmostEqual(flt(bt["withdrawal"]), 0.0, places=2,
                               msg="withdrawal should remain 0 (no flip on non-credit-card)")

    # ------------------------------------------------------------------
    # Enabling the flag must not touch existing BTs
    # ------------------------------------------------------------------

    def test_existing_bts_unchanged_when_flag_enabled(self):
        """Enabling is_credit_card on a Bank Account after BTs already exist
        must not touch those BTs. The flip is applied at import time only;
        toggling the flag later has no effect on historical data.
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
        self.assertAlmostEqual(flt(bt.deposit), 200.0, places=2)
        self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2)

        frappe.db.set_value(
            "Bank Account", self.normal_bank_account, "is_credit_card", 1
        )
        try:
            bt.description = "_ABR Test toggle no re-flip (updated)"
            bt.save(ignore_permissions=True)
            bt.reload()
            self.assertAlmostEqual(flt(bt.deposit), 200.0, places=2,
                                   msg="deposit must remain 200 after save with flag enabled")
            self.assertAlmostEqual(flt(bt.withdrawal), 0.0, places=2,
                                   msg="withdrawal must remain 0 after save with flag enabled")
        finally:
            frappe.db.set_value(
                "Bank Account", self.normal_bank_account, "is_credit_card", 0
            )
