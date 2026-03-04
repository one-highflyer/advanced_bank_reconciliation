import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from advanced_bank_reconciliation.utils.logger import get_logger

logger = get_logger()


def after_install():
    create_property_setters()


def after_migrate():
    create_property_setters()


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
    """Extend JE Account reference_type options with Customer/Supplier.

    This allows bank rules to store a party reference on non-Receivable/Payable
    accounts (e.g., tracking a customer donation on an income account) without
    triggering ERPNext's party-account-type validation.
    """
    new_types = ["Customer", "Supplier"]

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
