import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from advanced_bank_reconciliation.utils.logger import get_logger

logger = get_logger()


def after_install():
    create_abr_custom_fields()
    create_property_setters()
    sync_accounting_dimensions()


def after_migrate():
    create_abr_custom_fields()
    create_property_setters()
    sync_accounting_dimensions()


def create_abr_custom_fields():
    """Create custom fields needed by ABR on other doctypes."""
    try:
        create_custom_fields(get_custom_fields(), ignore_validate=True, update=True)
    except Exception as e:
        logger.error("ABR setup: Failed to create custom fields", exc_info=True)
        frappe.db.rollback()
        frappe.log_error(
            message="Failed to create custom fields during ABR setup.\n\n%s" % e,
            title="ABR Setup: Custom Field Creation Failed",
        )
        frappe.db.commit()
        raise


def get_custom_fields():
    abr_bank_rule_field = {
        "fieldname": "abr_bank_rule",
        "fieldtype": "Link",
        "options": "ABR Bank Rule",
        "label": "ABR Bank Rule",
        "read_only": 1,
        "insert_after": "cheque_no",
        "no_copy": 1,
    }
    return {
        "Journal Entry": [abr_bank_rule_field],
        "Payment Entry": [
            {
                **abr_bank_rule_field,
                "insert_after": "reference_no",
            }
        ],
    }


def sync_accounting_dimensions():
    """Ensure existing accounting dimensions have their fields on ABR Bank Rule.

    When ABR is installed on a site that already has accounting dimensions,
    those dimensions won't have fields on ABR Bank Rule yet (since
    make_dimension_in_accounting_doctypes only runs on dimension creation).
    This function fills that gap on every install/migrate.
    """
    try:
        from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
            get_accounting_dimensions,
            make_dimension_in_accounting_doctypes,
        )
    except ImportError:
        logger.warning(
            "ABR setup: Could not import accounting dimension utilities from ERPNext. "
            "Skipping dimension sync for ABR Bank Rule."
        )
        return

    for fieldname in get_accounting_dimensions():
        dim_doc = frappe.get_doc("Accounting Dimension", {"fieldname": fieldname})
        if not frappe.db.exists(
            "Custom Field", {"dt": "ABR Bank Rule", "fieldname": fieldname}
        ):
            logger.info(
                "ABR setup: Adding accounting dimension '%s' to ABR Bank Rule",
                fieldname,
            )
            make_dimension_in_accounting_doctypes(
                doc=dim_doc, doclist=["ABR Bank Rule"]
            )


def create_property_setters():
    try:
        for ps in get_property_setters():
            make_property_setter(
                doctype=ps["doctype"],
                fieldname=ps["fieldname"],
                property=ps["property"],
                value=ps["value"],
                property_type=ps.get("property_type", "Text"),
                for_doctype=ps.get("for_doctype", False),
                validate_fields_for_doctype=False,
            )
    except Exception as e:
        logger.error("ABR setup: Failed to create property setters", exc_info=True)
        frappe.db.rollback()
        frappe.log_error(
            message="Failed to create property setters during ABR setup.\n\n%s" % e,
            title="ABR Setup: Property Setter Creation Failed",
        )
        frappe.db.commit()
        raise


def get_property_setters():
    property_setters = []

    extended_options = get_extended_reference_type_options()
    if extended_options:
        property_setters.append(
            {
                "doctype": "Journal Entry Account",
                "fieldname": "reference_type",
                "property": "options",
                "value": extended_options,
                "property_type": "Text",
            }
        )

    return property_setters


def get_extended_reference_type_options():
    """Extend JE Account reference_type options with Customer/Supplier/Employee.

    This allows bank rules to store a party reference on non-Receivable/Payable
    accounts (e.g., tracking a customer donation on an income account) without
    triggering ERPNext's party-account-type validation.
    """
    new_types = ["Customer", "Supplier", "Employee"]

    try:
        meta = frappe.get_meta("Journal Entry Account")
    except Exception:
        logger.error(
            "ABR setup: Could not load meta for 'Journal Entry Account'", exc_info=True
        )
        raise

    ref_type_field = meta.get_field("reference_type")

    if not ref_type_field or not ref_type_field.options:
        logger.warning(
            "ABR setup: 'reference_type' field not found or has no options on "
            "'Journal Entry Account'. Cannot extend options for party references."
        )
        return None

    current_options = ref_type_field.options
    options_list = [opt.strip() for opt in current_options.split("\n")]

    if all(t in options_list for t in new_types):
        return None

    for t in new_types:
        if t not in options_list:
            options_list.append(t)

    return "\n".join(options_list)
