# Copyright (c) 2024, High Flyer and contributors
# For license information, please see license.txt
import json
import logging
import os
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import (
    read_xls_file_from_attached_file,
    read_xlsx_file_from_attached_file,
)

logger = frappe.logger("bank_rec", allow_site=True)
logger.setLevel(logging.INFO)

BANK_MAPPING_FIELD_ORDER = [
    "date",
    "deposit",
    "withdrawal",
    "description",
    "reference_number",
    "custom_particulars",
    "custom_code",
    "bank_party_name",
]


class BankStatementImporter(Document):
    pass


def read_content(content, extension):
    if extension not in ("csv", "xlsx", "xls"):
        frappe.throw(
            _("Import template should be of type .csv, .xlsx or .xls"),
            title="Template Error",
        )

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
        frappe.throw(
            _("Bank Account '{0}' does not exist").format(bank_account),
            title="Validation Error",
        )

    file_content = None
    file_name = frappe.db.get_value("File", {"file_url": file_path})
    if file_name:
        extn = os.path.splitext(file_path)[1][1:]
        file = frappe.get_doc("File", file_name)
        file_content = file.get_content()
        data = read_content(file_content, extn)
        data_headers = data[0]
        data_body = data[1:]

    bank_mapping = {}
    bank_doc = frappe.get_doc("Bank Account", bank_account)

    # Validate that bank account is linked to a bank
    if bank_doc.bank:
        try:
            bank = frappe.get_doc("Bank", bank_doc.bank)

            # Safely get bank transaction mapping if it exists
            if (
                hasattr(bank, "bank_transaction_mapping")
                and bank.bank_transaction_mapping
            ):
                # Get bank transaction mapping - swap key and value
                for mapping in bank.bank_transaction_mapping:
                    if hasattr(mapping, "bank_transaction_field") and hasattr(
                        mapping, "file_field"
                    ):
                        bank_mapping[mapping.bank_transaction_field] = (
                            mapping.file_field
                        )

            # Safely get date format with fallback
            date_format = "Auto"  # Default fallback
            if (
                hasattr(bank, "bank_statement_date_format")
                and bank.bank_statement_date_format
            ):
                date_format = bank.bank_statement_date_format
            bank_mapping["date_format"] = date_format

        except frappe.DoesNotExistError:
            frappe.throw(
                _("Bank '{0}' linked to Bank Account '{1}' does not exist").format(
                    bank_doc.bank, bank_account
                ),
                title="Validation Error",
            )
    else:
        # Bank account not linked to any bank - use default date format
        bank_mapping["date_format"] = "Auto"
        frappe.msgprint(
            _(
                "Bank Account '{0}' is not linked to any Bank. Using default settings."
            ).format(bank_account),
            title="Warning",
        )

    return {"header": data_headers, "body": data_body, "bank_mapping": bank_mapping}


def parse_amount(amount_str):
    """Parse amount string using frappe's flt() which handles comma separators"""
    if not amount_str or amount_str == "":
        return 0.0

    # Use frappe's built-in flt() which handles commas, whitespace, and formatting
    result = flt(amount_str)

    # Validate that non-zero strings don't parse to zero (indicates invalid format)
    if (
        result == 0.0
        and amount_str
        and str(amount_str).strip() not in ("0", "0.0", "0.00", "-", "")
    ):
        logger.error("Failed to parse amount '%s'", amount_str)
        frappe.throw(
            _("Could not parse amount '{0}'. Please check your CSV format.").format(
                amount_str
            )
        )

    return result


def parse_json_if_required(data):
    if isinstance(data, str):
        value = data.strip()
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse JSON from importer data: %s", value[:200])
            return {}

    if isinstance(data, dict):
        return data

    return {}


def is_truthy(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value == 1

    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def get_selected_bank_mapping(importer_data):
    selected_mapping = {}

    if importer_data.get("date_select"):
        selected_mapping["date"] = importer_data.get("date_select")

    if is_truthy(importer_data.get("same_amount_field")):
        amount_field = importer_data.get("amount_select")
        if amount_field:
            selected_mapping["deposit"] = amount_field
            selected_mapping["withdrawal"] = amount_field
    else:
        if importer_data.get("deposit_select"):
            selected_mapping["deposit"] = importer_data.get("deposit_select")
        if importer_data.get("withdrawal_select"):
            selected_mapping["withdrawal"] = importer_data.get("withdrawal_select")

    if importer_data.get("description_select"):
        selected_mapping["description"] = importer_data.get("description_select")

    if importer_data.get("reference_number_select"):
        selected_mapping["reference_number"] = importer_data.get("reference_number_select")

    if importer_data.get("particulars_select"):
        selected_mapping["custom_particulars"] = importer_data.get("particulars_select")

    if importer_data.get("code_select"):
        selected_mapping["custom_code"] = importer_data.get("code_select")

    if importer_data.get("other_party_select"):
        selected_mapping["bank_party_name"] = importer_data.get("other_party_select")

    return selected_mapping


def save_bank_mapping_for_future_use(importer_data):
    bank_account = importer_data.get("bank_account")
    if not bank_account:
        frappe.msgprint(
            _("Could not save field mapping: no Bank Account was specified."),
            title=_("Warning"),
            indicator="orange",
        )
        return

    bank_account_doc = frappe.get_doc("Bank Account", bank_account)
    if not bank_account_doc.bank:
        frappe.msgprint(
            _(
                "Could not save field mapping because Bank Account '{0}' is not linked to a Bank."
            ).format(bank_account),
            title=_("Warning"),
            indicator="orange",
        )
        return

    bank = frappe.get_doc("Bank", bank_account_doc.bank)
    selected_mapping = get_selected_bank_mapping(importer_data)

    if hasattr(bank, "bank_transaction_mapping"):
        bank.bank_transaction_mapping = [
            row
            for row in bank.bank_transaction_mapping
            if row.bank_transaction_field not in BANK_MAPPING_FIELD_ORDER
        ]

        for fieldname in BANK_MAPPING_FIELD_ORDER:
            file_field = selected_mapping.get(fieldname)
            if file_field:
                bank.append(
                    "bank_transaction_mapping",
                    {"bank_transaction_field": fieldname, "file_field": file_field},
                )

    if importer_data.get("date_format"):
        bank.bank_statement_date_format = importer_data.get("date_format")

    bank.save(ignore_permissions=True)


def build_table(mapping, data_headers, data_body):
    tbl = []
    tbl_header = [
        "Date",
        "Deposit",
        "Withdrawal",
        "Description",
        "Reference Number",
        "Bank Account",
        "Currency",
        "Is Duplicated",
        "Particulars",
        "Code",
        "Other Party",
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
        if mapping["same_amount_field"] == True:
            val = parse_amount(data_row[data_headers.index(mapping["amount_select"])])
            if val >= 0:
                tbl_row.append(
                    abs(val) if mapping["positive_field"] == "Deposit" else 0
                )
                tbl_row.append(
                    abs(val) if mapping["positive_field"] == "Withdrawal" else 0
                )
            else:
                tbl_row.append(
                    abs(val) if mapping["positive_field"] == "Withdrawal" else 0
                )
                tbl_row.append(
                    abs(val) if mapping["positive_field"] == "Deposit" else 0
                )
        else:
            tbl_row.append(
                parse_amount(data_row[data_headers.index(mapping["deposit_select"])])
            )
            tbl_row.append(
                parse_amount(data_row[data_headers.index(mapping["withdrawal_select"])])
            )
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

        # Particulars
        particulars_value = ""
        if (
            mapping.get("particulars_select")
            and mapping["particulars_select"] in data_headers
        ):
            particulars_value = (
                data_row[data_headers.index(mapping["particulars_select"])] or ""
            )
        tbl_row.append(particulars_value)

        # Code
        code_value = ""
        if mapping.get("code_select") and mapping["code_select"] in data_headers:
            code_value = data_row[data_headers.index(mapping["code_select"])] or ""
        tbl_row.append(code_value)

        # Other Party
        other_party_value = ""
        if (
            mapping.get("other_party_select")
            and mapping["other_party_select"] in data_headers
        ):
            other_party_value = (
                data_row[data_headers.index(mapping["other_party_select"])] or ""
            )
        tbl_row.append(other_party_value)

        tbl.append(tbl_row)

    return tbl


def parse_date(date_str, format):
    if not date_str:
        return None
    if format == "Auto":
        return getdate(date_str)

    # Define format patterns mapping
    format_patterns = {
        # Slash-separated
        "Y/m/d": "%Y/%m/%d",
        "d/m/Y": "%d/%m/%Y",
        "dd/mm/YY": "%d/%m/%y",
        "m/d/Y": "%m/%d/%Y",
        "m/d/YY": "%m/%d/%y",
        "Y/d/m": "%Y/%d/%m",

        # Dash-separated
        "m-d-Y": "%m-%d-%Y",
        "m-d-YY": "%m-%d-%y",
        "d-m-Y": "%d-%m-%Y",
        "d-m-YY": "%d-%m-%y",
        "Y-m-d": "%Y-%m-%d",

        # Dot-separated
        "d.m.Y": "%d.%m.%Y",
        "d.m.YY": "%d.%m.%y",
        "Y.m.d": "%Y.%m.%d",
        "m.d.Y": "%m.%d.%Y",
        "m.d.YY": "%m.%d.%y",
    }

    # Try to parse with specified format
    pattern = format_patterns.get(format)
    if pattern:
        try:
            return datetime.strptime(str(date_str), pattern).date()
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse date '%s' with format '%s': %s",
                date_str,
                format,
                str(e),
            )
            pass

    # Fallback to auto detection
    try:
        return getdate(date_str)
    except (ValueError, TypeError) as e:
        logger.error(
            "Failed to parse date '%s' with auto detection: %s", date_str, str(e)
        )
        return None


@frappe.whitelist()
def form_start_import(data_import, bank_account):
    out = start_import(data_import, bank_account)
    return out


@frappe.whitelist()
def map_fields(data, data_headers, data_body):
    out = build_table(json.loads(data), json.loads(data_headers), json.loads(data_body))
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
def publish_records(data_import, importer_data=None):
    import_success = False
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
                "description": str(item[3]) if item[3] else None,
            }

            particulars = item[8] if len(item) > 8 else None
            code = None
            other_party = None

            # New dataset format has: [.., is_duplicated, particulars, code, other_party]
            if len(item) > 10:
                code = item[9]
                other_party = item[10]
            # Legacy dataset format has: [.., is_duplicated, particulars, other_party]
            elif len(item) > 9:
                other_party = item[9]

            if particulars:
                bank_transaction_dict["custom_particulars"] = str(particulars)

            if code:
                bank_transaction_dict["custom_code"] = str(code)

            if other_party:
                bank_transaction_dict["bank_party_name"] = str(other_party)

            bank_transaction = frappe.new_doc("Bank Transaction")
            bank_transaction.update(bank_transaction_dict)
            bank_transaction.insert()
            bank_transaction.submit()
        logger.info("Bank transactions submitted successfully")
        import_success = True
    except Exception as e:
        logger.error("Publish records error: %s", str(e), exc_info=True)
        frappe.db.rollback()

    # Save bank mapping independently of import outcome
    parsed_importer_data = parse_json_if_required(importer_data)
    if is_truthy(parsed_importer_data.get("save_mapping_for_future_use")):
        try:
            save_bank_mapping_for_future_use(parsed_importer_data)
        except Exception as e:
            logger.error("Failed to save bank mapping: %s", str(e), exc_info=True)
            frappe.msgprint(
                _("Saving the field mapping for future use failed: {0}").format(str(e)),
                title=_("Warning"),
                indicator="orange",
            )

    return import_success
