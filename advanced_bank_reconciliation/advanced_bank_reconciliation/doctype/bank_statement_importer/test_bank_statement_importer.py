# Copyright (c) 2024, High Flyer and Contributors
# See license.txt

# import frappe
from datetime import datetime, date
from frappe.tests.utils import FrappeTestCase
from nexwave_insinc_erp_app.nexwave_insinc_erp_app.doctype.bank_statement_importer.bank_statement_importer import parse_date


class TestBankStatementImporter(FrappeTestCase):
		def test_date_parser(self):
				expected_date = date(2024, 5, 9)

				# d/m/Y
				date_str = "9/05/2024"
				d = self.convert_date(date_str, "d/m/Y")
				self.assertEqual(d, expected_date)
				
				# m/d/Y
				date_str = "5/09/2024"
				d = self.convert_date(date_str, "m/d/Y")
				self.assertEqual(d, expected_date)

				# Y/m/d
				date_str = "2024/05/09"
				d = self.convert_date(date_str, "Y/m/d")
				self.assertEqual(d, expected_date)

				# Y/d/m
				date_str = "2024/09/05"
				d = self.convert_date(date_str, "Y/d/m")
				self.assertEqual(d, expected_date)

		def convert_date(self, date, format):
				d = parse_date(date, format)
				print("Date str:", date, "format:", format, "Converted:", d)
				return d
