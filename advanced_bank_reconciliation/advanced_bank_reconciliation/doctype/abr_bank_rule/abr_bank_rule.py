# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt

import operator as op

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import (
	create_journal_entry_bts,
	create_payment_entry_bts,
	get_bank_transactions,
)
from advanced_bank_reconciliation.utils.logger import get_logger


class ABRBankRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule_condition.abr_bank_rule_condition import (
			ABRBankRuleCondition,
		)

		account: DF.Link | None
		bank_account: DF.Link
		company: DF.Link
		conditions: DF.Table[ABRBankRuleCondition]
		cost_center: DF.Link | None
		enabled: DF.Check
		entry_type: DF.Literal["", "Journal Entry", "Payment Entry"]
		match_any_condition: DF.Check
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		priority: DF.Int
		title: DF.Data
	# end: auto-generated types

	NUMERIC_ONLY_OPERATORS = {"Greater than", "Greater than or Equals", "Less Than", "Less Than or Equals"}
	TEXT_ONLY_OPERATORS = {"Contains", "Not Contains"}
	NUMERIC_FIELDS = {"Deposit", "Withdrawal"}
	VALID_OPERATORS = {
		"Equals", "Not Equals", "Greater than", "Greater than or Equals",
		"Less Than", "Less Than or Equals", "Contains", "Not Contains",
	}

	def validate(self):
		if not self.conditions:
			frappe.throw("At least one condition is required")
		if not self.entry_type:
			frappe.throw("Entry Type is required")
		if self.entry_type == "Journal Entry" and not self.account:
			frappe.throw("Account is required for Journal Entry rules")
		if self.entry_type == "Payment Entry":
			if not self.party_type:
				frappe.throw("Party Type is required for Payment Entry rules")
			if not self.party:
				frappe.throw("Party is required for Payment Entry rules")

		self._validate_bank_account_company()
		self._validate_conditions()

	def _validate_bank_account_company(self):
		if self.bank_account and self.company:
			ba_company = frappe.db.get_value("Bank Account", self.bank_account, "company")
			if ba_company and ba_company != self.company:
				frappe.throw(
					"Bank Account '%s' belongs to company '%s', not '%s'"
					% (self.bank_account, ba_company, self.company)
				)

	def _validate_conditions(self):
		for cond in self.conditions:
			if not cond.value:
				frappe.throw("Value is required for condition on field '%s'" % cond.field_name)
			if cond.field_name not in CONDITION_FIELD_MAP:
				frappe.throw("Unknown condition field '%s'" % cond.field_name)
			if cond.condition not in self.VALID_OPERATORS:
				frappe.throw("Unknown operator '%s'" % cond.condition)
			if cond.condition in self.NUMERIC_ONLY_OPERATORS and cond.field_name not in self.NUMERIC_FIELDS:
				frappe.throw(
					"Operator '%s' is only valid for numeric fields (Deposit, Withdrawal), not '%s'"
					% (cond.condition, cond.field_name)
				)
			if cond.condition in self.TEXT_ONLY_OPERATORS and cond.field_name in self.NUMERIC_FIELDS:
				frappe.throw(
					"Operator '%s' is not valid for numeric fields, not '%s'"
					% (cond.condition, cond.field_name)
				)


# --- Field name to Bank Transaction fieldname mapping ---

CONDITION_FIELD_MAP = {
	"Deposit": ("deposit", True),
	"Withdrawal": ("withdrawal", True),
	"Currency": ("currency", False),
	"Description": ("description", False),
	"Reference Number": ("reference_number", False),
	"Particulars": ("custom_particulars", False),
	"Party Name": ("bank_party_name", False),
	"Code": ("custom_code", False),
}
"""Maps condition field label -> (transaction_fieldname, is_numeric)"""


# --- Rule engine ---


@frappe.whitelist()
def run_bank_rules(bank_account, from_date, to_date):
	"""Run all enabled ABR Bank Rules against unreconciled bank transactions."""
	frappe.has_permission("ABR Bank Rule", throw=True)
	logger = get_logger()

	if not bank_account or not from_date or not to_date:
		frappe.throw("Bank account, from date and to date are required")

	transactions = get_bank_transactions(bank_account, from_date, to_date)
	rules = _load_rules(bank_account)

	logger.info(
		"Running %s rules against %s transactions for bank account '%s'",
		len(rules),
		len(transactions),
		bank_account,
	)

	matched_count = 0
	unmatched_count = 0
	error_count = 0
	skipped_count = 0

	for txn_summary in transactions:
		matched_rule = None
		try:
			transaction = frappe.get_doc("Bank Transaction", txn_summary.name)
			if not transaction.unallocated_amount or transaction.unallocated_amount <= 0:
				skipped_count += 1
				continue
			matched_rule = _match_transaction(transaction, rules, logger)
			if matched_rule:
				_execute_rule_action(transaction, matched_rule, logger)
				frappe.db.commit()
				matched_count += 1
			else:
				unmatched_count += 1
		except Exception:
			error_count += 1
			tb = frappe.get_traceback()
			rule_title = matched_rule.title if matched_rule else "N/A"
			logger.error(
				"Error processing transaction '%s' (rule: '%s'): %s",
				txn_summary.name, rule_title, tb,
			)
			frappe.db.rollback()
			try:
				frappe.log_error(
					message="Bank Account: %s\nRule: %s\nTransaction: %s\n\n%s"
					% (bank_account, rule_title, txn_summary.name, tb),
					title="ABR Bank Rule failed for %s" % txn_summary.name,
				)
				frappe.db.commit()
			except Exception:
				logger.error(
					"Failed to persist Error Log for transaction '%s': %s",
					txn_summary.name, frappe.get_traceback(),
				)

	result_msg = "Bank Rules Result: %s matched, %s unmatched, %s skipped, %s errors" % (
		matched_count,
		unmatched_count,
		skipped_count,
		error_count,
	)
	logger.info(
		"Bank Rules Result: %s matched, %s unmatched, %s skipped, %s errors",
		matched_count, unmatched_count, skipped_count, error_count,
	)

	indicator = "orange" if error_count else "green"
	frappe.msgprint(result_msg, indicator=indicator, title="Bank Rules")

	return {
		"matched": matched_count,
		"unmatched": unmatched_count,
		"skipped": skipped_count,
		"errors": error_count,
	}


def _load_rules(bank_account):
	"""Load all enabled rules for the bank account, ordered by priority."""
	rule_names = frappe.get_all(
		"ABR Bank Rule",
		filters={"bank_account": bank_account, "enabled": 1},
		pluck="name",
		order_by="priority asc, creation asc",
	)
	return [frappe.get_doc("ABR Bank Rule", name) for name in rule_names]


def _match_transaction(transaction, rules, logger):
	"""Find the first matching rule for the transaction. Returns the rule or None."""
	for rule in rules:
		if _conditions_match(transaction, rule, logger):
			logger.info("Rule '%s' matched transaction '%s'", rule.title, transaction.name)
			return rule
	return None


def _conditions_match(transaction, rule, logger):
	"""Check if the rule's conditions match the transaction."""
	if not rule.conditions:
		return False
	if rule.match_any_condition:
		return any(evaluate_condition(transaction, cond, logger) for cond in rule.conditions)
	return all(evaluate_condition(transaction, cond, logger) for cond in rule.conditions)


def _execute_rule_action(transaction, rule, logger):
	"""Create a JE or PE based on the rule's action configuration."""
	if rule.entry_type == "Journal Entry":
		create_journal_entry_bts(
			transaction.name,
			transaction.reference_number,
			transaction.date,
			transaction.date,
			entry_type="Journal Entry",
			second_account=rule.account,
			party_type=rule.party_type,
			party=rule.party,
			cost_center=rule.cost_center,
		)
	elif rule.entry_type == "Payment Entry":
		create_payment_entry_bts(
			transaction.name,
			transaction.reference_number,
			transaction.date,
			party_type=rule.party_type,
			party=rule.party,
			posting_date=transaction.date,
			cost_center=rule.cost_center,
		)
	else:
		frappe.throw("Unsupported entry type '%s' in rule '%s'" % (rule.entry_type, rule.title))

	logger.info(
		"Created %s for transaction '%s' via rule '%s'",
		rule.entry_type,
		transaction.name,
		rule.title,
	)


NUMERIC_OPERATORS = {
	"Equals": op.eq,
	"Not Equals": op.ne,
	"Greater than": op.gt,
	"Greater than or Equals": op.ge,
	"Less Than": op.lt,
	"Less Than or Equals": op.le,
}


def evaluate_condition(transaction, condition, logger):
	"""Evaluate a single condition against a bank transaction."""
	field_info = CONDITION_FIELD_MAP.get(condition.field_name)
	if not field_info:
		logger.error("Unknown condition field '%s'", condition.field_name)
		return False

	fieldname, is_numeric = field_info
	field_value = transaction.get(fieldname)
	condition_value = condition.value
	operator = condition.condition

	logger.info(
		"Evaluating: field='%s' (%s) value='%s' op='%s' test='%s'",
		condition.field_name,
		fieldname,
		field_value,
		operator,
		condition_value,
	)

	numeric_op = NUMERIC_OPERATORS.get(operator)
	if numeric_op:
		if is_numeric or operator not in ("Equals", "Not Equals"):
			return numeric_op(flt(field_value), flt(condition_value))
		return numeric_op(str(field_value or "").lower(), str(condition_value or "").lower())

	if operator == "Contains":
		return bool(field_value) and condition_value.lower() in str(field_value).lower()
	if operator == "Not Contains":
		if not field_value:
			return False
		return condition_value.lower() not in str(field_value).lower()

	logger.error("Unknown operator '%s'", operator)
	return False
