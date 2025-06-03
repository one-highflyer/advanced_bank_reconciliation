# Copyright (c) 2024, High Flyer and contributors
# For license information, please see license.txt
import os
import frappe
import json
from datetime import datetime
from frappe.model.document import Document
from frappe.utils.xlsxutils import (
    read_xls_file_from_attached_file,
    read_xlsx_file_from_attached_file,
)
from frappe.utils.csvutils import read_csv_content
from frappe.utils import getdate

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

def start_import(file_path, bank_account=None):
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
	if bank_account:
		bank_doc = frappe.get_doc("Bank Account", bank_account)
		if bank_doc.bank:
			bank = frappe.get_doc("Bank", bank_doc.bank)
			# Get bank transaction mapping
			for mapping in bank.bank_transaction_mapping:
				bank_mapping[mapping.file_field] = mapping.bank_transaction_field
			# Get date format
			bank_mapping['date_format'] = bank.bank_statement_date_format or "Auto"
	
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
        except (ValueError, TypeError):
            pass
    
    # Fallback to auto detection
    try:
        return getdate(date_str)
    except (ValueError, TypeError):
        return None


@frappe.whitelist()
def form_start_import(data_import, bank_account=None):
	out = start_import(data_import, bank_account)
	return out

@frappe.whitelist()
def map_fields(data, data_headers, data_body):
    out = build_table(json.loads(data),json.loads(data_headers),json.loads(data_body))
    return out


@frappe.whitelist()
def get_last_transaction(bank_account):
    print("Bank account: ", bank_account)
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
		bank_transactions = []
		for item in dataset:
			bank_transactions.append({
				"date": item[0],
				"bank_account": item[5],
				"deposit": item[1],
				"withdrawal": item[2],
				"reference_number": item[4],
				"description": item[3]
			})
		for transaction in bank_transactions:
			bank_transaction = frappe.new_doc("Bank Transaction")
			bank_transaction.update(transaction)
			bank_transaction.insert()
			bank_transaction.submit()
		print("Bank transactions submitted")
		return True
	except (ValueError, TypeError, KeyError) as e:
		frappe.log_error(f"Publish records error: {str(e)}")
		print("Publish exception")
		return False
	finally:
		print("After publish")
