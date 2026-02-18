// Copyright (c) 2026, HighFlyer and contributors
// For license information, please see license.txt

frappe.ui.form.on("ABR Bank Rule", {
	refresh(frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
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
});
