# Copyright (c) 2026, HighFlyer and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ABRBankRuleCondition(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        condition: DF.Literal[
            "",
            "Equals",
            "Not Equals",
            "Greater than",
            "Greater than or Equals",
            "Less Than",
            "Less Than or Equals",
            "Contains",
            "Not Contains",
        ]
        field_name: DF.Literal[
            "",
            "Deposit",
            "Withdrawal",
            "Currency",
            "Description",
            "Reference Number",
            "Particulars",
            "Party Name",
            "Code",
        ]
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        value: DF.Data | None
    # end: auto-generated types

    pass
