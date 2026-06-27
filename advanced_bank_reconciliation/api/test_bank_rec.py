from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from advanced_bank_reconciliation.api.bank_rec import (
	get_bank_accounts,
	get_bank_rules,
	get_boot,
	get_statement_summary,
	get_transaction_context,
	get_transactions,
)
from advanced_bank_reconciliation.api.matching import (
	get_match_candidates,
	submit_match,
	update_transaction_metadata,
)
from advanced_bank_reconciliation.api.create_voucher import (
	create_voucher_draft_from_transaction,
	create_voucher_from_transaction,
	get_create_defaults,
)
from advanced_bank_reconciliation.api.cash_coding import (
	get_cash_coding_rows,
	preview_cash_coding,
	submit_cash_coding,
)
from advanced_bank_reconciliation.api.matched import (
	get_matched_transactions,
	unreconcile_transaction,
)
from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.tests.fixtures import (
	TEST_COMPANY,
	TEST_COMPANY_2,
	TEST_CUSTOMER,
	create_test_bank_transaction,
	create_test_sales_invoice,
	ensure_bank_account_for_company,
	setup_abr_test_data,
)


def _clear_user_permission_cache(user):
	frappe.cache.hdel("user_permissions", user)


def _ensure_test_user(email, roles):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)

	allowed_roles = set(roles).union({"All", "Desk User"})
	user.roles = [row for row in user.roles if row.role in allowed_roles]
	for role in roles:
		if not any(row.role == role for row in user.roles):
			user.append("roles", {"role": role})

	user.save(ignore_permissions=True)
	return email


def _ensure_company_user_permission(user, company):
	for permission in frappe.get_all(
		"User Permission",
		filters={
			"user": user,
			"allow": "Company",
			"for_value": ["!=", company],
		},
		pluck="name",
	):
		frappe.delete_doc("User Permission", permission, ignore_permissions=True)

	if not frappe.db.exists(
		"User Permission",
		{
			"user": user,
			"allow": "Company",
			"for_value": company,
		},
	):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
	_clear_user_permission_cache(user)


class TestBankRecPhaseOneAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account_a = setup_abr_test_data(company=TEST_COMPANY)
		cls.bank_account_b = ensure_bank_account_for_company(TEST_COMPANY_2)
		cls.bank_transaction_a = create_test_bank_transaction(
			cls.bank_account_a,
			deposit=100,
			reference_number="_ABR-PHASE1-A",
		)
		cls.bank_transaction_b = create_test_bank_transaction(
			cls.bank_account_b,
			deposit=100,
			reference_number="_ABR-PHASE1-B",
		)
		cls.accounts_user = _ensure_test_user(
			"abr-phase1-accounts@example.com",
			["Accounts User"],
		)
		cls.disallowed_user = _ensure_test_user(
			"abr-phase1-sales@example.com",
			["Sales User"],
		)
		_ensure_company_user_permission(cls.accounts_user, TEST_COMPANY)
		frappe.db.commit()

	def test_guest_cannot_boot_bank_rec(self):
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, get_boot)

	def test_user_without_accounting_role_cannot_boot_bank_rec(self):
		with self.set_user(self.disallowed_user):
			self.assertRaises(frappe.PermissionError, get_boot)

	def test_accounts_user_can_boot_bank_rec(self):
		with self.set_user(self.accounts_user):
			boot = get_boot()

		self.assertEqual(boot["default_route"], "/bank-rec/reconcile")
		self.assertIn("settings", boot)
		self.assertIn("csrf_token", boot)
		self.assertEqual(boot["allowed_companies"], [TEST_COMPANY])

	def test_bank_accounts_are_limited_to_permitted_company(self):
		with self.set_user(self.accounts_user):
			accounts = get_bank_accounts()

		names = {row["name"] for row in accounts}
		self.assertIn(self.bank_account_a, names)
		self.assertNotIn(self.bank_account_b, names)

	def test_bank_accounts_can_be_filtered_by_permitted_company(self):
		with self.set_user(self.accounts_user):
			accounts = get_bank_accounts(company=TEST_COMPANY)

		names = {row["name"] for row in accounts}
		self.assertIn(self.bank_account_a, names)
		self.assertNotIn(self.bank_account_b, names)

	def test_bank_account_filter_rejects_unpermitted_company(self):
		with self.set_user(self.accounts_user):
			self.assertRaises(
				frappe.PermissionError,
				get_bank_accounts,
				company=TEST_COMPANY_2,
			)

	def test_cross_company_bank_account_is_rejected(self):
		with self.set_user(self.accounts_user):
			self.assertRaises(
				frappe.PermissionError,
				get_transactions,
				self.bank_account_b,
			)

	def test_cross_company_bank_transaction_is_rejected(self):
		with self.set_user(self.accounts_user):
			self.assertRaises(
				frappe.PermissionError,
				get_transaction_context,
				self.bank_transaction_b.name,
			)

	def test_statement_summary_does_not_return_difference_without_statement_balance(self):
		with self.set_user(self.accounts_user):
			summary = get_statement_summary(self.bank_account_a)

		self.assertIn("unreconciled_count", summary)
		self.assertIn("cleared_balance", summary)
		self.assertIn("unreconciled_total", summary)
		self.assertNotIn("difference", summary)

	def test_rules_list_is_permission_checked(self):
		rule = frappe.get_doc(
			{
				"doctype": "ABR Bank Rule",
				"title": "_ABR Phase 1 Rule",
				"company": TEST_COMPANY,
				"bank_account": self.bank_account_a,
				"entry_type": "Journal Entry",
				"account": frappe.db.get_value("Bank Account", self.bank_account_a, "account"),
				"conditions": [
					{
						"field_name": "Description",
						"condition": "Contains",
						"value": "Phase 1",
					}
				],
			}
		)
		rule.insert(ignore_permissions=True)

		with self.set_user(self.accounts_user):
			rules = get_bank_rules(self.bank_account_a)
			self.assertTrue(any(row["name"] == rule.name for row in rules))
			self.assertRaises(
				frappe.PermissionError,
				get_bank_rules,
				self.bank_account_b,
			)


class TestBankRecPhaseTwoAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account_a = setup_abr_test_data(company=TEST_COMPANY)
		cls.bank_account_b = ensure_bank_account_for_company(TEST_COMPANY_2)
		cls.accounts_user = _ensure_test_user(
			"abr-phase2-accounts@example.com",
			["Accounts User"],
		)
		_ensure_company_user_permission(cls.accounts_user, TEST_COMPANY)
		frappe.db.commit()

	def _sales_invoice_match_fixture(self, amount=125):
		sales_invoice = create_test_sales_invoice(outstanding=amount)
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			deposit=amount,
			reference_number="_ABR-PHASE2-MATCH",
		)
		return bank_transaction, sales_invoice

	def test_match_candidates_return_unpaid_sales_invoice(self):
		bank_transaction, sales_invoice = self._sales_invoice_match_fixture()

		with self.set_user(self.accounts_user):
			result = get_match_candidates(
				bank_transaction.name,
				document_types=["unpaid_sales_invoice"],
				from_date=add_days(nowdate(), -1),
				to_date=add_days(nowdate(), 1),
			)

		candidates = result["candidates"]
		self.assertTrue(
			any(row["voucher_name"] == sales_invoice.name for row in candidates),
			candidates,
		)
		row = next(row for row in candidates if row["voucher_name"] == sales_invoice.name)
		self.assertEqual(row["voucher_type"], "Sales Invoice")
		self.assertIn(row["confidence"], {"high", "medium", "low"})
		self.assertIn("Amount", row["reasons"])

	def test_submit_match_reconciles_sales_invoice(self):
		bank_transaction, sales_invoice = self._sales_invoice_match_fixture(amount=90)

		result = submit_match(
			bank_transaction.name,
			[
				{
					"voucher_type": "Sales Invoice",
					"voucher_name": sales_invoice.name,
					"amount": 90,
				}
			],
		)

		self.assertEqual(result["status"], "Reconciled")
		bank_transaction.reload()
		self.assertEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 0.0, places=2)
		self.assertTrue(
			any(row.payment_entry == sales_invoice.name for row in bank_transaction.payment_entries)
		)

	def test_submit_match_rejects_negative_allocation_amount(self):
		bank_transaction, sales_invoice = self._sales_invoice_match_fixture(amount=45)

		with self.set_user(self.accounts_user):
			self.assertRaises(
				frappe.ValidationError,
				submit_match,
				bank_transaction.name,
				[
					{
						"voucher_type": "Sales Invoice",
						"voucher_name": sales_invoice.name,
						"amount": -45,
					}
				],
			)

	def test_submit_match_rejects_empty_selection(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			deposit=25,
			reference_number="_ABR-PHASE2-EMPTY",
		)

		with self.assertRaises(frappe.ValidationError):
			submit_match(bank_transaction.name, [])

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 25.0, places=2)
		self.assertFalse(bank_transaction.payment_entries)

	def test_submit_match_rejects_zero_allocation_amount(self):
		bank_transaction, sales_invoice = self._sales_invoice_match_fixture(amount=35)

		with self.assertRaises(frappe.ValidationError):
			submit_match(
				bank_transaction.name,
				[
					{
						"voucher_type": "Sales Invoice",
						"voucher_name": sales_invoice.name,
						"amount": 0,
					}
				],
			)

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 35.0, places=2)
		self.assertFalse(bank_transaction.payment_entries)

	def test_submit_match_rejects_disallowed_voucher_doctype(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			deposit=30,
			reference_number="_ABR-PHASE2-DOCTYPE",
		)

		with self.assertRaises(frappe.PermissionError):
			submit_match(
				bank_transaction.name,
				[
					{
						"voucher_type": "GL Entry",
						"voucher_name": "_ABR-NO-SUCH-GL",
						"amount": 1,
					}
				],
			)

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 30.0, places=2)
		self.assertFalse(bank_transaction.payment_entries)

	def test_submit_match_rejects_over_allocation(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			deposit=100,
			reference_number="_ABR-PHASE2-OVER",
		)
		sales_invoice = create_test_sales_invoice(outstanding=150)

		with self.assertRaises(frappe.ValidationError):
			submit_match(
				bank_transaction.name,
				[
					{
						"voucher_type": "Sales Invoice",
						"voucher_name": sales_invoice.name,
						"amount": 150,
					}
				],
			)

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 100.0, places=2)
		self.assertFalse(bank_transaction.payment_entries)

	def test_duplicate_submit_returns_idempotent_response_for_same_voucher(self):
		bank_transaction, sales_invoice = self._sales_invoice_match_fixture(amount=75)
		vouchers = [
			{
				"voucher_type": "Sales Invoice",
				"voucher_name": sales_invoice.name,
				"amount": 75,
			}
		]

		submit_match(bank_transaction.name, vouchers)
		result = submit_match(bank_transaction.name, vouchers)

		self.assertTrue(result["idempotent"])
		self.assertEqual(result["status"], "Reconciled")

	def test_update_transaction_metadata_rejects_cross_company_transaction(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_b,
			deposit=50,
			reference_number="_ABR-PHASE2-CROSS",
		)

		with self.set_user(self.accounts_user):
			self.assertRaises(
				frappe.PermissionError,
				update_transaction_metadata,
				bank_transaction.name,
				"_ABR-BLOCKED",
			)

	def test_update_transaction_metadata_saves_allowed_fields(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			deposit=60,
			reference_number="_ABR-PHASE2-OLD",
		)

		result = update_transaction_metadata(
			bank_transaction.name,
			"_ABR-PHASE2-NEW",
			"Customer",
			TEST_CUSTOMER,
		)

		bank_transaction.reload()
		self.assertEqual(result["transaction"]["reference_number"], "_ABR-PHASE2-NEW")
		self.assertEqual(bank_transaction.reference_number, "_ABR-PHASE2-NEW")
		self.assertEqual(bank_transaction.party_type, "Customer")
		self.assertEqual(bank_transaction.party, TEST_CUSTOMER)


class TestBankRecMutationGuardsAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account_a = setup_abr_test_data(company=TEST_COMPANY)
		cls.bank_account_b = ensure_bank_account_for_company(TEST_COMPANY_2)
		cls.accounts_user = _ensure_test_user(
			"abr-mutation-accounts@example.com",
			["Accounts User"],
		)
		cls.disallowed_user = _ensure_test_user(
			"abr-mutation-sales@example.com",
			["Sales User"],
		)
		_ensure_company_user_permission(cls.accounts_user, TEST_COMPANY)
		_ensure_company_user_permission(cls.disallowed_user, TEST_COMPANY)
		frappe.db.commit()

	def _ledger_account(self, root_type, company=TEST_COMPANY):
		account = frappe.db.get_value(
			"Account",
			{
				"company": company,
				"root_type": root_type,
				"is_group": 0,
				"disabled": 0,
			},
			"name",
		)
		self.assertTrue(account, "Expected a ledger account for {0} in {1}".format(root_type, company))
		return account

	def _mutation_calls(self, bank_transaction):
		company = frappe.db.get_value("Bank Account", bank_transaction.bank_account, "company")
		account = self._ledger_account("Expense", company=company)
		return {
			"submit_match": lambda: submit_match(
				bank_transaction.name,
				[
					{
						"voucher_type": "Sales Invoice",
						"voucher_name": "_ABR-NO-SUCH-INVOICE",
						"amount": 1,
					}
				],
			),
			"update_transaction_metadata": lambda: update_transaction_metadata(
				bank_transaction.name,
				"_ABR-MUTATION-GUARD",
			),
			"create_voucher_from_transaction": lambda: create_voucher_from_transaction(
				bank_transaction.name,
				{
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-MUTATION-GUARD",
				},
			),
			"create_voucher_draft_from_transaction": lambda: create_voucher_draft_from_transaction(
				bank_transaction.name,
				{
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-MUTATION-GUARD",
				},
			),
			"submit_cash_coding": lambda: submit_cash_coding(
				[
					{
						"bank_transaction_name": bank_transaction.name,
						"account": account,
						"posting_date": nowdate(),
						"reference_date": nowdate(),
						"reference_number": "_ABR-MUTATION-GUARD",
					}
				]
			),
			"unreconcile_transaction": lambda: unreconcile_transaction(
				bank_transaction.name,
				cancel_linked_documents=False,
			),
		}

	def test_mutating_endpoints_reject_guest_and_non_bank_rec_user(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_a,
			withdrawal=11,
			reference_number="_ABR-MUTATION-DENY",
		)

		for user in ("Guest", self.disallowed_user):
			for name, call in self._mutation_calls(bank_transaction).items():
				with self.subTest(user=user, endpoint=name):
					with self.set_user(user):
						self.assertRaises(frappe.PermissionError, call)

	def test_mutating_endpoints_reject_cross_company_transactions(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account_b,
			withdrawal=12,
			reference_number="_ABR-MUTATION-CROSS",
		)

		with self.set_user(self.accounts_user):
			for name, call in self._mutation_calls(bank_transaction).items():
				with self.subTest(endpoint=name):
					if name == "submit_cash_coding":
						result = call()
						self.assertEqual(result["summary"]["success"], 0)
						self.assertEqual(result["summary"]["error"], 1)
						self.assertEqual(result["results"][0]["status"], "error")
						self.assertTrue(result["results"][0]["message"])
					else:
						self.assertRaises(frappe.PermissionError, call)


class TestBankRecPhaseThreeAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(company=TEST_COMPANY)
		frappe.db.commit()

	def _ledger_account(self, root_type):
		account = frappe.db.get_value(
			"Account",
			{
				"company": TEST_COMPANY,
				"root_type": root_type,
				"is_group": 0,
				"disabled": 0,
			},
			"name",
		)
		self.assertTrue(account, "Expected a ledger account for {0}".format(root_type))
		return account

	def test_create_defaults_returns_form_options(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=25,
			reference_number="_ABR-PHASE3-DEFAULTS",
		)

		result = get_create_defaults(bank_transaction.name)

		self.assertEqual(result["transaction"]["name"], bank_transaction.name)
		self.assertTrue(result["options"]["accounts"])
		self.assertIn("posting_date", result["defaults"])

	def test_create_defaults_include_accounting_dimensions(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=27,
			reference_number="_ABR-PHASE3-DIMS",
		)
		dimension_context = {
			"accounting_dimensions": [
				{
					"fieldname": "region",
					"fieldtype": "Link",
					"label": "Region",
					"options": "Region",
					"has_company_field": True,
					"default_value": "_Test Region",
					"mandatory_for_bs": True,
					"mandatory_for_pl": False,
				}
			],
			"dimension_options": {"region": [{"name": "_Test Region"}]},
		}

		with patch(
			"advanced_bank_reconciliation.api.create_voucher.get_accounting_dimension_context",
			return_value=dimension_context,
		):
			result = get_create_defaults(bank_transaction.name)

		self.assertEqual(
			result["options"]["accounting_dimensions"],
			dimension_context["accounting_dimensions"],
		)
		self.assertEqual(
			result["options"]["dimension_options"],
			dimension_context["dimension_options"],
		)

	def test_create_journal_entry_from_withdrawal_reconciles_transaction(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=33,
			reference_number="_ABR-PHASE3-JE",
		)
		account = self._ledger_account("Expense")

		result = create_voucher_from_transaction(
			bank_transaction.name,
			{
				"account": account,
				"posting_date": nowdate(),
				"reference_date": nowdate(),
				"reference_number": "_ABR-PHASE3-JE",
			},
		)

		self.assertEqual(result["voucher_type"], "Journal Entry")
		self.assertTrue(result["voucher_name"])
		journal_entry = frappe.get_doc("Journal Entry", result["voucher_name"])
		self.assertEqual(journal_entry.docstatus, 1)
		bank_transaction.reload()
		self.assertEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 0.0, places=2)

	def test_create_draft_handoff_does_not_reconcile_transaction(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			deposit=44,
			reference_number="_ABR-PHASE3-DRAFT",
		)
		account = self._ledger_account("Income")

		result = create_voucher_draft_from_transaction(
			bank_transaction.name,
			{
				"account": account,
				"posting_date": nowdate(),
				"reference_date": nowdate(),
				"reference_number": "_ABR-PHASE3-DRAFT",
			},
		)

		self.assertEqual(result["voucher_type"], "Journal Entry")
		self.assertIn("/app/journal-entry/", result["desk_url"])
		journal_entry = frappe.get_doc("Journal Entry", result["voucher_name"])
		self.assertEqual(journal_entry.docstatus, 0)
		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertFalse(bank_transaction.payment_entries)

	def test_create_payment_entry_draft_handoff(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			deposit=22,
			reference_number="_ABR-PHASE3-PE-DRAFT",
		)

		result = create_voucher_draft_from_transaction(
			bank_transaction.name,
			{
				"party_type": "Customer",
				"party": TEST_CUSTOMER,
				"mode_of_payment": "Cash",
				"posting_date": nowdate(),
				"reference_date": nowdate(),
				"reference_number": "_ABR-PHASE3-PE-DRAFT",
			},
		)

		self.assertEqual(result["voucher_type"], "Payment Entry")
		self.assertIn("/app/payment-entry/", result["desk_url"])
		payment_entry = frappe.get_doc("Payment Entry", result["voucher_name"])
		self.assertEqual(payment_entry.docstatus, 0)
		self.assertEqual(payment_entry.party_type, "Customer")
		self.assertEqual(payment_entry.party, TEST_CUSTOMER)
		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertFalse(bank_transaction.payment_entries)

	def test_create_voucher_rejects_unsupported_party_type(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			deposit=24,
			reference_number="_ABR-PHASE3-PARTY",
		)
		account = self._ledger_account("Income")

		with self.assertRaises(frappe.ValidationError):
			create_voucher_from_transaction(
				bank_transaction.name,
				{
					"account": account,
					"party_type": "Lead",
					"party": "_ABR-NO-SUCH-LEAD",
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE3-PARTY",
				},
			)

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertFalse(bank_transaction.payment_entries)

	def test_save_as_rule_creates_rule_after_voucher_creation(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=38,
			reference_number="_ABR-PHASE3-RULE-SUCCESS",
		)
		account = self._ledger_account("Expense")
		rule_title = "_ABR Phase 3 Rule {0}".format(bank_transaction.name)

		result = create_voucher_from_transaction(
			bank_transaction.name,
			{
				"account": account,
				"posting_date": nowdate(),
				"reference_date": nowdate(),
				"reference_number": "_ABR-PHASE3-RULE-SUCCESS",
				"save_as_rule": True,
				"rule_title": rule_title,
			},
		)

		self.assertEqual(result["status"], "Reconciled")
		self.assertTrue(result["rule"]["name"])
		rule = frappe.get_doc("ABR Bank Rule", result["rule"]["name"])
		self.assertEqual(rule.title, rule_title)
		self.assertEqual(rule.bank_account, self.bank_account)
		self.assertEqual(rule.entry_type, "Journal Entry")
		self.assertEqual(rule.account, account)
		self.assertTrue(rule.conditions)
		bank_transaction.reload()
		self.assertEqual(bank_transaction.status, "Reconciled")

	def test_save_as_rule_requires_title_before_voucher_creation(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=37,
			reference_number="_ABR-PHASE3-RULE-TITLE",
		)
		account = self._ledger_account("Expense")

		with self.assertRaises(frappe.ValidationError):
			create_voucher_from_transaction(
				bank_transaction.name,
				{
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE3-RULE-TITLE",
					"save_as_rule": True,
				},
			)

		bank_transaction.reload()
		self.assertNotEqual(bank_transaction.status, "Reconciled")
		self.assertFalse(bank_transaction.payment_entries)


class TestBankRecPhaseFourAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(company=TEST_COMPANY)
		frappe.db.commit()

	def _ledger_account(self, root_type):
		account = frappe.db.get_value(
			"Account",
			{
				"company": TEST_COMPANY,
				"root_type": root_type,
				"is_group": 0,
				"disabled": 0,
			},
			"name",
		)
		self.assertTrue(account, "Expected a ledger account for {0}".format(root_type))
		return account

	def test_cash_coding_rows_include_unreconciled_transactions(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=18,
			reference_number="_ABR-PHASE4-ROWS",
		)

		result = get_cash_coding_rows(
			self.bank_account,
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
		)

		names = {row["transaction"]["name"] for row in result["rows"]}
		self.assertIn(bank_transaction.name, names)

	def test_cash_coding_rows_include_accounting_dimensions(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=17,
			reference_number="_ABR-PHASE4-DIMS",
		)
		dimension_context = {
			"accounting_dimensions": [
				{
					"fieldname": "region",
					"fieldtype": "Link",
					"label": "Region",
					"options": "Region",
					"has_company_field": True,
					"default_value": "_Test Region",
					"mandatory_for_bs": True,
					"mandatory_for_pl": False,
				}
			],
			"dimension_options": {"region": [{"name": "_Test Region"}]},
		}

		with patch(
			"advanced_bank_reconciliation.api.cash_coding.get_accounting_dimension_context",
			return_value=dimension_context,
		):
			result = get_cash_coding_rows(
				self.bank_account,
				from_date=add_days(nowdate(), -1),
				to_date=add_days(nowdate(), 1),
			)

		row = next(
			row for row in result["rows"] if row["transaction"]["name"] == bank_transaction.name
		)
		self.assertEqual(row["dimensions"], {})
		self.assertEqual(
			result["options"]["accounting_dimensions"],
			dimension_context["accounting_dimensions"],
		)
		self.assertEqual(
			result["options"]["dimension_options"],
			dimension_context["dimension_options"],
		)

	def test_submit_cash_coding_reconciles_valid_row(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=28,
			reference_number="_ABR-PHASE4-SUBMIT",
		)
		account = self._ledger_account("Expense")

		result = submit_cash_coding(
			[
				{
					"bank_transaction_name": bank_transaction.name,
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE4-SUBMIT",
				}
			]
		)

		self.assertEqual(result["summary"]["success"], 1)
		bank_transaction.reload()
		self.assertEqual(bank_transaction.status, "Reconciled")
		self.assertAlmostEqual(flt(bank_transaction.unallocated_amount), 0.0, places=2)

	def test_submit_cash_coding_returns_row_level_errors(self):
		valid_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=19,
			reference_number="_ABR-PHASE4-VALID",
		)
		invalid_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=21,
			reference_number="_ABR-PHASE4-INVALID",
		)
		account = self._ledger_account("Expense")

		result = submit_cash_coding(
			[
				{
					"bank_transaction_name": valid_transaction.name,
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE4-VALID",
				},
				{
					"bank_transaction_name": invalid_transaction.name,
					"account": "",
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE4-INVALID",
				},
			]
		)

		self.assertEqual(result["summary"]["success"], 1)
		self.assertEqual(result["summary"]["error"], 1)
		valid_transaction.reload()
		invalid_transaction.reload()
		self.assertEqual(valid_transaction.status, "Reconciled")
		self.assertNotEqual(invalid_transaction.status, "Reconciled")

	def test_preview_cash_coding_rejects_reconciled_transaction(self):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=26,
			reference_number="_ABR-PHASE4-PREVIEW",
		)
		account = self._ledger_account("Expense")
		setup_result = submit_cash_coding(
			[
				{
					"bank_transaction_name": bank_transaction.name,
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE4-PREVIEW",
				}
			]
		)
		self.assertEqual(setup_result["summary"]["success"], 1, setup_result)
		bank_transaction.reload()
		self.assertEqual(bank_transaction.status, "Reconciled")

		result = preview_cash_coding(
			[
				{
					"bank_transaction_name": bank_transaction.name,
					"account": account,
					"posting_date": nowdate(),
					"reference_date": nowdate(),
					"reference_number": "_ABR-PHASE4-PREVIEW",
				}
			]
		)

		self.assertEqual(result["results"][0]["status"], "error")
		self.assertIn("already reconciled", result["results"][0]["message"])


class TestBankRecPhaseFiveAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.bank_account = setup_abr_test_data(company=TEST_COMPANY)
		frappe.db.commit()

	def _ledger_account(self, root_type):
		account = frappe.db.get_value(
			"Account",
			{
				"company": TEST_COMPANY,
				"root_type": root_type,
				"is_group": 0,
				"disabled": 0,
			},
			"name",
		)
		self.assertTrue(account, "Expected a ledger account for {0}".format(root_type))
		return account

	def _matched_journal_entry_fixture(self, amount=31):
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=amount,
			reference_number="_ABR-PHASE5-MATCHED",
		)
		result = create_voucher_from_transaction(
			bank_transaction.name,
			{
				"account": self._ledger_account("Expense"),
				"posting_date": nowdate(),
				"reference_date": nowdate(),
				"reference_number": "_ABR-PHASE5-MATCHED",
			},
		)
		return bank_transaction, result["voucher_name"]

	def _submitted_bank_journal_entry(self, amount=100):
		bank_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
		expense_account = self._ledger_account("Expense")
		cost_center = frappe.db.get_value(
			"Cost Center",
			{"company": TEST_COMPANY, "is_group": 0},
			"name",
		)
		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Bank Entry",
				"company": TEST_COMPANY,
				"posting_date": nowdate(),
				"cheque_no": "_ABR-PHASE5-SHARED",
				"cheque_date": nowdate(),
				"accounts": [
					{
						"account": expense_account,
						"debit_in_account_currency": amount,
						"debit": amount,
						"cost_center": cost_center,
					},
					{
						"account": bank_account,
						"credit_in_account_currency": amount,
						"credit": amount,
					},
				],
			}
		)
		journal_entry.insert()
		journal_entry.submit()
		return journal_entry

	def test_matched_transactions_list_reconciled_rows(self):
		bank_transaction, _journal_entry = self._matched_journal_entry_fixture()

		result = get_matched_transactions(
			self.bank_account,
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
		)

		names = {row["name"] for row in result["rows"]}
		self.assertIn(bank_transaction.name, names)

	def test_matched_transactions_include_all_linked_payments(self):
		first_invoice = create_test_sales_invoice(outstanding=2000)
		second_invoice = create_test_sales_invoice(outstanding=2950)
		bank_transaction = create_test_bank_transaction(
			self.bank_account,
			deposit=4950,
			reference_number="_ABR-PHASE5-SPLIT",
		)

		submit_match(
			bank_transaction.name,
			[
				{
					"voucher_type": "Sales Invoice",
					"voucher_name": first_invoice.name,
					"amount": 2000,
				},
				{
					"voucher_type": "Sales Invoice",
					"voucher_name": second_invoice.name,
					"amount": 2950,
				},
			],
		)

		result = get_matched_transactions(
			self.bank_account,
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
		)
		row = next(row for row in result["rows"] if row["name"] == bank_transaction.name)

		self.assertEqual(len(row["linked_payments"]), 2)
		self.assertEqual(
			{payment["payment_entry"] for payment in row["linked_payments"]},
			{first_invoice.name, second_invoice.name},
		)
		self.assertAlmostEqual(
			sum(flt(payment["allocated_amount"]) for payment in row["linked_payments"]),
			4950,
			places=2,
		)

	def test_unreconcile_only_keeps_linked_journal_entry_submitted(self):
		bank_transaction, journal_entry_name = self._matched_journal_entry_fixture(amount=32)

		result = unreconcile_transaction(bank_transaction.name, cancel_linked_documents="false")

		self.assertEqual(result["transaction"]["status"], "Unreconciled")
		self.assertFalse(result["cancel_linked_documents"])
		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		self.assertEqual(journal_entry.docstatus, 1)
		bank_transaction.reload()
		self.assertFalse(bank_transaction.payment_entries)

	def test_unreconcile_does_not_cancel_document_still_allocated_elsewhere(self):
		journal_entry = self._submitted_bank_journal_entry(amount=100)
		first_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=40,
			reference_number="_ABR-PHASE5-SHARED-1",
		)
		second_transaction = create_test_bank_transaction(
			self.bank_account,
			withdrawal=60,
			reference_number="_ABR-PHASE5-SHARED-2",
		)

		submit_match(
			first_transaction.name,
			[
				{
					"voucher_type": "Journal Entry",
					"voucher_name": journal_entry.name,
					"amount": 40,
				}
			],
		)
		submit_match(
			second_transaction.name,
			[
				{
					"voucher_type": "Journal Entry",
					"voucher_name": journal_entry.name,
					"amount": 60,
				}
			],
		)

		unreconcile_transaction(first_transaction.name, cancel_linked_documents=True)

		journal_entry.reload()
		first_transaction.reload()
		second_transaction.reload()
		self.assertEqual(journal_entry.docstatus, 1)
		self.assertFalse(first_transaction.payment_entries)
		self.assertEqual(second_transaction.status, "Reconciled")
		self.assertTrue(
			any(row.payment_entry == journal_entry.name for row in second_transaction.payment_entries)
		)

	def test_unreconcile_can_cancel_linked_journal_entry(self):
		bank_transaction, journal_entry_name = self._matched_journal_entry_fixture(amount=34)

		unreconcile_transaction(bank_transaction.name, cancel_linked_documents=True)

		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		self.assertEqual(journal_entry.docstatus, 2)
		bank_transaction.reload()
		self.assertFalse(bank_transaction.payment_entries)
