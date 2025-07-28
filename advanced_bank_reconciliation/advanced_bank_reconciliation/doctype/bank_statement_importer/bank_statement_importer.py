# Copyright (c) 2024, High Flyer and contributors
# For license information, please see license.txt
import json
import logging
import os
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)

logger = frappe.logger("bank_rec", allow_site=True)
logger.setLevel(logging.INFO)

class BankStatementImporter(Document):
	pass

def read_content(content, extension):
	if extension not in ("csv", "xlsx", "xls"):
		frappe.throw(_("Import template should be of type .csv, .xlsx or .xls"), title="Template Error")

	if extension == "csv":
		data = read_csv_content(content)
	elif extension == "xlsx":
		data = read_xlsx_file_from_attached_file(fcontent=content)
	elif extension == "xls":
		data = read_xls_file_from_attached_file(content)

	return data

def start_import(file_path, bank_account):
	# Validate bank_account parameter
	if not bank_account:
		frappe.throw(_("Bank Account is required"), title="Validation Error")
	
	# Validate that bank account exists
	if not frappe.db.exists("Bank Account", bank_account):
		frappe.throw(_("Bank Account '{0}' does not exist").format(bank_account), title="Validation Error")
	
	file_content = None
	file_name = frappe.db.get_value("File", {"file_url": file_path})
	if file_name:
		extn = os.path.splitext(file_path)[1][1:]
		file = frappe.get_doc("File", file_name)
		file_content = file.get_content()
		data = read_content(file_content,extn)
		data_headers = data[0]
		data_body = data[1:]
	
	bank_mapping = {}
	bank_doc = frappe.get_doc("Bank Account", bank_account)
	
	# Validate that bank account is linked to a bank
	if bank_doc.bank:
		try:
			bank = frappe.get_doc("Bank", bank_doc.bank)
			
			# Safely get bank transaction mapping if it exists
			if hasattr(bank, 'bank_transaction_mapping') and bank.bank_transaction_mapping:
				# Get bank transaction mapping - swap key and value
				for mapping in bank.bank_transaction_mapping:
					if hasattr(mapping, 'bank_transaction_field') and hasattr(mapping, 'file_field'):
						bank_mapping[mapping.bank_transaction_field] = mapping.file_field
			
			# Safely get date format with fallback
			date_format = "Auto"  # Default fallback
			if hasattr(bank, 'bank_statement_date_format') and bank.bank_statement_date_format:
				date_format = bank.bank_statement_date_format
			bank_mapping['date_format'] = date_format
			
		except frappe.DoesNotExistError:
			frappe.throw(_("Bank '{0}' linked to Bank Account '{1}' does not exist").format(bank_doc.bank, bank_account), title="Validation Error")
	else:
		# Bank account not linked to any bank - use default date format
		bank_mapping['date_format'] = "Auto"
		frappe.msgprint(_("Bank Account '{0}' is not linked to any Bank. Using default settings.").format(bank_account), title="Warning")
	
	return {
		"header": data_headers,
		"body": data_body,
		"bank": bank_mapping
	}

def build_table(mapping, data_headers, data_body):
	tbl = []
	tbl_header = [
		"Date",
		"Deposit",
		"Withdrawal",
		"Description",
		"Reference Number",
		"Bank Account",
		"Currency"
	]
	tbl.append(tbl_header)

	bank_account = frappe.get_doc("Bank Account", mapping["bank_account"])
	account = frappe.get_doc("Account", bank_account.account)
	currency = account.account_currency
	matching = True

	for data_row in data_body:
		# Skip empty rows
		if not data_row or all(cell is None or cell == "" for cell in data_row):
			continue
		
		tbl_row = []
		# Date
		date = data_row[data_headers.index(mapping["date_select"])]
		date = parse_date(date, mapping["date_format"])
		tbl_row.append(date)
		# Deposit/Withdrawal
		if(mapping["same_amount_field"] == True):
			val = float(data_row[data_headers.index(mapping["amount_select"])])
			if(val >= 0):
				tbl_row.append(abs(val) if mapping["positive_field"] == "Deposit" else 0)
				tbl_row.append(abs(val) if mapping["positive_field"] == "Withdrawal" else 0)
			else:
				tbl_row.append(abs(val) if mapping["positive_field"] == "Withdrawal" else 0)
				tbl_row.append(abs(val) if mapping["positive_field"] == "Deposit" else 0)
		else:
			tbl_row.append(data_row[data_headers.index(mapping["deposit_select"])])
			tbl_row.append(data_row[data_headers.index(mapping["withdrawal_select"])])
		# Description
		tbl_row.append(data_row[data_headers.index(mapping["description_select"])])
		# Reference Number
		tbl_row.append(data_row[data_headers.index(mapping["reference_number_select"])])
		tbl_row.append(bank_account.name)
		tbl_row.append(currency)
		# Duplicates
		if matching:
			duplicates = frappe.db.count(
				"Bank Transaction",
				filters={
					"bank_account": bank_account.name,
					"date": tbl_row[0],
					"deposit": tbl_row[1],
					"withdrawal": tbl_row[2],
					"reference_number": tbl_row[4],
					"description": tbl_row[3],
				},
			)
			if duplicates > 0:
				tbl_row.append(1)
			else:
				matching = False
				tbl_row.append(0)
		else:
			tbl_row.append(0)
		tbl.append(tbl_row)

	return tbl


def parse_date(date_str, format):
	if not date_str:
		return None
	if format == "Auto":
		return getdate(date_str)

	# Define format patterns mapping
	format_patterns = {
		"Y/m/d": "%Y/%m/%d",
		"d/m/Y": "%d/%m/%Y", 
		"dd/mm/YY": "%d/%m/%y",
		"m/d/Y": "%m/%d/%Y",
		"m-d-Y": "%m-%d-%Y",
		"d-m-Y": "%d-%m-%Y",
		"Y-m-d": "%Y-%m-%d",
		"Y/d/m": "%Y/%d/%m"
	}

	# Try to parse with specified format
	pattern = format_patterns.get(format)
	if pattern:
		try:
			return datetime.strptime(str(date_str), pattern).date()
		except (ValueError, TypeError) as e:
			logger.warning("Failed to parse date '%s' with format '%s': %s", date_str, format, str(e))
			pass
	
	# Fallback to auto detection
	try:
		return getdate(date_str)
	except (ValueError, TypeError) as e:
		logger.error("Failed to parse date '%s' with auto detection: %s", date_str, str(e))
		return None


@frappe.whitelist()
def form_start_import(data_import, bank_account):
	out = start_import(data_import, bank_account)
	return out

@frappe.whitelist()
def map_fields(data, data_headers, data_body):
	out = build_table(json.loads(data),json.loads(data_headers),json.loads(data_body))
	return out


@frappe.whitelist()
def get_last_transaction(bank_account):
	logger.info("Getting last transaction for bank account: %s", bank_account)
	# get the last bank transaction doc ordered by date desc for the given bank account
	last_transaction = frappe.get_all(
		"Bank Transaction",
		filters={"bank_account": bank_account, "docstatus": 1},
		fields=["date", "deposit", "withdrawal"],
		order_by="date desc",
		limit_page_length=1,
	)

	if last_transaction:
		return last_transaction[0]
	return None


@frappe.whitelist()
def publish_records(data_import):
	try:
		dataset = (json.loads(data_import))[1:]
		logger.info("Importing %s bank transactions", len(dataset))
		for item in dataset:
			bank_transaction_dict = {
				"date": item[0],
				"bank_account": item[5],
				"currency": item[6],
				"deposit": item[1],
				"withdrawal": item[2],
				"reference_number": item[4],
				"description": str(item[3]) if item[3] else None
			}

			bank_transaction = frappe.new_doc("Bank Transaction")
			bank_transaction.update(bank_transaction_dict)
			bank_transaction.insert()
			bank_transaction.submit()
		logger.info("Bank transactions submitted successfully")
		return True
	except Exception as e:
		logger.error("Publish records error: %s", str(e), exc_info=True)
		frappe.db.rollback()
		return False
