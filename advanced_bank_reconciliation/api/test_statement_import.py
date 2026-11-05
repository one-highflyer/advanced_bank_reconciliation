"""Focused unit tests. These tests do not connect to a site or write site data."""

import copy
import hashlib
import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import frappe
from openpyxl import Workbook

from advanced_bank_reconciliation.api import statement_import as api


HEADERS = [
    "Date",
    "Amount",
    "Description",
    "Reference",
    "Particulars",
    "Code",
    "Other Party",
    "Deposit",
    "Withdrawal",
]
SOURCE = [
    ["05/11/2026", "125.50", "Transfer", 123, 0, 456, "Counterparty", "125.50", ""],
    ["06/11/2026", "-25", "Payment", 0, "", "", "", "", "25"],
]
FILE_HASH = "a" * 64


def mapping(**changes):
    result = dict(
        date_select="Date",
        date_format="d/m/Y",
        same_amount_field=True,
        amount_select="Amount",
        positive_field="Deposit",
        deposit_select="",
        withdrawal_select="",
        description_select="Description",
        reference_number_select="Reference",
        particulars_select="Particulars",
        code_select="Code",
        other_party_select="Other Party",
        save_mapping_for_future_use=False,
    )
    result.update(changes)
    return result


class MemoryDatabase:
    """A transaction stub that lets failure tests inspect the savepoint boundary."""

    def __init__(self):
        self.rows = []
        self.snapshots = {}
        self.get_value = Mock(return_value="_Test Bank Account")
        self.rollback = Mock(side_effect=self._rollback)
        self.release_savepoint = Mock(side_effect=lambda name: self.snapshots.pop(name))

    def savepoint(self, name):
        self.snapshots[name] = copy.deepcopy(self.rows)

    def _rollback(self, save_point):
        self.rows = self.snapshots[save_point]

    def get_values(self, doctype, filters=None, fieldname=None, **kwargs):
        rows = self.rows
        if "transaction_id" in filters:
            prefix = filters["transaction_id"][1][:-1]
            return [
                frappe._dict(row)
                for row in rows
                if row.get("transaction_id", "").startswith(prefix)
            ]
        return [frappe._dict(row) for row in rows if row.get("docstatus") != 2]


class Transaction:
    def __init__(self, database, failures):
        self.database = database
        self.failures = failures

    def update(self, values):
        self.__dict__.update(values)

    def precision(self, field):
        return self.failures.get("precision", {}).get(field, 2)

    def insert(self):
        if self.failures.get("insert"):
            self.failures["insert"] -= 1
            raise RuntimeError("internal insert detail")
        self.name = "_Test Bank Transaction " + str(len(self.database.rows) + 1)
        self.database.rows.append(
            frappe._dict(
                {
                    key: value
                    for key, value in self.__dict__.items()
                    if key not in ("database", "failures")
                }
            )
        )

    def submit(self):
        self.failures["submits"] = self.failures.get("submits", 0) + 1
        if self.failures.get("submit_at") == self.failures["submits"]:
            raise RuntimeError("internal submit detail")
        self.database.rows[-1].docstatus = 1


class TestStatementImport(unittest.TestCase):
    def setUp(self):
        context = patch.object(
            frappe.local, "flags", frappe._dict(in_test=True), create=True
        )
        context.start()
        self.addCleanup(context.stop)
        self.db = MemoryDatabase()
        self.failures = {}
        self.bank = frappe._dict(
            name="_Test Bank Account",
            account_name="Test Account",
            account="_Test Ledger",
            company="_Test Company",
            bank=None,
            is_credit_card=0,
        )
        self.source = copy.deepcopy(SOURCE)
        self._patch(
            "_fail",
            side_effect=lambda message: (_ for _ in ()).throw(
                frappe.ValidationError(message)
            ),
        )
        self._patch("_account_context", return_value=(self.bank, "NZD", False))
        self._patch(
            "_read_statement", side_effect=lambda url: (HEADERS, self.source, FILE_HASH)
        )
        self._patch("_bank_mapping", return_value=(None, {"date_format": "Auto"}))
        self._patch("get_logger", return_value=Mock())
        self._patch("_", side_effect=lambda message: message)
        for target, value in (
            ("db", self.db),
            ("session", frappe._dict(user="_Test Import User")),
        ):
            context = patch.object(frappe, target, value, create=True)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(frappe, "has_permission", return_value=True)
        self.permissions = context.start()
        self.addCleanup(context.stop)
        context = patch.object(
            frappe,
            "new_doc",
            side_effect=lambda doctype: Transaction(self.db, self.failures),
        )
        context.start()
        self.addCleanup(context.stop)

    def _patch(self, name, **kwargs):
        context = patch.object(api, name, **kwargs)
        mock = context.start()
        self.addCleanup(context.stop)
        return mock

    def preview(self, **changes):
        return api.preview_statement(
            self.bank.name, "/private/files/statement.csv", mapping(**changes)
        )

    def run_import(self, **changes):
        args = dict(
            bank_account=self.bank.name,
            file_url="/private/files/statement.csv",
            mapping=mapping(),
            selected_rows=[0, 1],
            file_hash=FILE_HASH,
            request_id="test-request",
        )
        args.update(changes)
        return api.import_statement(**args)

    def test_signed_amounts_and_numeric_text_are_preserved(self):
        result = self.preview()
        self.assertEqual(result["rows"][0]["deposit"], 125.5)
        self.assertEqual(result["rows"][1]["withdrawal"], 25)
        self.assertEqual(result["rows"][0]["reference_number"], "123")
        self.assertEqual(result["rows"][1]["reference_number"], "0")
        self.assertEqual(result["rows"][0]["custom_particulars"], "0")
        self.assertEqual(result["rows"][0]["custom_code"], "456")
        self.assertEqual(
            result["summary"],
            dict(
                total=2,
                ready=2,
                possible_duplicates=0,
                errors=0,
                money_in=125.5,
                money_out=25,
            ),
        )

    def test_separate_amounts_and_positive_withdrawal_selection(self):
        self.assertEqual(
            self.preview(
                same_amount_field=False,
                deposit_select="Deposit",
                withdrawal_select="Withdrawal",
            )["rows"][1]["withdrawal"],
            25,
        )
        self.assertEqual(
            self.preview(positive_field="Withdrawal")["rows"][0]["withdrawal"], 125.5
        )
        self.assertEqual(
            self.preview(positive_field="Withdrawal")["rows"][1]["deposit"], 25
        )

    def test_credit_card_preview_and_insert_use_one_direction_change(self):
        api._account_context.return_value = (self.bank, "NZD", True)
        self.assertEqual(self.preview()["rows"][0]["withdrawal"], 125.5)
        result = self.run_import()
        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(self.db.rows[0].withdrawal, 125.5)
        self.assertEqual(self.db.rows[0].deposit, 0)

    def test_all_explicit_date_formats_are_strict_and_native_dates_work(self):
        for label, pattern in api.DATE_FORMATS.items():
            with self.subTest(label=label):
                self.assertEqual(
                    api._parse_date(date(2026, 11, 5).strftime(pattern), label),
                    "2026-11-05",
                )
        self.assertEqual(
            api._parse_date(datetime(2026, 11, 5, 14), "d/m/Y"), "2026-11-05"
        )
        self.assertEqual(api._parse_date(date(2026, 11, 5), "d/m/Y"), "2026-11-05")
        self.assertEqual(api._parse_date("2026-11-05", "Auto"), "2026-11-05")
        with self.assertRaises(ValueError):
            api._parse_date("2026-11-05", "d/m/Y")

    def test_saved_mapping_and_stale_mapping_are_not_replaced(self):
        saved = dict(
            date="Old Date",
            deposit="Amount",
            withdrawal="Amount",
            description="Description",
            reference_number="Reference",
            custom_code="Old Code",
            date_format="m/d/Y",
        )
        result, stale = api._default_mapping(HEADERS, saved)
        self.assertEqual(result["date_select"], "")
        self.assertEqual(result["code_select"], "")
        self.assertEqual(result["date_format"], "m/d/Y")
        self.assertEqual(result["positive_field"], "Deposit")
        self.assertTrue(result["same_amount_field"])
        self.assertEqual(stale, ["Old Date", "Old Code"])

    def test_new_mapping_suggests_columns_and_prepare_skips_empty_rows(self):
        self.source.insert(1, [None] * len(HEADERS))
        result = api.prepare_statement(self.bank.name, "/files/statement.csv")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["mapping"]["reference_number_select"], "Reference")
        self.assertEqual(set(result["mapping"]), set(mapping()))
        self.assertEqual(self.preview()["rows"][1]["source_row"], 4)
        self.assertEqual(self.preview()["rows"][1]["index"], 1)

    def test_bad_source_rows_are_visible_and_block_even_if_unselected(self):
        self.source[1][0] = "not a date"
        result = self.preview()
        self.assertIsNone(result["rows"][1]["date"])
        self.assertTrue(result["rows"][1]["errors"])
        with self.assertRaisesRegex(frappe.ValidationError, "invalid rows"):
            self.run_import(selected_rows=[0])
        self.assertEqual(self.db.rows, [])

    def test_invalid_amounts_never_become_ready_rows(self):
        for value in (
            "NaN",
            "Infinity",
            "1,00",
            "letters",
            "0",
            "-",
            1e-10,
            float("inf"),
            "1000000000000",
        ):
            with self.subTest(value=value):
                self.source[0][1] = value
                self.assertTrue(self.preview()["rows"][0]["errors"])
        self.assertEqual(api._parse_amount("1,200.50"), 1200.5)
        self.assertEqual(api._parse_amount(1e-7), 1e-7)

    def test_separate_negative_both_sides_and_zero_are_invalid(self):
        for deposit, withdrawal in (("-5", ""), ("5", "5"), ("", "")):
            self.source[0][7:9] = [deposit, withdrawal]
            self.assertTrue(
                self.preview(
                    same_amount_field=False,
                    deposit_select="Deposit",
                    withdrawal_select="Withdrawal",
                )["rows"][0]["errors"]
            )

    def test_currency_precision_rejects_amounts_without_rounding(self):
        for value in ("0.001", "10.001"):
            with self.subTest(value=value):
                self.source[0][1] = value
                preview = self.preview()
                self.assertIn("2 decimal places", preview["rows"][0]["errors"][0])
                self.assertEqual(preview["summary"]["money_in"], 0)
                with self.assertRaisesRegex(frappe.ValidationError, "invalid rows"):
                    self.run_import(selected_rows=[0])
        self.source[0][1] = "10.01"
        self.assertFalse(self.preview()["rows"][0]["errors"])
        self.assertEqual(self.preview()["rows"][0]["deposit"], 10.01)

    def test_configured_precision_applies_to_amount_and_unallocated_fields(self):
        self.source[0][1] = "10.001"
        self.failures["precision"] = dict(deposit=3, withdrawal=3, unallocated_amount=3)
        self.assertFalse(self.preview()["rows"][0]["errors"])
        self.assertEqual(self.preview()["rows"][0]["deposit"], 10.001)
        self.failures["precision"]["unallocated_amount"] = 2
        self.assertIn("2 decimal places", self.preview()["rows"][0]["errors"][0])

    def test_precision_document_receives_account_company_and_currency(self):
        transaction = Mock()
        transaction.precision.return_value = 3
        with patch.object(frappe, "new_doc", return_value=transaction):
            self.assertEqual(
                api._amount_precisions(self.bank, "NZD"), dict(deposit=3, withdrawal=3)
            )
        transaction.update.assert_called_once_with(
            dict(bank_account=self.bank.name, company=self.bank.company, currency="NZD")
        )

    def test_mapping_requires_description_reference_and_signed_direction(self):
        for change in (
            dict(description_select=""),
            dict(reference_number_select=""),
            dict(positive_field=""),
            dict(date_format="invalid"),
            dict(code_select="Missing"),
        ):
            with self.subTest(change=change), self.assertRaises(frappe.ValidationError):
                self.preview(**change)

    def test_duplicate_checks_continue_after_a_new_row(self):
        row = self.preview()["rows"][1]
        self.db.rows = [frappe._dict(row, name="_Test Existing", docstatus=1)]
        result = self.preview()
        self.assertFalse(result["rows"][0]["is_duplicate"])
        self.assertTrue(result["rows"][1]["is_duplicate"])
        with self.assertRaisesRegex(frappe.ValidationError, "may be duplicates"):
            self.run_import()
        with self.assertRaisesRegex(
            frappe.ValidationError, "duplicate rows have changed"
        ):
            self.run_import(include_duplicates=True)
        result = self.run_import(include_duplicates=True, confirmed_duplicate_rows=[1])
        self.assertEqual(result["imported_count"], 2)

    def test_duplicate_source_rows_warn_and_can_be_imported_deliberately(self):
        self.source[1] = list(self.source[0])
        self.assertEqual(self.preview()["summary"]["possible_duplicates"], 2)
        result = self.run_import(
            include_duplicates=True, confirmed_duplicate_rows=[0, 1]
        )
        self.assertEqual(result["imported_count"], 2)

    def test_new_duplicate_at_submit_requires_new_consent(self):
        rows = self.preview()["rows"]
        self.db.rows = [
            frappe._dict(row, name=f"_Test Existing {index}", docstatus=1)
            for index, row in enumerate(rows)
        ]
        with self.assertRaisesRegex(
            frappe.ValidationError, "duplicate rows have changed"
        ):
            self.run_import(include_duplicates=True, confirmed_duplicate_rows=[0])

    def test_hash_and_row_selection_are_revalidated(self):
        for changes in (
            dict(file_hash="b" * 64),
            dict(selected_rows=[-1]),
            dict(selected_rows=[2]),
            dict(selected_rows=[True]),
            dict(selected_rows=["0"]),
            dict(selected_rows=[0, 0]),
            dict(selected_rows=[]),
            dict(selected_rows=[dict(deposit=500)]),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(frappe.ValidationError),
            ):
                self.run_import(**changes)
        self.assertEqual(self.db.rows, [])

    def test_create_and_submit_permissions_checked_before_reading_file(self):
        self.permissions.side_effect = frappe.PermissionError("Permission denied")
        with self.assertRaises(frappe.PermissionError):
            self.run_import()
        api._read_statement.assert_not_called()

    def test_access_denial_prevents_preview(self):
        api._account_context.side_effect = frappe.PermissionError(
            "Bank Account access denied"
        )
        with self.assertRaises(frappe.PermissionError):
            self.preview()
        api._read_statement.assert_not_called()

    def test_context_reports_latest_transaction_and_mapping_permission(self):
        bank = Mock()
        api._bank_mapping.return_value = bank, {"date_format": "d/m/Y"}
        last = dict(name="_Test Existing", date="2026-11-04", deposit=5, withdrawal=0)
        with patch.object(frappe, "get_list", return_value=[last]) as get_list:
            result = api.get_import_context(self.bank.name)
        self.assertEqual(result["last_transaction"], last)
        self.assertEqual(result["currency"], "NZD")
        self.assertTrue(result["can_save_mapping"])
        self.assertEqual(get_list.call_args.kwargs["filters"]["docstatus"], 1)

    def test_public_endpoints_only_allow_authenticated_post_requests(self):
        for endpoint in (
            api.get_import_context,
            api.prepare_statement,
            api.preview_statement,
            api.import_statement,
        ):
            self.assertEqual(
                frappe.allowed_http_methods_for_whitelisted_func[endpoint], ["POST"]
            )
            self.assertNotIn(endpoint, frappe.guest_methods)

    def test_mapping_save_preserves_other_fields_and_uses_normal_permissions(self):
        bank = Mock()
        other = frappe._dict(
            bank_transaction_field="transaction_type", file_field="Type"
        )
        previous = frappe._dict(bank_transaction_field="date", file_field="Old Date")
        bank.get.return_value = [other, previous]
        api._save_mapping(bank, mapping())
        bank.set.assert_called_once_with("bank_transaction_mapping", [other])
        bank.save.assert_called_once_with()
        self.assertEqual(bank.bank_statement_date_format, "d/m/Y")
        bank.append.assert_any_call(
            "bank_transaction_mapping",
            dict(bank_transaction_field="date", file_field="Date"),
        )

    def test_insert_and_submit_failures_rollback_and_request_can_retry(self):
        for failure in (dict(insert=1), dict(submit_at=2)):
            with self.subTest(failure=failure):
                self.db.rows = []
                self.failures.clear()
                self.failures.update(failure)
                with self.assertRaisesRegex(
                    frappe.ValidationError, "No rows were imported"
                ):
                    self.run_import()
                self.assertEqual(self.db.rows, [])
                self.failures.clear()
                result = self.run_import()
                self.assertEqual(result["imported_count"], 2)
                self.assertFalse(result["idempotent"])

    def test_request_id_retry_returns_same_transactions_without_new_consent(self):
        first = self.run_import()
        second = self.run_import()
        self.assertEqual(second["transactions"], first["transactions"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(len(self.db.rows), 2)
        with self.assertRaisesRegex(frappe.ValidationError, "request ID was used"):
            self.run_import(selected_rows=[0])

    def test_mapping_save_without_bank_or_write_permission_warns(self):
        result = self.run_import(mapping=mapping(save_mapping_for_future_use=True))
        self.assertFalse(result["mapping_saved"])
        self.assertIn("no linked Bank", result["warnings"][0])
        bank = Mock()
        api._bank_mapping.return_value = bank, {}
        self.permissions.return_value = False
        saved_bank, warnings = api._mapping_save_state(
            self.bank, mapping(save_mapping_for_future_use=True)
        )
        self.assertIsNone(saved_bank)
        self.assertIn("write permission", warnings[0])

    def test_mapping_save_failure_is_atomic_and_not_ignored(self):
        bank = Mock()
        api._bank_mapping.return_value = bank, {}
        self._patch("_save_mapping", side_effect=RuntimeError("private failure detail"))
        with self.assertRaisesRegex(
            frappe.ValidationError, "mapping could not be saved"
        ):
            self.run_import(mapping=mapping(save_mapping_for_future_use=True))
        self.assertEqual(self.db.rows, [])
        self.db.rollback.assert_called_once()


class TestStatementFileValidation(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "statement.csv"
        self.path.write_text(
            "Date,Amount,Description,Reference\n2026-11-05,5,Transfer,0\n"
        )
        self.doc = Mock(
            file_url="/private/files/statement.csv",
            is_remote_file=False,
            is_folder=False,
        )
        self.doc.get_full_path.return_value = str(self.path)
        self._patch(
            "_fail",
            side_effect=lambda message: (_ for _ in ()).throw(
                frappe.ValidationError(message)
            ),
        )
        for name, value in (("db", Mock(get_value=Mock(return_value="_Test File"))),):
            context = patch.object(frappe, name, value, create=True)
            context.start()
            self.addCleanup(context.stop)
        for name, kwargs in (
            ("get_doc", dict(return_value=self.doc)),
            ("has_permission", dict(return_value=True)),
            ("get_site_path", dict(return_value=str(self.root))),
        ):
            context = patch.object(frappe, name, **kwargs)
            context.start()
            self.addCleanup(context.stop)

    def _patch(self, name, **kwargs):
        context = patch.object(api, name, **kwargs)
        result = context.start()
        self.addCleanup(context.stop)
        return result

    def test_csv_file_is_read_from_uploaded_path_and_hashed(self):
        headers, rows, digest = api._read_statement(self.doc.file_url)
        self.assertEqual(headers, ["Date", "Amount", "Description", "Reference"])
        self.assertEqual(rows[0][-1], "0")
        self.assertEqual(digest, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_xlsx_and_xls_preserve_native_dates(self):
        workbook = Workbook()
        workbook.active.append(["Date", "Amount", "Description", "Reference"])
        workbook.active.append([datetime(2026, 11, 5), 5, "Transfer", 123])
        buffer = BytesIO()
        workbook.save(buffer)
        self.path.write_bytes(buffer.getvalue())
        self.doc.file_url = "/private/files/statement.xlsx"
        _, rows, _ = api._read_statement(self.doc.file_url)
        self.assertIsInstance(rows[0][0], datetime)
        self.doc.file_url = "/private/files/statement.xls"
        book = Mock(datemode=0)
        sheet = book.sheet_by_index.return_value
        sheet.nrows = 2
        sheet.row.side_effect = [
            [Mock(ctype=1, value="Date")],
            [Mock(ctype=api.xlrd.XL_CELL_DATE, value=46331)],
        ]
        with patch.object(api.xlrd, "open_workbook", return_value=book):
            _, rows, _ = api._read_statement(self.doc.file_url)
        self.assertIsInstance(rows[0][0], datetime)

    def test_csv_source_rows_account_for_multiline_cells(self):
        self.path.write_text(
            'Date,Amount,Description,Reference\n2026-11-05,5,"Line one\nLine two",0\n2026-11-06,6,Transfer,1\n'
        )
        _, rows, _ = api._read_statement(self.doc.file_url)
        self.assertEqual(rows[0].source_row, 2)
        self.assertEqual(rows[1].source_row, 4)

    def test_unsafe_missing_and_unreadable_file_are_rejected(self):
        for url in (
            "/etc/passwd",
            "https://example.invalid/file.csv",
            "/files/../secret.csv",
            "/private/files/%2e%2e/secret.csv",
            "/files/statement.csv?x=1",
            "/files/a\\b.csv",
        ):
            with self.subTest(url=url), self.assertRaises(frappe.ValidationError):
                api._read_statement(url)
        frappe.db.get_value.return_value = None
        with self.assertRaisesRegex(frappe.ValidationError, "not found"):
            api._read_statement(self.doc.file_url)
        frappe.db.get_value.return_value = "_Test File"
        self.doc.get_full_path.return_value = str(self.root.parent / "outside.csv")
        with self.assertRaisesRegex(frappe.ValidationError, "outside"):
            api._read_statement(self.doc.file_url)

    def test_file_read_permission_is_required(self):
        frappe.has_permission.side_effect = frappe.PermissionError(
            "Private file access denied"
        )
        with self.assertRaises(frappe.PermissionError):
            api._read_statement(self.doc.file_url)

    def test_repeated_headers_are_rejected(self):
        self.path.write_text(
            "Date,Amount,Amount,Description,Reference\n2026-11-05,5,5,Transfer,1\n"
        )
        with self.assertRaisesRegex(frappe.ValidationError, "repeated column headers"):
            api._read_statement(self.doc.file_url)
