// Copyright (c) 2025, HighFlyer and contributors
// For license information, please see license.txt

const partyCompanyFields = {
	customer_company_field: "Customer",
	supplier_company_field: "Supplier",
	employee_company_field: "Employee",
};

frappe.ui.form.on("Advance Bank Reconciliation Settings", {
	async refresh(frm) {
		for (const [fieldname, partyType] of Object.entries(partyCompanyFields)) {
			const { message = [] } = await frappe.call({
				method: "advanced_bank_reconciliation.api.party_company.get_company_link_fields",
				args: { party_type: partyType },
			});
			frm.fields_dict[fieldname].set_data(
				message.map((row) => ({
					label: `${row.label} (${row.fieldname})`,
					value: row.fieldname,
				}))
			);
		}
	},
});
