// Copyright (c) 2024, High Flyer and contributors
// For license information, please see license.txt
frappe.provide("nexwave.accounts.bank_reconciliation");

function get_modern_bank_rec_url(frm) {
	const params = new URLSearchParams();
	const add_param = (key, value) => {
		if (value === undefined || value === null || value === "") return;
		params.set(key, value);
	};

	add_param("bank_account", frm.doc.bank_account);
	add_param("from_date", frm.doc.bank_statement_from_date);
	add_param("to_date", frm.doc.bank_statement_to_date);
	add_param("statement_balance", frm.doc.bank_statement_closing_balance);

	const query = params.toString();
	return query ? `/bank-rec/reconcile?${query}` : "/bank-rec/reconcile";
}

function render_modern_bank_rec_prompt(frm) {
	const cards_field = frm.get_field("reconciliation_tool_cards");
	if (!cards_field?.$wrapper?.length) return;

	let $prompt = frm.$wrapper.find(".abr-modern-bank-rec-prompt");
	if (!$prompt.length) {
		$prompt = $(`
			<div class="abr-modern-bank-rec-prompt alert alert-info" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
				<div>
					<div><strong>${__("Try the new Bank Rec")}</strong></div>
					<div class="small text-muted">${__("Use the split-screen reconciliation and bank coding views with the current filters.")}</div>
				</div>
				<a class="btn btn-sm btn-primary" href="/bank-rec/reconcile">${__("Open Bank Rec")}</a>
			</div>
		`);
		$prompt.insertBefore(cards_field.$wrapper);
	}

	$prompt.find("a").attr("href", get_modern_bank_rec_url(frm));
}

frappe.ui.form.on("Advance Bank Reconciliation Tool", {
	setup: function (frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_company_account: 1,
				},
			};
		});
		let no_bank_transactions_text = `<div class="text-muted text-center">${__(
			"No Matching Bank Transactions Found"
		)}</div>`;
		set_field_options("no_bank_transactions", no_bank_transactions_text);
	},

	onload: function (frm) {
		// Set default filter dates
		let today = frappe.datetime.get_today();
		frm.doc.bank_statement_from_date = frappe.datetime.add_months(today, -1);
		frm.doc.bank_statement_to_date = today;
		frm.trigger("bank_account");
		frm.trigger("setup_bulk_reconciliation_styles");
	},

	filter_by_reference_date: function (frm) {
		if (frm.doc.filter_by_reference_date) {
			frm.set_value("bank_statement_from_date", "");
			frm.set_value("bank_statement_to_date", "");
		} else {
			frm.set_value("from_reference_date", "");
			frm.set_value("to_reference_date", "");
		}
	},

	refresh: function (frm) {
		frm.disable_save();
		render_modern_bank_rec_prompt(frm);
		frappe.require("advance-bank-reconciliation-tool.bundle.js", () => frm.trigger("make_reconciliation_tool"));

		frm.add_custom_button(__("Upload Bank Statement"), () => {
			const route = "Bank Statement Importer";
			if (frm.doc.bank_account) {
				frappe.set_route("Form", route, { bank_account: frm.doc.bank_account });
			} else {
				frappe.set_route("Form", route);
			}
		});

		frm.add_custom_button(__("Get Unreconciled Entries"), function () {
			frm.trigger("make_reconciliation_tool");
			frm.trigger("validate_bank_transactions");
		});
		frm.change_custom_button_type("Get Unreconciled Entries", null, "primary");

		frm.add_custom_button(__("Run Bank Rules"), function () {
			if (!frm.doc.bank_account || !frm.doc.bank_statement_from_date || !frm.doc.bank_statement_to_date) {
				frappe.msgprint(__("Please select a bank account and date range first"));
				return;
			}
			frm.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.abr_bank_rule.run_bank_rules",
				args: {
					bank_account: frm.doc.bank_account,
					from_date: frm.doc.bank_statement_from_date,
					to_date: frm.doc.bank_statement_to_date,
				},
				callback: function () {
					frm.refresh();
				},
			});
		}, __("Reconcile"));

		frm.add_custom_button(__("Auto Reconcile"), function () {
			if (!frm.doc.bank_account) {
				frappe.msgprint(__("Please select a bank account first"));
				return;
			}
			frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.auto_reconcile_vouchers",
				args: {
					bank_account: frm.doc.bank_account,
					from_date: frm.doc.bank_statement_from_date,
					to_date: frm.doc.bank_statement_to_date,
					filter_by_reference_date: frm.doc.filter_by_reference_date,
					from_reference_date: frm.doc.from_reference_date,
					to_reference_date: frm.doc.to_reference_date,
				},
				callback: function () {
					frm.refresh();
				},
			});
		}, __("Reconcile"));

		frm.add_custom_button(__("Batch Validate Transactions"), function () {
			frm.trigger("batch_validate_transactions");
		}, __("Validation"));
	},

	bank_account: function (frm) {
		render_modern_bank_rec_prompt(frm);
		frappe.db.get_value("Bank Account", frm.doc.bank_account, "account", (r) => {
			frappe.db.get_value("Account", r.account, "account_currency", (r) => {
				frm.doc.account_currency = r.account_currency;
				frm.trigger("render_chart");
			});
		});
		frm.trigger("get_account_opening_balance");
	},

	bank_statement_from_date: function (frm) {
		render_modern_bank_rec_prompt(frm);
		frm.trigger("get_account_opening_balance");
	},

	bank_statement_to_date: function (frm) {
		render_modern_bank_rec_prompt(frm);
	},

	bank_statement_closing_balance: function (frm) {
		render_modern_bank_rec_prompt(frm);
	},

	make_reconciliation_tool(frm) {
		frm.get_field("reconciliation_tool_cards").$wrapper.empty();
		render_modern_bank_rec_prompt(frm);
		if (frm.doc.bank_account && frm.doc.bank_statement_to_date) {
			frm.trigger("get_cleared_balance").then(() => {
				if (
					frm.doc.bank_account &&
					frm.doc.bank_statement_from_date &&
					frm.doc.bank_statement_to_date
				) {
					frm.trigger("render_chart");
					frm.trigger("render");
					frappe.utils.scroll_to(frm.get_field("reconciliation_tool_cards").$wrapper, true, 30);
				}
			});
		}
	},

	get_account_opening_balance(frm) {
		if (frm.doc.company && frm.doc.bank_account && frm.doc.bank_statement_from_date) {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance",
				args: {
					bank_account: frm.doc.bank_account,
					till_date: frappe.datetime.add_days(frm.doc.bank_statement_from_date, -1),
					company: frm.doc.company,
				},
				callback: (response) => {
					frm.set_value("account_opening_balance", response.message);
				},
			});
		}
	},

	get_cleared_balance(frm) {
		if (frm.doc.company && frm.doc.bank_account && frm.doc.bank_statement_to_date) {
			return frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance",
				args: {
					bank_account: frm.doc.bank_account,
					till_date: frm.doc.bank_statement_to_date,
					company: frm.doc.company,
				},
				callback: (response) => {
					frm.cleared_balance = response.message;
				},
			});
		}
	},

	validate_bank_transactions(frm) {
		if (frm.doc.bank_account && frm.doc.bank_statement_to_date) {
			console.log("Validating bank transactions...");
			frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.validate_bank_transactions",
				args: {
					from_date: frm.doc.bank_statement_from_date,
					to_date: frm.doc.bank_statement_to_date,
					company: frm.doc.company,
					bank_account: frm.doc.bank_account,
				},
				callback: function (r) {
					console.log("Bank transaction validation completed", r);
					// Re-fetch the cleared balance and render cards
					frm.trigger("get_cleared_balance").then(() => {
						frm.trigger("render_chart");
					});
				},
			});
		}
	},


	batch_validate_transactions(frm) {
		if (!frm.doc.bank_account) {
			frappe.msgprint(__("Please select a bank account first"));
			return;
		}

		frappe.confirm(
			__("This will queue background validation jobs for unvalidated transactions in the selected period. Continue?"),
			function () {
				frappe.call({
					method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.batch_validate_unvalidated_transactions",
					args: {
						bank_account: frm.doc.bank_account,
						from_date: frm.doc.bank_statement_from_date,
						to_date: frm.doc.bank_statement_to_date,
						limit: 100,
					},
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __("Batch Validation Started"),
								message: r.message.message,
								indicator: "blue"
							});
							
							// Re-fetch the cleared balance and render cards after validation
							setTimeout(() => {
								frm.trigger("get_cleared_balance").then(() => {
									frm.trigger("render_chart");
								});
							}, 2000); // Wait 2 seconds for background jobs to complete
						} else {
							frappe.msgprint({
								title: __("Error"),
								message: r.message?.error || __("Failed to start batch validation"),
								indicator: "red"
							});
						}
					},
				});
			}
		);
	},
	
	// Add custom CSS for bulk reconciliation progress dialog
	setup_bulk_reconciliation_styles() {
		if (!document.getElementById('bulk-reconciliation-styles')) {
			const style = document.createElement('style');
			style.id = 'bulk-reconciliation-styles';
			style.textContent = `
				.bulk-reconciliation-progress {
					padding: 20px 10px;
				}
				.bulk-reconciliation-progress .progress {
					border-radius: 10px;
					overflow: hidden;
					box-shadow: 0 2px 4px rgba(0,0,0,0.1);
				}
				.bulk-reconciliation-progress .progress-bar {
					background: linear-gradient(90deg, #2490ef 0%, #1a73e8 100%);
					transition: width 0.3s ease;
				}
				.bulk-reconciliation-progress .progress-text {
					font-weight: 600;
					font-size: 13px;
					line-height: 25px;
				}
				.bulk-reconciliation-progress .progress-message {
					font-weight: 500;
					color: #6c757d;
				}
			`;
			document.head.appendChild(style);
		}
	},

	render_chart(frm) {
		frm.cards_manager = new nexwave.accounts.bank_reconciliation.NumberCardManager({
			$reconciliation_tool_cards: frm.get_field("reconciliation_tool_cards").$wrapper,
			bank_statement_closing_balance: frm.doc.bank_statement_closing_balance,
			cleared_balance: frm.cleared_balance,
			currency: frm.doc.account_currency,
		});
	},

	render(frm) {
		if (frm.doc.bank_account) {
			frm.bank_reconciliation_data_table_manager =
				new nexwave.accounts.bank_reconciliation.DataTableManager({
					company: frm.doc.company,
					bank_account: frm.doc.bank_account,
					$reconciliation_tool_dt: frm.get_field("reconciliation_tool_dt").$wrapper,
					$no_bank_transactions: frm.get_field("no_bank_transactions").$wrapper,
					$reconciled_transactions_dt: frm.get_field("reconciled_transactions_dt").$wrapper,
					$no_reconciled_transactions: frm.get_field("no_reconciled_transactions").$wrapper,
					bank_statement_from_date: frm.doc.bank_statement_from_date,
					bank_statement_to_date: frm.doc.bank_statement_to_date,
					filter_by_reference_date: frm.doc.filter_by_reference_date,
					from_reference_date: frm.doc.from_reference_date,
					to_reference_date: frm.doc.to_reference_date,
					bank_statement_closing_balance: frm.doc.bank_statement_closing_balance,
					cards_manager: frm.cards_manager,
				});
		}
	},
});
