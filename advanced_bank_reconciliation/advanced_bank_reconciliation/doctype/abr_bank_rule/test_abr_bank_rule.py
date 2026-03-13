# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt

import logging
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.abr_bank_rule import (
	_conditions_match,
	_load_rules,
	_match_transaction,
	evaluate_condition,
	run_bank_rules,
)
from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	_sanitize_dimensions,
)

# --- Constants ---

TEST_COMPANY = "_Test Company"
TEST_COMPANY_ABBR = "_TC"
ABR_TEST_BANK = "ABR Test Bank"
ABR_MODULE = "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.abr_bank_rule"


# --- Helpers ---


def get_test_logger():
	return logging.getLogger("test_abr_bank_rule")


def make_condition(field_name, condition, value):
	"""Create a mock ABR Bank Rule Condition row."""
	return frappe._dict(field_name=field_name, condition=condition, value=value)


def make_transaction(**kwargs):
	"""Create a mock Bank Transaction dict with sensible defaults."""
	defaults = {
		"deposit": 0,
		"withdrawal": 0,
		"currency": "INR",
		"description": "",
		"reference_number": "",
		"custom_particulars": "",
		"bank_party_name": "",
		"custom_code": "",
	}
	defaults.update(kwargs)
	return frappe._dict(defaults)


def make_mock_rule(conditions, match_any=False, **kwargs):
	"""Create a mock ABR Bank Rule dict for unit tests."""
	defaults = {
		"title": "Mock Rule",
		"conditions": conditions,
		"match_any_condition": match_any,
		"entry_type": "Journal Entry",
		"account": None,
		"party_type": None,
		"party": None,
		"cost_center": None,
	}
	defaults.update(kwargs)
	return frappe._dict(defaults)


def setup_test_bank_account():
	"""Create a test Bank, GL Account, and Bank Account. Idempotent + committed."""
	bank_name = ABR_TEST_BANK

	if not frappe.db.exists("Bank", bank_name):
		frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(
			ignore_if_duplicate=True
		)

	gl_account = f"_Test Bank - {TEST_COMPANY_ABBR}"
	if not frappe.db.exists("Account", gl_account):
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": TEST_COMPANY,
				"account_name": "_Test Bank",
				"parent_account": f"Current Assets - {TEST_COMPANY_ABBR}",
				"account_type": "Bank",
				"is_group": 0,
			}
		).insert(ignore_if_duplicate=True)

	# Bank Account name is auto-generated ({account_name} - {bank}), so query for it
	ba_name = frappe.db.get_value(
		"Bank Account", {"bank": bank_name, "account": gl_account, "company": TEST_COMPANY}
	)
	if not ba_name:
		ba = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": bank_name,
				"bank": bank_name,
				"account": gl_account,
				"is_company_account": 1,
				"company": TEST_COMPANY,
			}
		).insert()
		ba_name = ba.name

	frappe.db.commit()
	return ba_name


def cleanup_test_rules(bank_account):
	"""Delete any leftover ABR Bank Rules for the test bank account."""
	for name in frappe.get_all(
		"ABR Bank Rule", filters={"bank_account": bank_account}, pluck="name"
	):
		frappe.delete_doc("ABR Bank Rule", name, force=True)


def cleanup_test_bank_transactions(bank_account):
	"""Cancel and delete any leftover Bank Transactions for the test bank account."""
	for bt in frappe.get_all(
		"Bank Transaction",
		filters={"bank_account": bank_account},
		fields=["name", "docstatus"],
	):
		if bt.docstatus == 1:
			frappe.get_doc("Bank Transaction", bt.name).cancel()
		frappe.delete_doc("Bank Transaction", bt.name, force=True)


# ============================================================================
# Group 1: Rule Validation
# ============================================================================


class TestABRBankRuleValidation(FrappeTestCase):
	"""Test ABR Bank Rule document validation."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_test_bank_account()

	def tearDown(self):
		frappe.db.rollback()

	def _make_rule(self, **overrides):
		doc_dict = {
			"doctype": "ABR Bank Rule",
			"title": "Validation Test Rule",
			"enabled": 1,
			"priority": 10,
			"company": TEST_COMPANY,
			"bank_account": self.bank_account,
			"entry_type": "Journal Entry",
			"account": f"Sales - {TEST_COMPANY_ABBR}",
			"conditions": [
				{"field_name": "Description", "condition": "Contains", "value": "test"}
			],
		}
		doc_dict.update(overrides)
		return frappe.get_doc(doc_dict)

	def test_rule_without_conditions_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(conditions=[]).insert()

	def test_rule_without_entry_type_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(entry_type="").insert()

	def test_je_rule_without_account_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(entry_type="Journal Entry", account="").insert()

	def test_pe_rule_without_party_type_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				entry_type="Payment Entry", account="", party_type="", party="_Test Customer"
			).insert()

	def test_pe_rule_without_party_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				entry_type="Payment Entry", account="", party_type="Customer", party=""
			).insert()

	def test_valid_je_rule_saves(self):
		rule = self._make_rule()
		rule.insert()
		self.assertTrue(rule.name)

	def test_valid_pe_rule_saves(self):
		rule = self._make_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
		)
		rule.insert()
		self.assertTrue(rule.name)

	def test_condition_without_value_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Description", "condition": "Contains", "value": ""}]
			).insert()

	def test_numeric_operator_on_text_field_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Description", "condition": "Greater than", "value": "100"}]
			).insert()

	def test_numeric_operator_on_deposit_succeeds(self):
		rule = self._make_rule(
			conditions=[{"field_name": "Deposit", "condition": "Greater than", "value": "100"}]
		)
		rule.insert()
		self.assertTrue(rule.name)

	def test_bank_account_company_mismatch_fails(self):
		other_company = "_Test Company 1"
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(company=other_company).insert()

	def test_contains_on_numeric_field_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Deposit", "condition": "Contains", "value": "5"}]
			).insert()

	def test_not_contains_on_numeric_field_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Withdrawal", "condition": "Not Contains", "value": "5"}]
			).insert()

	def test_unknown_field_name_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Nonexistent", "condition": "Equals", "value": "x"}]
			).insert()

	def test_unknown_operator_fails(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_rule(
				conditions=[{"field_name": "Description", "condition": "Starts With", "value": "x"}]
			).insert()


# ============================================================================
# Group 2: Condition Evaluation (pure unit tests, no DB)
# ============================================================================


class TestEvaluateCondition(FrappeTestCase):
	"""Test evaluate_condition() with mock objects."""

	def setUp(self):
		self.logger = get_test_logger()

	# --- Numeric operators on Deposit/Withdrawal ---

	def test_deposit_equals_match(self):
		txn = make_transaction(deposit=100)
		self.assertTrue(evaluate_condition(txn, make_condition("Deposit", "Equals", "100"), self.logger))

	def test_deposit_equals_no_match(self):
		txn = make_transaction(deposit=200)
		self.assertFalse(evaluate_condition(txn, make_condition("Deposit", "Equals", "100"), self.logger))

	def test_withdrawal_greater_than_match(self):
		txn = make_transaction(withdrawal=100)
		self.assertTrue(
			evaluate_condition(txn, make_condition("Withdrawal", "Greater than", "50"), self.logger)
		)

	def test_withdrawal_greater_than_boundary(self):
		txn = make_transaction(withdrawal=50)
		self.assertFalse(
			evaluate_condition(txn, make_condition("Withdrawal", "Greater than", "50"), self.logger)
		)

	def test_deposit_gte_match(self):
		txn = make_transaction(deposit=100)
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Deposit", "Greater than or Equals", "100"), self.logger
			)
		)

	def test_deposit_less_than_match(self):
		txn = make_transaction(deposit=50)
		self.assertTrue(
			evaluate_condition(txn, make_condition("Deposit", "Less Than", "100"), self.logger)
		)

	def test_deposit_lte_match(self):
		txn = make_transaction(deposit=100)
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Deposit", "Less Than or Equals", "100"), self.logger
			)
		)

	def test_deposit_not_equals_match(self):
		txn = make_transaction(deposit=200)
		self.assertTrue(
			evaluate_condition(txn, make_condition("Deposit", "Not Equals", "100"), self.logger)
		)

	# --- Text operators on Description ---

	def test_description_contains_match(self):
		txn = make_transaction(description="Monthly PAYROLL Run")
		self.assertTrue(
			evaluate_condition(txn, make_condition("Description", "Contains", "PAYROLL"), self.logger)
		)

	def test_description_contains_case_insensitive(self):
		txn = make_transaction(description="Monthly PAYROLL Run")
		self.assertTrue(
			evaluate_condition(txn, make_condition("Description", "Contains", "payroll"), self.logger)
		)

	def test_description_contains_no_match(self):
		txn = make_transaction(description="Monthly PAYROLL Run")
		self.assertFalse(
			evaluate_condition(txn, make_condition("Description", "Contains", "INVOICE"), self.logger)
		)

	def test_description_not_contains_match(self):
		txn = make_transaction(description="Monthly PAYROLL Run")
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Description", "Not Contains", "REFUND"), self.logger
			)
		)

	def test_description_not_contains_no_match(self):
		txn = make_transaction(description="Monthly PAYROLL Run")
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Description", "Not Contains", "PAYROLL"), self.logger
			)
		)

	def test_text_equals_case_insensitive(self):
		txn = make_transaction(description="payroll")
		self.assertTrue(
			evaluate_condition(txn, make_condition("Description", "Equals", "PAYROLL"), self.logger)
		)

	def test_text_not_equals_same_value(self):
		txn = make_transaction(description="PAYROLL")
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Description", "Not Equals", "PAYROLL"), self.logger
			)
		)

	def test_reference_number_equals(self):
		txn = make_transaction(reference_number="12345")
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Reference Number", "Equals", "12345"), self.logger
			)
		)

	# --- Custom fields ---

	def test_particulars_contains(self):
		txn = make_transaction(custom_particulars="City Impact Church")
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Particulars", "Contains", "City Impact"), self.logger
			)
		)

	def test_code_equals(self):
		txn = make_transaction(custom_code="TFR")
		self.assertTrue(
			evaluate_condition(txn, make_condition("Code", "Equals", "TFR"), self.logger)
		)

	def test_party_name_contains(self):
		txn = make_transaction(bank_party_name="ACME Corp Ltd")
		self.assertTrue(
			evaluate_condition(
				txn, make_condition("Other Party", "Contains", "ACME"), self.logger
			)
		)

	# --- Edge cases ---

	def test_contains_on_none_field_returns_false(self):
		txn = make_transaction(description=None)
		self.assertFalse(
			evaluate_condition(txn, make_condition("Description", "Contains", "test"), self.logger)
		)

	def test_not_contains_on_none_field_returns_false(self):
		txn = make_transaction(description=None)
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Description", "Not Contains", "test"), self.logger
			)
		)

	def test_deposit_equals_zero(self):
		txn = make_transaction(deposit=0)
		self.assertTrue(
			evaluate_condition(txn, make_condition("Deposit", "Equals", "0"), self.logger)
		)

	def test_unknown_field_returns_false(self):
		txn = make_transaction()
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Nonexistent Field", "Equals", "x"), self.logger
			)
		)

	def test_unknown_operator_returns_false(self):
		txn = make_transaction(description="test")
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Description", "Starts With", "test"), self.logger
			)
		)

	def test_deposit_less_than_boundary(self):
		txn = make_transaction(deposit=100)
		self.assertFalse(
			evaluate_condition(txn, make_condition("Deposit", "Less Than", "100"), self.logger)
		)

	def test_currency_equals_match(self):
		txn = make_transaction(currency="NZD")
		self.assertTrue(
			evaluate_condition(txn, make_condition("Currency", "Equals", "NZD"), self.logger)
		)

	def test_currency_equals_no_match(self):
		txn = make_transaction(currency="NZD")
		self.assertFalse(
			evaluate_condition(txn, make_condition("Currency", "Equals", "USD"), self.logger)
		)

	def test_not_contains_on_empty_string_returns_false(self):
		txn = make_transaction(description="")
		self.assertFalse(
			evaluate_condition(
				txn, make_condition("Description", "Not Contains", "test"), self.logger
			)
		)


# ============================================================================
# Group 3: Conditions Match (AND/OR logic, pure unit tests)
# ============================================================================


class TestConditionsMatch(FrappeTestCase):
	"""Test _conditions_match() AND/OR logic with mock objects."""

	def setUp(self):
		self.logger = get_test_logger()
		self.txn = make_transaction(deposit=100, description="Monthly PAYROLL Run")

	def test_and_logic_all_match(self):
		rule = make_mock_rule(
			[
				make_condition("Deposit", "Equals", "100"),
				make_condition("Description", "Contains", "PAYROLL"),
			],
			match_any=False,
		)
		self.assertTrue(_conditions_match(self.txn, rule, self.logger))

	def test_and_logic_one_fails(self):
		rule = make_mock_rule(
			[
				make_condition("Deposit", "Equals", "100"),
				make_condition("Description", "Contains", "INVOICE"),
			],
			match_any=False,
		)
		self.assertFalse(_conditions_match(self.txn, rule, self.logger))

	def test_or_logic_first_matches(self):
		rule = make_mock_rule(
			[
				make_condition("Deposit", "Equals", "100"),
				make_condition("Description", "Contains", "INVOICE"),
			],
			match_any=True,
		)
		self.assertTrue(_conditions_match(self.txn, rule, self.logger))

	def test_or_logic_second_matches(self):
		rule = make_mock_rule(
			[
				make_condition("Deposit", "Equals", "999"),
				make_condition("Description", "Contains", "PAYROLL"),
			],
			match_any=True,
		)
		self.assertTrue(_conditions_match(self.txn, rule, self.logger))

	def test_or_logic_none_match(self):
		rule = make_mock_rule(
			[
				make_condition("Deposit", "Equals", "999"),
				make_condition("Description", "Contains", "INVOICE"),
			],
			match_any=True,
		)
		self.assertFalse(_conditions_match(self.txn, rule, self.logger))

	def test_empty_conditions_returns_false(self):
		rule = make_mock_rule([], match_any=False)
		self.assertFalse(_conditions_match(self.txn, rule, self.logger))


# ============================================================================
# Group 4: Rule Priority and Selection (real DB rules, mock transactions)
# ============================================================================


class TestRulePriority(FrappeTestCase):
	"""Test _load_rules() ordering and _match_transaction() first-match-wins."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_test_bank_account()
		cleanup_test_rules(cls.bank_account)
		frappe.db.commit()

	def setUp(self):
		self.logger = get_test_logger()

	def tearDown(self):
		frappe.db.rollback()

	def _create_rule(self, title, priority, conditions, enabled=1):
		return frappe.get_doc(
			{
				"doctype": "ABR Bank Rule",
				"title": title,
				"enabled": enabled,
				"priority": priority,
				"company": TEST_COMPANY,
				"bank_account": self.bank_account,
				"entry_type": "Journal Entry",
				"account": f"Sales - {TEST_COMPANY_ABBR}",
				"conditions": conditions,
			}
		).insert()

	def test_higher_priority_rule_wins(self):
		self._create_rule(
			"High Priority",
			1,
			[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
		)
		self._create_rule(
			"Low Priority",
			10,
			[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
		)

		txn = make_transaction(deposit=100, description="Monthly PAYROLL Run")
		rules = _load_rules(self.bank_account)
		matched = _match_transaction(txn, rules, self.logger)

		self.assertIsNotNone(matched)
		self.assertEqual(matched.title, "High Priority")

	def test_fallback_to_lower_priority(self):
		self._create_rule(
			"High - No Match",
			1,
			[{"field_name": "Description", "condition": "Contains", "value": "INVOICE"}],
		)
		self._create_rule(
			"Low - Match",
			10,
			[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
		)

		txn = make_transaction(deposit=100, description="Monthly PAYROLL Run")
		rules = _load_rules(self.bank_account)
		matched = _match_transaction(txn, rules, self.logger)

		self.assertIsNotNone(matched)
		self.assertEqual(matched.title, "Low - Match")

	def test_no_matching_rule_returns_none(self):
		self._create_rule(
			"No Match",
			10,
			[{"field_name": "Description", "condition": "Contains", "value": "INVOICE"}],
		)

		txn = make_transaction(deposit=100, description="Monthly PAYROLL Run")
		rules = _load_rules(self.bank_account)
		matched = _match_transaction(txn, rules, self.logger)

		self.assertIsNone(matched)

	def test_disabled_rules_excluded(self):
		self._create_rule(
			"Disabled Rule",
			1,
			[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
			enabled=0,
		)

		rules = _load_rules(self.bank_account)
		self.assertEqual(len(rules), 0)


# ============================================================================
# Group 5: Integration - run_bank_rules (real txns + rules, mocked actions)
# ============================================================================


class TestRunBankRules(FrappeTestCase):
	"""Integration tests for run_bank_rules with mocked action execution.

	We mock _execute_rule_action to avoid creating real JE/PE (and the complex
	cleanup that entails). We also mock frappe.db.commit and frappe.db.rollback
	so test data stays in the uncommitted transaction buffer and tearDown's
	rollback cleans everything up.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_test_bank_account()
		cleanup_test_rules(cls.bank_account)
		cleanup_test_bank_transactions(cls.bank_account)
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()

	def _create_bt(self, **kwargs):
		defaults = {
			"doctype": "Bank Transaction",
			"date": today(),
			"bank_account": self.bank_account,
			"company": TEST_COMPANY,
			"currency": "INR",
		}
		defaults.update(kwargs)
		bt = frappe.get_doc(defaults)
		bt.insert()
		bt.submit()
		return bt

	def _create_rule(self, **kwargs):
		defaults = {
			"doctype": "ABR Bank Rule",
			"title": "Integration Test Rule",
			"enabled": 1,
			"priority": 10,
			"company": TEST_COMPANY,
			"bank_account": self.bank_account,
			"entry_type": "Journal Entry",
			"account": f"Sales - {TEST_COMPANY_ABBR}",
		}
		defaults.update(kwargs)
		return frappe.get_doc(defaults).insert()

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_matching_rule_increments_matched_count(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="PAYROLL monthly")
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["matched"], 1)
		self.assertEqual(result["unmatched"], 0)
		self.assertEqual(result["errors"], 0)
		mock_execute.assert_called_once()

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_non_matching_increments_unmatched(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="Random Transfer")
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["matched"], 0)
		self.assertEqual(result["unmatched"], 1)
		mock_execute.assert_not_called()

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_mixed_matched_and_unmatched(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="PAYROLL monthly")
		self._create_bt(deposit=200, description="Random Transfer")
		self._create_bt(withdrawal=100, description="PAYROLL advance")
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["matched"], 2)
		self.assertEqual(result["unmatched"], 1)

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_je_rule_dispatches_with_correct_args(self, _rb, _commit, mock_execute):
		bt = self._create_bt(deposit=500, description="PAYROLL monthly")
		expense_account = f"Sales - {TEST_COMPANY_ABBR}"
		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")

		self._create_rule(
			entry_type="Journal Entry",
			account=expense_account,
			cost_center=cost_center,
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
		)

		run_bank_rules(self.bank_account, add_days(today(), -1), today())

		mock_execute.assert_called_once()
		transaction_arg, rule_arg, _logger_arg = mock_execute.call_args[0]
		self.assertEqual(transaction_arg.name, bt.name)
		self.assertEqual(rule_arg.entry_type, "Journal Entry")
		self.assertEqual(rule_arg.account, expense_account)
		self.assertEqual(rule_arg.cost_center, cost_center)

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_pe_rule_dispatches_with_party_info(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="Customer Payment")
		self._create_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
			conditions=[
				{"field_name": "Description", "condition": "Contains", "value": "Customer Payment"}
			],
		)

		run_bank_rules(self.bank_account, add_days(today(), -1), today())

		mock_execute.assert_called_once()
		rule_arg = mock_execute.call_args[0][1]
		self.assertEqual(rule_arg.entry_type, "Payment Entry")
		self.assertEqual(rule_arg.party_type, "Customer")
		self.assertEqual(rule_arg.party, "_Test Customer")

	@patch(f"{ABR_MODULE}._execute_rule_action", side_effect=Exception("Simulated error"))
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_error_in_action_increments_error_count(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="PAYROLL monthly")
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["matched"], 0)
		self.assertEqual(result["errors"], 1)

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_error_on_one_txn_does_not_block_others(self, _rb, _commit, mock_execute):
		self._create_bt(deposit=500, description="PAYROLL first")
		self._create_bt(deposit=300, description="PAYROLL second")
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)
		mock_execute.side_effect = [Exception("Simulated error"), None]

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["errors"], 1)
		self.assertEqual(result["matched"], 1)
		self.assertEqual(mock_execute.call_count, 2)

	@patch(f"{ABR_MODULE}._execute_rule_action")
	@patch(f"{ABR_MODULE}.get_bank_transactions")
	@patch("frappe.db.commit")
	@patch("frappe.db.rollback")
	def test_already_reconciled_txn_is_skipped(self, _rb, _commit, mock_get_txns, mock_execute):
		bt = self._create_bt(deposit=500, description="PAYROLL monthly")
		# Set unallocated_amount to 0, but force get_bank_transactions to still return it
		# (simulates a race condition where txn was reconciled after the query)
		frappe.db.set_value("Bank Transaction", bt.name, "unallocated_amount", 0)
		mock_get_txns.return_value = [frappe._dict(name=bt.name)]
		self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)

		result = run_bank_rules(self.bank_account, add_days(today(), -1), today())

		self.assertEqual(result["matched"], 0)
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(result["unmatched"], 0)
		mock_execute.assert_not_called()

	def test_run_bank_rules_without_bank_account_throws(self):
		with self.assertRaises(frappe.ValidationError):
			run_bank_rules("", add_days(today(), -1), today())

	def test_run_bank_rules_without_dates_throws(self):
		with self.assertRaises(frappe.ValidationError):
			run_bank_rules(self.bank_account, None, None)


# ============================================================================
# Group 6: End-to-End (real JE/PE creation, no mocks)
# ============================================================================


def cleanup_bank_rule_test(bt_name, rule_name):
	"""Unreconcile bank transaction, cancel/delete linked vouchers, then delete BT and rule."""
	bt = frappe.get_doc("Bank Transaction", bt_name)
	voucher_links = [(pe.payment_document, pe.payment_entry) for pe in bt.payment_entries]

	if bt.payment_entries:
		bt.remove_payment_entries()

	for doctype, docname in voucher_links:
		voucher = frappe.get_doc(doctype, docname)
		if voucher.docstatus == 1:
			voucher.cancel()
		frappe.delete_doc(doctype, docname, force=True)

	bt.reload()
	if bt.docstatus == 1:
		bt.cancel()
	frappe.delete_doc("Bank Transaction", bt_name, force=True)

	if rule_name and frappe.db.exists("ABR Bank Rule", rule_name):
		frappe.delete_doc("ABR Bank Rule", rule_name, force=True)

	frappe.db.commit()


class TestRunBankRulesEndToEnd(FrappeTestCase):
	"""End-to-end tests that create real JE/PE without mocking."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_test_bank_account()
		cleanup_test_rules(cls.bank_account)
		cleanup_test_bank_transactions(cls.bank_account)
		frappe.db.commit()

	def _create_bt(self, **kwargs):
		defaults = {
			"doctype": "Bank Transaction",
			"date": today(),
			"bank_account": self.bank_account,
			"company": TEST_COMPANY,
			"currency": "INR",
		}
		defaults.update(kwargs)
		bt = frappe.get_doc(defaults)
		bt.insert()
		bt.submit()
		return bt

	def _create_rule(self, **kwargs):
		defaults = {
			"doctype": "ABR Bank Rule",
			"title": "E2E Test Rule",
			"enabled": 1,
			"priority": 10,
			"company": TEST_COMPANY,
			"bank_account": self.bank_account,
			"entry_type": "Journal Entry",
			"account": f"Sales - {TEST_COMPANY_ABBR}",
		}
		defaults.update(kwargs)
		return frappe.get_doc(defaults).insert()

	def test_je_rule_creates_journal_entry_and_reconciles(self):
		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")
		bt = self._create_bt(deposit=500, description="PAYROLL monthly", reference_number="JE-REF-001")
		rule = self._create_rule(
			entry_type="Journal Entry",
			account=f"Sales - {TEST_COMPANY_ABBR}",
			cost_center=cost_center,
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			self.assertEqual(bt.unallocated_amount, 0)
			self.assertTrue(len(bt.payment_entries) > 0)

			je_link = bt.payment_entries[0]
			self.assertEqual(je_link.payment_document, "Journal Entry")

			je = frappe.get_doc("Journal Entry", je_link.payment_entry)
			self.assertEqual(je.docstatus, 1)

			# Verify amounts and direction
			bank_gl = f"_Test Bank - {TEST_COMPANY_ABBR}"
			bank_row = next((row for row in je.accounts if row.account == bank_gl), None)
			second_row = next(
				(row for row in je.accounts if row.account == f"Sales - {TEST_COMPANY_ABBR}"), None
			)
			self.assertIsNotNone(bank_row)
			self.assertIsNotNone(second_row)
			self.assertEqual(bank_row.debit_in_account_currency, 500)
			self.assertEqual(second_row.credit_in_account_currency, 500)
			self.assertEqual(second_row.cost_center, cost_center)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_pe_rule_creates_payment_entry_and_reconciles(self):
		bt = self._create_bt(deposit=300, description="Customer Payment Received", reference_number="PE-REF-001")
		rule = self._create_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
			conditions=[
				{"field_name": "Description", "condition": "Contains", "value": "Customer Payment"}
			],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			self.assertEqual(bt.unallocated_amount, 0)
			self.assertTrue(len(bt.payment_entries) > 0)

			pe_link = bt.payment_entries[0]
			self.assertEqual(pe_link.payment_document, "Payment Entry")

			pe = frappe.get_doc("Payment Entry", pe_link.payment_entry)
			self.assertEqual(pe.docstatus, 1)
			self.assertEqual(pe.party_type, "Customer")
			self.assertEqual(pe.party, "_Test Customer")
			self.assertEqual(pe.payment_type, "Receive")
			self.assertEqual(pe.paid_amount, 300)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_je_rule_withdrawal_creates_correct_direction(self):
		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")
		bt = self._create_bt(
			withdrawal=200, description="Office supplies", reference_number="WD-REF-001"
		)
		rule = self._create_rule(
			entry_type="Journal Entry",
			account=f"Sales - {TEST_COMPANY_ABBR}",
			cost_center=cost_center,
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "Office"}],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			self.assertEqual(bt.unallocated_amount, 0)

			je = frappe.get_doc("Journal Entry", bt.payment_entries[0].payment_entry)
			self.assertEqual(je.docstatus, 1)

			bank_gl = f"_Test Bank - {TEST_COMPANY_ABBR}"
			bank_row = next((row for row in je.accounts if row.account == bank_gl), None)
			second_row = next(
				(row for row in je.accounts if row.account == f"Sales - {TEST_COMPANY_ABBR}"), None
			)
			self.assertIsNotNone(bank_row)
			self.assertIsNotNone(second_row)
			self.assertEqual(bank_row.credit_in_account_currency, 200)
			self.assertEqual(second_row.debit_in_account_currency, 200)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_running_rules_twice_does_not_double_process(self):
		bt = self._create_bt(
			deposit=500, description="PAYROLL monthly", reference_number="IDEM-001"
		)
		rule = self._create_rule(
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL"}]
		)
		frappe.db.commit()

		try:
			result1 = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result1["matched"], 1)

			result2 = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result2["matched"], 0)
			self.assertEqual(result2["unmatched"], 0)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_je_rule_with_party_on_receivable_account_uses_party_fields(self):
		"""Party on Receivable account should use standard party_type/party, not reference fields."""
		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")
		debtors_account = f"Debtors - {TEST_COMPANY_ABBR}"
		bt = self._create_bt(deposit=400, description="Customer invoice payment", reference_number="RCV-001")
		rule = self._create_rule(
			entry_type="Journal Entry",
			account=debtors_account,
			party_type="Customer",
			party="_Test Customer",
			cost_center=cost_center,
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "invoice payment"}],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			self.assertEqual(bt.unallocated_amount, 0)

			je = frappe.get_doc("Journal Entry", bt.payment_entries[0].payment_entry)
			self.assertEqual(je.docstatus, 1)

			second_row = next(
				(row for row in je.accounts if row.account == debtors_account), None
			)
			self.assertIsNotNone(second_row)
			self.assertEqual(second_row.party_type, "Customer")
			self.assertEqual(second_row.party, "_Test Customer")
			self.assertFalse(second_row.reference_type)
			self.assertFalse(second_row.reference_name)
			self.assertEqual(second_row.credit_in_account_currency, 400)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_je_rule_with_party_on_income_account_stores_as_reference(self):
		"""Party on non-Receivable/Payable account should be stored as reference_type/reference_name."""
		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")
		bt = self._create_bt(deposit=250, description="Donation from member", reference_number="DON-001")
		rule = self._create_rule(
			entry_type="Journal Entry",
			account=f"Sales - {TEST_COMPANY_ABBR}",
			party_type="Customer",
			party="_Test Customer",
			cost_center=cost_center,
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "Donation"}],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			self.assertEqual(bt.unallocated_amount, 0)
			self.assertTrue(len(bt.payment_entries) > 0)

			je = frappe.get_doc("Journal Entry", bt.payment_entries[0].payment_entry)
			self.assertEqual(je.docstatus, 1)

			# Verify the second account row does NOT have party set (Income account)
			second_row = next(
				(row for row in je.accounts if row.account == f"Sales - {TEST_COMPANY_ABBR}"), None
			)
			self.assertIsNotNone(second_row)
			self.assertFalse(second_row.party_type)
			self.assertFalse(second_row.party)
			# Party should be stored as reference instead
			self.assertEqual(second_row.reference_type, "Customer")
			self.assertEqual(second_row.reference_name, "_Test Customer")
			self.assertEqual(second_row.credit_in_account_currency, 250)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_je_rule_stamps_abr_bank_rule_on_journal_entry(self):
		"""Created JE should have abr_bank_rule set to the rule name."""
		bt = self._create_bt(deposit=150, description="PAYROLL stamp test", reference_number="STAMP-JE-001")
		rule = self._create_rule(
			entry_type="Journal Entry",
			account=f"Sales - {TEST_COMPANY_ABBR}",
			conditions=[{"field_name": "Description", "condition": "Contains", "value": "PAYROLL stamp"}],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			je = frappe.get_doc("Journal Entry", bt.payment_entries[0].payment_entry)
			self.assertEqual(je.abr_bank_rule, rule.name)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)

	def test_pe_rule_stamps_abr_bank_rule_on_payment_entry(self):
		"""Created PE should have abr_bank_rule set to the rule name."""
		bt = self._create_bt(deposit=175, description="Customer Payment stamp", reference_number="STAMP-PE-001")
		rule = self._create_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
			conditions=[
				{"field_name": "Description", "condition": "Contains", "value": "Customer Payment stamp"}
			],
		)
		frappe.db.commit()

		try:
			result = run_bank_rules(self.bank_account, add_days(today(), -1), today())
			self.assertEqual(result["matched"], 1)
			self.assertEqual(result["errors"], 0)

			bt.reload()
			pe = frappe.get_doc("Payment Entry", bt.payment_entries[0].payment_entry)
			self.assertEqual(pe.abr_bank_rule, rule.name)
		finally:
			cleanup_bank_rule_test(bt.name, rule.name)


# ============================================================================
# Group 7: _sanitize_dimensions (unit tests, mocked dimensions)
# ============================================================================

DIMENSIONS_IMPORT_PATH = (
	"erpnext.accounts.doctype.accounting_dimension"
	".accounting_dimension.get_accounting_dimensions"
)


class TestSanitizeDimensions(FrappeTestCase):
	"""Test _sanitize_dimensions() with mocked get_accounting_dimensions."""

	def test_returns_none_for_none_input(self):
		self.assertIsNone(_sanitize_dimensions(None))

	def test_returns_none_for_empty_dict(self):
		self.assertIsNone(_sanitize_dimensions({}))

	@patch(DIMENSIONS_IMPORT_PATH, return_value=["location"])
	def test_filters_to_valid_dimensions_only(self, _mock):
		result = _sanitize_dimensions({"location": "AK", "bogus": "val"})
		self.assertEqual(result, {"location": "AK"})

	@patch(DIMENSIONS_IMPORT_PATH, return_value=["location"])
	def test_returns_empty_dict_when_all_invalid(self, _mock):
		result = _sanitize_dimensions({"bogus": "val"})
		self.assertEqual(result, {})

	@patch(DIMENSIONS_IMPORT_PATH, return_value=["location"])
	def test_handles_string_input(self, _mock):
		result = _sanitize_dimensions('{"location": "AK"}')
		self.assertEqual(result, {"location": "AK"})

	def test_returns_none_for_non_dict_input(self):
		self.assertIsNone(_sanitize_dimensions([1, 2]))

	@patch(DIMENSIONS_IMPORT_PATH, side_effect=ImportError("mocked"))
	def test_returns_none_on_import_error(self, _mock):
		self.assertIsNone(_sanitize_dimensions({"location": "AK"}))


# ============================================================================
# Group 8: on_trash cleanup (integration, real DB)
# ============================================================================


class TestOnTrashCleanup(FrappeTestCase):
	"""Test ABRBankRule.on_trash clears abr_bank_rule on linked JE/PE."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_test_bank_account()

	def _create_rule(self, title="Trash Test Rule", **kwargs):
		defaults = {
			"doctype": "ABR Bank Rule",
			"title": title,
			"enabled": 1,
			"priority": 10,
			"company": TEST_COMPANY,
			"bank_account": self.bank_account,
			"entry_type": "Journal Entry",
			"account": f"Sales - {TEST_COMPANY_ABBR}",
			"conditions": [
				{"field_name": "Description", "condition": "Contains", "value": "trash-test"}
			],
		}
		defaults.update(kwargs)
		return frappe.get_doc(defaults).insert()

	def test_on_trash_clears_je_reference(self):
		rule = self._create_rule()
		frappe.db.commit()

		cost_center = frappe.db.get_value("Company", TEST_COMPANY, "cost_center")
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": TEST_COMPANY,
			"posting_date": today(),
			"accounts": [
				{
					"account": f"_Test Bank - {TEST_COMPANY_ABBR}",
					"debit_in_account_currency": 100,
					"cost_center": cost_center,
				},
				{
					"account": f"Sales - {TEST_COMPANY_ABBR}",
					"credit_in_account_currency": 100,
					"cost_center": cost_center,
				},
			],
			"abr_bank_rule": rule.name,
		})
		je.insert()
		frappe.db.commit()

		try:
			frappe.delete_doc("ABR Bank Rule", rule.name, force=True)
			frappe.db.commit()

			je.reload()
			self.assertFalse(je.abr_bank_rule)
		finally:
			if frappe.db.exists("Journal Entry", je.name):
				je_doc = frappe.get_doc("Journal Entry", je.name)
				if je_doc.docstatus == 1:
					je_doc.cancel()
				frappe.delete_doc("Journal Entry", je.name, force=True)
			if frappe.db.exists("ABR Bank Rule", rule.name):
				frappe.delete_doc("ABR Bank Rule", rule.name, force=True)
			frappe.db.commit()

	def test_on_trash_clears_pe_reference(self):
		rule = self._create_rule(
			entry_type="Payment Entry",
			account="",
			party_type="Customer",
			party="_Test Customer",
		)
		frappe.db.commit()

		pe = frappe.get_doc({
			"doctype": "Payment Entry",
			"company": TEST_COMPANY,
			"posting_date": today(),
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": "_Test Customer",
			"paid_from": f"Debtors - {TEST_COMPANY_ABBR}",
			"paid_to": f"_Test Bank - {TEST_COMPANY_ABBR}",
			"paid_amount": 100,
			"received_amount": 100,
			"reference_no": "TRASH-PE-001",
			"reference_date": today(),
			"abr_bank_rule": rule.name,
		})
		pe.insert()
		frappe.db.commit()

		try:
			frappe.delete_doc("ABR Bank Rule", rule.name, force=True)
			frappe.db.commit()

			pe.reload()
			self.assertFalse(pe.abr_bank_rule)
		finally:
			if frappe.db.exists("Payment Entry", pe.name):
				pe_doc = frappe.get_doc("Payment Entry", pe.name)
				if pe_doc.docstatus == 1:
					pe_doc.cancel()
				frappe.delete_doc("Payment Entry", pe.name, force=True)
			if frappe.db.exists("ABR Bank Rule", rule.name):
				frappe.delete_doc("ABR Bank Rule", rule.name, force=True)
			frappe.db.commit()

	def test_on_trash_no_error_when_no_linked_docs(self):
		rule = self._create_rule(title="Orphan Rule")
		frappe.db.commit()

		try:
			frappe.delete_doc("ABR Bank Rule", rule.name, force=True)
			frappe.db.commit()
		except Exception:
			self.fail("on_trash raised an error when no linked JE/PE exist")
