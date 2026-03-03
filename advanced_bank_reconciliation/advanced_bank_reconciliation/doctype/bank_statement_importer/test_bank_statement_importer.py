# Copyright (c) 2024, High Flyer and Contributors
# See license.txt

from datetime import date

from frappe.tests.utils import FrappeTestCase

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.bank_statement_importer.bank_statement_importer import (
    get_selected_bank_mapping,
    is_truthy,
    parse_date,
    parse_json_if_required,
)


class TestBankStatementImporter(FrappeTestCase):
    def test_date_parser(self):
        expected_date = date(2024, 5, 9)

        # d/m/Y
        self.assertEqual(self.convert_date("9/05/2024", "d/m/Y"), expected_date)
        # m/d/Y
        self.assertEqual(self.convert_date("5/09/2024", "m/d/Y"), expected_date)
        # Y/m/d
        self.assertEqual(self.convert_date("2024/05/09", "Y/m/d"), expected_date)
        # Y/d/m
        self.assertEqual(self.convert_date("2024/09/05", "Y/d/m"), expected_date)

    def test_get_selected_bank_mapping_with_same_amount_and_code(self):
        importer_data = {
            "date_select": "Txn Date",
            "same_amount_field": 1,
            "amount_select": "Amount",
            "description_select": "Description",
            "reference_number_select": "Reference",
            "particulars_select": "Particulars",
            "code_select": "Code",
            "other_party_select": "Counterparty",
        }
        self.assertEqual(
            get_selected_bank_mapping(importer_data),
            {
                "date": "Txn Date",
                "deposit": "Amount",
                "withdrawal": "Amount",
                "description": "Description",
                "reference_number": "Reference",
                "custom_particulars": "Particulars",
                "custom_code": "Code",
                "bank_party_name": "Counterparty",
            },
        )

    def test_get_selected_bank_mapping_with_separate_amount_fields(self):
        importer_data = {
            "date_select": "Date",
            "same_amount_field": 0,
            "deposit_select": "Credit",
            "withdrawal_select": "Debit",
        }
        self.assertEqual(
            get_selected_bank_mapping(importer_data),
            {"date": "Date", "deposit": "Credit", "withdrawal": "Debit"},
        )

    def test_parse_json_if_required_and_is_truthy(self):
        self.assertEqual(parse_json_if_required('{"save_mapping_for_future_use": 1}'), {"save_mapping_for_future_use": 1})
        self.assertEqual(parse_json_if_required({"bank_account": "BA-001"}), {"bank_account": "BA-001"})
        self.assertEqual(parse_json_if_required(""), {})
        self.assertEqual(parse_json_if_required("{"), {})
        self.assertEqual(parse_json_if_required("not json"), {})
        self.assertTrue(is_truthy("1"))
        self.assertTrue(is_truthy("true"))
        self.assertFalse(is_truthy("false"))

    def convert_date(self, date_str, date_format):
        return parse_date(date_str, date_format)
