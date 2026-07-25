// Copyright (c) 2026, HighFlyer and contributors
// For license information, please see license.txt

frappe.ui.form.on("ABR Bank Rule", {
	refresh(frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_company_account: 1,
					disabled: 0,
				},
			};
		});

		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", ["Customer", "Supplier", "Employee"]],
				},
			};
		});

		frm.set_query("party", () => ({
			query: "advanced_bank_reconciliation.api.party_company.search_parties",
			filters: {
				party_type: frm.doc.party_type,
				company: frm.doc.company,
			},
		}));

		for (const field of ["account", "cost_center"]) {
			frm.set_query(field, function () {
				return {
					filters: {
						company: frm.doc.company,
						is_group: 0,
						disabled: 0,
					},
				};
			});
		}
	},

	company(frm) {
		for (const field of ["bank_account", "account", "cost_center", "party"]) {
			frm.set_value(field, "");
		}
	},

	party_type(frm) {
		frm.set_value("party", "");
	},
});
