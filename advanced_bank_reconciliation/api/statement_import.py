"""Statement import for Bank Rec. Source files remain authoritative at every step."""

import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4
from zipfile import ZipFile

import frappe
import xlrd
from dateutil.parser import parse as parse_auto_date
from frappe import _
from frappe.utils.csvutils import unescape_formula_injection
from frappe.utils.html_utils import sanitize_html
from openpyxl import load_workbook

from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.bank_statement_importer.bank_statement_importer import (
    BANK_MAPPING_FIELD_ORDER,
    get_selected_bank_mapping,
    is_truthy,
)
from advanced_bank_reconciliation.api.permission import assert_bank_account_access
from advanced_bank_reconciliation.utils.logger import get_logger


DATE_FORMATS = {
    "Y/m/d": "%Y/%m/%d",
    "d/m/Y": "%d/%m/%Y",
    "dd/mm/YY": "%d/%m/%y",
    "m/d/Y": "%m/%d/%Y",
    "m/d/YY": "%m/%d/%y",
    "Y/d/m": "%Y/%d/%m",
    "m-d-Y": "%m-%d-%Y",
    "m-d-YY": "%m-%d-%y",
    "d-m-Y": "%d-%m-%Y",
    "d-m-YY": "%d-%m-%y",
    "Y-m-d": "%Y-%m-%d",
    "d.m.Y": "%d.%m.%Y",
    "d.m.YY": "%d.%m.%y",
    "Y.m.d": "%Y.%m.%d",
    "m.d.Y": "%m.%d.%Y",
    "m.d.YY": "%m.%d.%y",
}
FIELD_MAPPING = {
    "date": "date_select",
    "description": "description_select",
    "reference_number": "reference_number_select",
    "custom_particulars": "particulars_select",
    "custom_code": "code_select",
    "bank_party_name": "other_party_select",
}
HEADER_HINTS = {
    "date_select": ("date", "transaction date", "txn date", "posting date"),
    "amount_select": ("amount", "transaction amount"),
    "deposit_select": ("deposit", "deposits", "credit", "credits", "money in"),
    "withdrawal_select": ("withdrawal", "withdrawals", "debit", "debits", "money out"),
    "description_select": ("description", "transaction description", "details", "memo"),
    "reference_number_select": (
        "reference number",
        "reference",
        "ref",
        "transaction reference",
    ),
    "particulars_select": ("particulars",),
    "code_select": ("code",),
    "other_party_select": ("other party", "payee", "counterparty", "party name"),
}
TEXT_FIELDS = (
    "description",
    "reference_number",
    "custom_particulars",
    "custom_code",
    "bank_party_name",
)
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_XLSX_BYTES = 32 * 1024 * 1024
MAX_XLSX_MEMBERS = 1000
MAX_ROWS = 20_001  # Includes the header.
MAX_COLUMNS = 256
MAX_CELLS = 500_000
CSV_ENCODINGS = {
    "utf-8": "utf-8-sig",
    "windows-1252": "windows-1252",
    "windows-1250": "windows-1250",
}


class _SourceRow(list):
    def __init__(self, values, source_row):
        super().__init__(values)
        self.source_row = source_row


def _check_dimensions(rows, columns):
    if rows > MAX_ROWS or columns > MAX_COLUMNS or rows * columns > MAX_CELLS:
        _fail(
            "The statement has too many rows or columns. Split it into smaller files."
        )


def _read_csv_rows(content, csv_encoding):
    if not isinstance(csv_encoding, str) or csv_encoding not in CSV_ENCODINGS:
        _fail("The CSV encoding is not supported.")
    try:
        decoded = content.decode(CSV_ENCODINGS[csv_encoding])
    except UnicodeDecodeError:
        _fail(
            "This CSV cannot be read with the selected encoding. Choose a different CSV encoding."
        )
    reader = csv.reader(io.StringIO(decoded, newline=""))
    start_line = 1
    for row in reader:
        _check_dimensions(1, len(row))
        yield _SourceRow(
            [unescape_formula_injection(value.strip()) or None for value in row],
            start_line,
        )
        start_line = reader.line_num + 1


def _read_excel_rows(content, extension):
    if extension == "xls":
        with xlrd.open_workbook(
            file_contents=content, on_demand=True, ragged_rows=True
        ) as book:
            sheet = book.sheet_by_index(0)
            _check_dimensions(sheet.nrows, sheet.ncols)
            for index in range(sheet.nrows):
                yield [
                    xlrd.xldate_as_datetime(cell.value, book.datemode)
                    if cell.ctype == xlrd.XL_CELL_DATE
                    else cell.value
                    for cell in sheet.row(index)
                ]
        return

    with ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if (
            len(members) > MAX_XLSX_MEMBERS
            or sum(member.file_size for member in members) > MAX_XLSX_BYTES
        ):
            _fail(
                "The spreadsheet is too large after decompression. Split it into smaller files."
            )
    workbook = load_workbook(
        io.BytesIO(content), data_only=True, read_only=True, keep_links=False
    )
    try:
        sheet = workbook.active
        _check_dimensions(sheet.max_row or 0, sheet.max_column or 0)
        # Check the actual rows even if the workbook declares smaller dimensions.
        sheet.reset_dimensions()
        yield from sheet.iter_rows(values_only=True)
    finally:
        workbook.close()


def _read_content(content, extension, csv_encoding):
    source = (
        _read_csv_rows(content, csv_encoding)
        if extension == "csv"
        else _read_excel_rows(content, extension)
    )
    rows = []
    width = 0
    text_length = 0
    try:
        for row in source:
            width = max(width, len(row))
            _check_dimensions(len(rows) + 1, width)
            text_length += sum(len(cell) for cell in row if isinstance(cell, str))
            if text_length > MAX_FILE_BYTES:
                _fail(
                    "The statement contains too much text. Split it into smaller files."
                )
            rows.append(row)
    finally:
        source.close()
    return rows


def _fail(message):
    frappe.throw(_(message), title=_("Statement Import"))


def _json_value(value, label, expected):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            _fail("{0} is not valid JSON.".format(label))
    if not isinstance(value, expected):
        _fail("{0} has an invalid format.".format(label))
    return value


def _text(value):
    return "" if value is None else str(value).strip()


def _account_context(bank_account, *, for_update=False):
    doc = assert_bank_account_access(bank_account, for_update=for_update)
    frappe.has_permission("Bank Transaction", "read", throw=True)
    if not doc.account:
        _fail(
            "Link a ledger account to this Bank Account before you import a statement."
        )
    account = frappe.db.get_value(
        "Account",
        doc.account,
        ["company", "account_currency"],
        as_dict=True,
        for_update=for_update,
    )
    if not account or account.company != doc.company or not account.account_currency:
        _fail(
            "The Bank Account needs a ledger account and currency in the same company."
        )
    return doc, account.account_currency, bool(doc.get("is_credit_card"))


def _account_revision(doc, currency, is_credit_card):
    fields = [doc.name, doc.company, doc.account, doc.bank, currency, is_credit_card]
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()


def _bank_mapping(bank_account_doc):
    if not bank_account_doc.bank:
        return None, {"date_format": "Auto"}
    bank = frappe.get_doc("Bank", bank_account_doc.bank)
    frappe.has_permission("Bank", "read", doc=bank, throw=True)
    mapping = {
        row.bank_transaction_field: row.file_field
        for row in (bank.get("bank_transaction_mapping") or [])
        if row.bank_transaction_field and row.file_field
    }
    mapping["date_format"] = bank.get("bank_statement_date_format") or "Auto"
    return bank, mapping


def _read_statement(file_id, csv_encoding="utf-8"):
    if not isinstance(file_id, str) or not file_id:
        _fail("Select an uploaded statement file.")
    try:
        doc = frappe.get_doc("File", file_id)
    except frappe.DoesNotExistError:
        _fail("The uploaded file was not found. Upload the statement again.")
    frappe.has_permission("File", "read", doc=doc, throw=True)
    file_url = doc.file_url
    if (
        doc.is_remote_file
        or doc.is_folder
        or not isinstance(file_url, str)
        or not file_url
    ):
        _fail("Select a local uploaded statement file.")
    url = urlsplit(file_url)
    decoded = unquote(url.path)
    if (
        url.scheme
        or url.netloc
        or url.query
        or url.fragment
        or not decoded.startswith(("/files/", "/private/files/"))
        or "\\" in decoded
        or "\x00" in decoded
        or any(part in (".", "..") for part in decoded.split("/"))
    ):
        _fail("Select a local uploaded statement file.")
    extension = Path(decoded).suffix.lower().lstrip(".")
    if extension not in ("csv", "xlsx", "xls"):
        _fail("Use a CSV, XLSX, or XLS statement file.")
    root = Path(
        frappe.get_site_path(
            "private" if decoded.startswith("/private/") else "public", "files"
        )
    ).resolve()
    path = Path(doc.get_full_path()).resolve()
    if root not in path.parents or not path.is_file():
        _fail(
            "The uploaded file is missing or is outside the upload folder. Upload it again."
        )
    try:
        with path.open("rb") as uploaded:
            content = uploaded.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            _fail("The statement exceeds 10 MB. Split it into smaller files.")
        data = _read_content(content, extension, csv_encoding)
    except frappe.ValidationError:
        raise
    except Exception:
        _fail(
            "The statement file could not be read. Check its file format and upload it again."
        )
    if not data or not data[0]:
        _fail("The statement file needs a header row.")
    headers = [_text(cell).lstrip("\ufeff") for cell in data[0]]
    if not any(headers):
        _fail("The statement file needs a header row.")
    if any(count > 1 for header, count in Counter(headers).items() if header):
        _fail(
            "The statement has repeated column headers. Give each column a unique name and upload it again."
        )
    digest = hashlib.sha256()
    if extension == "csv":
        # The preview and retry must use the same encoding as the import.
        digest.update(f"csv:{csv_encoding}\0".encode())
    digest.update(content)
    return headers, data[1:], digest.hexdigest()


def _default_mapping(headers, saved):
    mapping = {key: "" for key in HEADER_HINTS}
    mapping.update(
        date_format=saved.get("date_format") or "Auto",
        same_amount_field=False,
        positive_field="Deposit",
        save_mapping_for_future_use=False,
    )
    stale = []
    for field, key in FIELD_MAPPING.items():
        mapping[key] = saved.get(field) or ""
    deposit, withdrawal = saved.get("deposit"), saved.get("withdrawal")
    if deposit and deposit == withdrawal:
        mapping.update(same_amount_field=True, amount_select=deposit)
    else:
        mapping.update(deposit_select=deposit or "", withdrawal_select=withdrawal or "")
    for key in HEADER_HINTS:
        value = mapping[key]
        if value and value not in headers:
            stale.append(value)
            mapping[key] = ""
    if mapping["date_format"] not in ("Auto", *DATE_FORMATS):
        stale.append(mapping["date_format"])
        mapping["date_format"] = "Auto"
    # Saved selections are never silently replaced with a different column.
    if not any(saved.get(field) for field in BANK_MAPPING_FIELD_ORDER):
        for key, hints in HEADER_HINTS.items():
            mapping[key] = next(
                (
                    header
                    for hint in hints
                    for header in headers
                    if header.casefold() == hint
                ),
                "",
            )
        mapping["same_amount_field"] = bool(
            mapping["amount_select"]
            and not (mapping["deposit_select"] and mapping["withdrawal_select"])
        )
    return mapping, list(dict.fromkeys(stale))


def _validate_mapping(mapping, headers):
    mapping = _json_value(mapping, "Column mapping", dict)
    result = {key: _text(mapping.get(key)) for key in HEADER_HINTS}
    result.update(
        date_format=_text(mapping.get("date_format")) or "Auto",
        same_amount_field=is_truthy(mapping.get("same_amount_field")),
        positive_field=_text(mapping.get("positive_field")),
        save_mapping_for_future_use=is_truthy(
            mapping.get("save_mapping_for_future_use")
        ),
    )
    if result["date_format"] not in ("Auto", *DATE_FORMATS):
        _fail("Select a supported date format.")
    required = ["date_select", "description_select", "reference_number_select"]
    if result["same_amount_field"]:
        required.append("amount_select")
        if result["positive_field"] not in ("Deposit", "Withdrawal"):
            _fail("Select whether positive amounts are deposits or withdrawals.")
    else:
        required.extend(("deposit_select", "withdrawal_select"))
        if (
            result["deposit_select"] == result["withdrawal_select"]
            and result["deposit_select"]
        ):
            _fail("Use the signed amount option when both amounts use the same column.")
    for key in HEADER_HINTS:
        if key in required and not result[key]:
            _fail(
                "Select all required columns: Date, Description, Reference, and Amounts."
            )
        if result[key] and result[key] not in headers:
            _fail("A selected column is not in this file. Check the column mapping.")
    return result


def _parse_date(value, date_format):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Date is missing or invalid.")
    try:
        if date_format == "Auto":
            # Missing date parts must not depend on the day the user imports the file.
            parsed = parse_auto_date(value.strip(), default=datetime(2000, 1, 1)).date()
            if (
                parsed
                != parse_auto_date(value.strip(), default=datetime(2001, 2, 2)).date()
            ):
                raise ValueError
        else:
            parsed = datetime.strptime(value.strip(), DATE_FORMATS[date_format]).date()
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Date does not match the selected format.") from None
    if not parsed:
        raise ValueError("Date is missing or invalid.")
    return parsed.isoformat()


def _parse_amount(value):
    if value is None or _text(value) in ("", "-"):
        return 0.0
    if isinstance(value, bool):
        raise ValueError("Amount is not a valid number.")
    is_number = isinstance(value, (int, float, Decimal))
    value = _text(value)
    if not is_number and not re.fullmatch(
        r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)", value
    ):
        raise ValueError("Amount is not a valid number.")
    try:
        amount = Decimal(value.replace(",", ""))
        result = float(amount)
    except (InvalidOperation, OverflowError):
        raise ValueError("Amount is not a valid number.") from None
    if (
        not amount.is_finite()
        or not math.isfinite(result)
        or abs(amount) >= Decimal("1000000000000")
    ):
        raise ValueError("Amount is outside the supported range.")
    if amount != amount.quantize(Decimal("0.000000001")):
        raise ValueError("Amount has more than nine decimal places.")
    if Decimal(str(result)) != amount:
        raise ValueError("Amount cannot be represented without losing precision.")
    return result


def _fingerprint(row):
    return (
        _text(row.get("date"))[:10],
        Decimal(str(row.get("deposit") or 0)),
        Decimal(str(row.get("withdrawal") or 0)),
        _text(row.get("description")),
        _text(row.get("reference_number")),
    )


def _amount_precisions(bank_doc, currency):
    transaction = frappe.new_doc("Bank Transaction")
    transaction.update(
        dict(bank_account=bank_doc.name, company=bank_doc.company, currency=currency)
    )
    unallocated_precision = transaction.precision("unallocated_amount")
    return {
        field: min(9, transaction.precision(field), unallocated_precision)
        for field in ("deposit", "withdrawal")
    }


def _build_preview(
    bank_doc,
    currency,
    is_credit_card,
    headers,
    source,
    mapping,
    file_hash,
    current=False,
):
    columns = {
        key: headers.index(value)
        for key, value in mapping.items()
        if key in HEADER_HINTS and value and value in headers
    }
    precisions = _amount_precisions(bank_doc, currency)
    rows = []
    for source_row, cells in enumerate(source, start=2):
        if not cells or all(cell is None or _text(cell) == "" for cell in cells):
            continue
        source_row = getattr(cells, "source_row", source_row)

        def cell(key):
            index = columns.get(key)
            return cells[index] if index is not None and index < len(cells) else None

        row = dict(
            index=len(rows),
            source_row=source_row,
            date=None,
            raw_date=_text(cell("date_select")),
            deposit=0.0,
            withdrawal=0.0,
            is_duplicate=False,
            errors=[],
        )
        for field in TEXT_FIELDS:
            value = _text(cell(FIELD_MAPPING[field]))
            row[field] = sanitize_html(value) if "<" in value or ">" in value else value
        if len(cells) > len(headers) and any(
            _text(value) for value in cells[len(headers) :]
        ):
            row["errors"].append("The row has values outside the header columns.")
        try:
            row["date"] = _parse_date(cell("date_select"), mapping["date_format"])
        except ValueError as exc:
            row["errors"].append(str(exc))
        try:
            if mapping["same_amount_field"]:
                amount = _parse_amount(cell("amount_select"))
                is_deposit = (amount >= 0) == (mapping["positive_field"] == "Deposit")
                row["deposit" if is_deposit else "withdrawal"] = abs(amount)
            else:
                row["deposit"] = _parse_amount(cell("deposit_select"))
                row["withdrawal"] = _parse_amount(cell("withdrawal_select"))
            if row["deposit"] < 0 or row["withdrawal"] < 0:
                raise ValueError(
                    "Separate deposits and withdrawals must not be negative."
                )
            if bool(row["deposit"]) == bool(row["withdrawal"]):
                raise ValueError("Each row needs one nonzero deposit or withdrawal.")
        except ValueError as exc:
            row["errors"].append(str(exc))
        if is_credit_card:
            row["deposit"], row["withdrawal"] = row["withdrawal"], row["deposit"]
        if not row["errors"]:
            for field, precision in precisions.items():
                value = Decimal(str(row[field]))
                if value != value.quantize(Decimal(1).scaleb(-precision)):
                    row["errors"].append(
                        "Amount has more than {0} decimal places for this Bank Transaction currency.".format(
                            precision
                        )
                    )
        rows.append(row)
    valid = [row for row in rows if not row["errors"]]
    if valid:
        existing = frappe.db.get_values(
            "Bank Transaction",
            filters={
                "bank_account": bank_doc.name,
                "docstatus": ["!=", 2],
                "date": ["in", sorted({row["date"] for row in valid})],
            },
            fieldname=[
                "date",
                "deposit",
                "withdrawal",
                "description",
                "reference_number",
            ],
            as_dict=True,
            for_update=current,
        )
        fingerprints = {_fingerprint(row) for row in existing}
        counts = Counter(_fingerprint(row) for row in valid)
        for row in valid:
            key = _fingerprint(row)
            row["is_duplicate"] = key in fingerprints or counts[key] > 1
    duplicates = sum(row["is_duplicate"] for row in valid)
    return dict(
        rows=rows,
        summary=dict(
            total=len(rows),
            ready=len(valid) - duplicates,
            possible_duplicates=duplicates,
            errors=len(rows) - len(valid),
            money_in=float(
                sum((Decimal(str(row["deposit"])) for row in valid), Decimal(0))
            ),
            money_out=float(
                sum((Decimal(str(row["withdrawal"])) for row in valid), Decimal(0))
            ),
        ),
        currency=currency,
        file_hash=file_hash,
        account_revision=_account_revision(bank_doc, currency, is_credit_card),
        amount_precision=precisions,
    )


@frappe.whitelist(methods=["POST"])
def get_import_context(bank_account):
    doc, currency, credit_card = _account_context(bank_account)
    bank, mapping = _bank_mapping(doc)
    last = frappe.get_list(
        "Bank Transaction",
        filters={"bank_account": doc.name, "docstatus": 1},
        fields=["name", "date", "deposit", "withdrawal", "description"],
        order_by="date desc, creation desc",
        page_length=1,
    )
    return dict(
        bank_account=dict(
            name=doc.name,
            account_name=doc.account_name,
            account=doc.account,
            company=doc.company,
            bank=doc.bank,
            currency=currency,
        ),
        bank=doc.bank or None,
        currency=currency,
        is_credit_card=credit_card,
        last_transaction=last[0] if last else None,
        bank_mapping=mapping,
        can_save_mapping=bool(
            bank and frappe.has_permission("Bank", "write", doc=bank)
        ),
    )


@frappe.whitelist(methods=["POST"])
def prepare_statement(bank_account, file_id, csv_encoding="utf-8"):
    doc, _, _ = _account_context(bank_account)
    headers, source, _ = _read_statement(file_id, csv_encoding)
    _, saved = _bank_mapping(doc)
    mapping, stale = _default_mapping(headers, saved)
    nonempty = [row for row in source if row and any(_text(cell) for cell in row)]
    return dict(
        headers=headers,
        preview_rows=nonempty[:5],
        row_count=len(nonempty),
        mapping=mapping,
        stale_mappings=stale,
    )


@frappe.whitelist(methods=["POST"])
def preview_statement(bank_account, file_id, mapping, csv_encoding="utf-8"):
    doc, currency, credit_card = _account_context(bank_account)
    headers, source, file_hash = _read_statement(file_id, csv_encoding)
    mapping = _validate_mapping(mapping, headers)
    return _build_preview(
        doc, currency, credit_card, headers, source, mapping, file_hash
    )


def _indices(value, label, total):
    value = _json_value(value, label, list)
    if any(
        type(index) is not int or index < 0 or index >= total for index in value
    ) or len(set(value)) != len(value):
        _fail(
            "{0} contains an invalid or repeated row index. Preview the statement again.".format(
                label
            )
        )
    return sorted(value)


def _mapping_save_state(bank_doc, mapping):
    if not mapping["save_mapping_for_future_use"]:
        return None, []
    bank, _saved_mapping = _bank_mapping(bank_doc)
    if not bank:
        return None, [
            _("The mapping was not saved because this Bank Account has no linked Bank.")
        ]
    if not frappe.has_permission("Bank", "write", doc=bank):
        return None, [
            _(
                "The mapping was not saved because you do not have Bank write permission."
            )
        ]
    warnings = []
    if mapping["same_amount_field"]:
        warnings.append(
            _(
                "The Bank mapping cannot store the positive amount direction. Check that direction on the next import."
            )
        )
    return bank, warnings


def _save_mapping(bank, mapping):
    selected = get_selected_bank_mapping(mapping)
    bank.set(
        "bank_transaction_mapping",
        [
            row
            for row in (bank.get("bank_transaction_mapping") or [])
            if row.bank_transaction_field not in BANK_MAPPING_FIELD_ORDER
        ],
    )
    for field in BANK_MAPPING_FIELD_ORDER:
        if selected.get(field):
            bank.append(
                "bank_transaction_mapping",
                dict(bank_transaction_field=field, file_field=selected[field]),
            )
    bank.bank_statement_date_format = mapping["date_format"]
    bank.save()


def _result(bank_account, rows, total, mapping_saved, warnings, idempotent=False):
    dates = [str(row["date"])[:10] for row in rows]
    return dict(
        bank_account=bank_account,
        imported_count=len(rows),
        unselected_count=total - len(rows),
        from_date=min(dates) if dates else None,
        to_date=max(dates) if dates else None,
        transactions=[
            dict(name=row["name"], date=str(row["date"])[:10]) for row in rows
        ],
        mapping_saved=mapping_saved,
        warnings=warnings,
        idempotent=idempotent,
    )


def _request_prefix(request_id, bank_account):
    if request_id is None:
        return None
    if not isinstance(request_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,128}", request_id
    ):
        _fail("The import request ID is invalid.")
    key = "\0".join((frappe.session.user, bank_account, request_id))
    return "abr-import:" + hashlib.sha256(key.encode()).hexdigest()[:32] + ":"


@frappe.whitelist(methods=["POST"])
def import_statement(
    bank_account,
    file_id,
    mapping,
    selected_rows,
    file_hash,
    account_revision,
    include_duplicates=False,
    request_id=None,
    confirmed_duplicate_rows=None,
    csv_encoding="utf-8",
):
    doc, currency, _ = _account_context(bank_account)
    permission_doc = frappe.new_doc("Bank Transaction")
    permission_doc.update(
        dict(bank_account=doc.name, company=doc.company, currency=currency)
    )
    for permission in ("create", "submit"):
        frappe.has_permission(
            "Bank Transaction", permission, doc=permission_doc, throw=True
        )
    headers, source, actual_hash = _read_statement(file_id, csv_encoding)
    if file_hash != actual_hash:
        _fail(
            "The statement file or CSV encoding has changed. Preview it again before you import."
        )
    # Lock and reload the account before checking the reviewed settings and writing.
    doc, currency, credit_card = _account_context(bank_account, for_update=True)
    if account_revision != _account_revision(doc, currency, credit_card):
        _fail(
            "The bank account settings have changed. Preview the statement again before you import."
        )
    mapping = _validate_mapping(mapping, headers)
    preview = _build_preview(
        doc, currency, credit_card, headers, source, mapping, actual_hash, current=True
    )
    rows = preview["rows"]
    selected = _indices(selected_rows, "Selected rows", len(rows))
    if not selected:
        _fail("Select at least one row to import.")
    confirmed = _indices(
        confirmed_duplicate_rows or [], "Confirmed duplicate rows", len(rows)
    )
    include_duplicates = is_truthy(include_duplicates)
    prefix = _request_prefix(request_id, doc.name)
    payload = dict(
        file_hash=actual_hash,
        mapping=mapping,
        selected=selected,
        include_duplicates=include_duplicates,
        confirmed_duplicate_rows=confirmed,
    )
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[
        :32
    ]
    bank, warnings = _mapping_save_state(doc, mapping)
    if prefix:
        previous = frappe.db.get_values(
            "Bank Transaction",
            filters={
                "bank_account": doc.name,
                "transaction_id": ["like", prefix + "%"],
            },
            fieldname=["name", "date", "docstatus", "transaction_id"],
            as_dict=True,
            for_update=True,
        )
        if previous:
            expected = {str(index) for index in selected}
            parts = [row.transaction_id[len(prefix) :].split(":") for row in previous]
            if (
                len(previous) != len(selected)
                or any(
                    len(part) != 3 or part[0] != digest or part[1] not in ("0", "1")
                    for part in parts
                )
                or {part[2] for part in parts} != expected
                or any(row.docstatus != 1 for row in previous)
            ):
                _fail(
                    "This request ID was used for another import or its transactions have changed. Check the imported transactions."
                )
            previous.sort(key=lambda row: int(row.transaction_id.rsplit(":", 1)[1]))
            return _result(
                doc.name,
                previous,
                len(rows),
                parts[0][1] == "1",
                warnings,
                idempotent=True,
            )
    if preview["summary"]["errors"]:
        _fail(
            "The statement contains invalid rows. Correct all row errors and preview it again."
        )
    duplicates = {index for index in selected if rows[index]["is_duplicate"]}
    if duplicates and not include_duplicates:
        _fail(
            "Selected rows may be duplicates. Review and confirm them before you import."
        )
    if duplicates != set(confirmed) or not set(confirmed).issubset(selected):
        _fail(
            "The possible duplicate rows have changed. Preview and confirm the selected duplicates again."
        )
    savepoint = "statement_import_" + uuid4().hex
    frappe.db.savepoint(savepoint)
    imported = []
    current_row = None
    try:
        if bank:
            _save_mapping(bank, mapping)
        for index in selected:
            current_row = rows[index]
            transaction = frappe.new_doc("Bank Transaction")
            transaction.update(
                {
                    field: current_row[field]
                    for field in ("date", "deposit", "withdrawal", *TEXT_FIELDS)
                }
            )
            transaction.update(
                dict(bank_account=doc.name, company=doc.company, currency=currency)
            )
            if prefix:
                transaction.transaction_id = (
                    f"{prefix}{digest}:{int(bool(bank))}:{index}"
                )
            transaction.insert()
            transaction.submit()
            imported.append(dict(name=transaction.name, date=current_row["date"]))
    except Exception as exc:
        frappe.db.rollback(save_point=savepoint)
        if isinstance(
            exc,
            (frappe.ValidationError, frappe.PermissionError, frappe.DoesNotExistError),
        ):
            raise
        get_logger().exception("Statement import failed for Bank Account %s", doc.name)
        if current_row:
            _fail(
                "Import failed at source row {0}. No rows were imported. Check the statement or contact your administrator.".format(
                    current_row["source_row"]
                )
            )
        _fail(
            "The Bank mapping could not be saved. No rows were imported. Check the Bank settings or contact your administrator."
        )
    finally:
        frappe.db.release_savepoint(savepoint)
    return _result(doc.name, imported, len(rows), bool(bank), warnings)
