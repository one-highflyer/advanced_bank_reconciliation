frappe.provide("nexwave.accounts.bank_reconciliation");

nexwave.accounts.bank_reconciliation.DialogManager = class DialogManager {
	constructor(
		company,
		bank_account,
		bank_statement_from_date,
		bank_statement_to_date,
		filter_by_reference_date,
		from_reference_date,
		to_reference_date
	) {
		this.bank_account = bank_account;
		this.company = company;
		this.make_dialog();
		this.bank_statement_from_date = bank_statement_from_date;
		this.bank_statement_to_date = bank_statement_to_date;
		console.log("bank statement date", bank_statement_from_date, bank_statement_to_date);
		this.from_date = bank_statement_from_date;
		this.to_date = bank_statement_to_date;
		this.filter_by_reference_date = filter_by_reference_date;
		this.from_reference_date = from_reference_date;
		this.to_reference_date = to_reference_date;
	}
	show_dialog(bank_transaction_name, update_dt_cards) {
		this.bank_transaction_name = bank_transaction_name;
		this.update_dt_cards = update_dt_cards;
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Bank Transaction",
				filters: { name: this.bank_transaction_name },
				fieldname: [
					"date",
					"deposit",
					"withdrawal",
					"currency",
					"description",
					"name",
					"bank_account",
					"company",
					"reference_number",
					"party_type",
					"party",
					"unallocated_amount",
					"allocated_amount",
					"transaction_type",
				],
			},
			callback: (r) => {
				if (r.message) {
					this.bank_transaction = r.message;
					r.message.payment_entry = 1;
					r.message.journal_entry = 1;
					this.dialog.set_values(r.message);
					this.copy_data_to_voucher();
					this.dialog.show();
					const me = this;
					setTimeout(() => {
						me.update_options();
					}, 300);
				}
			},
		});
	}

	copy_data_to_voucher() {
		let copied = {
			reference_number: this.bank_transaction.reference_number || this.bank_transaction.description,
			posting_date: this.bank_transaction.date,
			reference_date: this.bank_transaction.date,
			mode_of_payment: this.bank_transaction.transaction_type,
		};
		this.dialog.set_values(copied);
	}

	get_linked_vouchers(document_types) {
		if (!this.bank_transaction_name) {
			console.log("Bank Transaction Name not found. Skip getting linked vouchers.");
			return;
		}

		console.log("get_linked_payments", this.bank_transaction_name, document_types, this.from_date, this.to_date, this.filter_by_reference_date, this.from_reference_date, this.to_reference_date);
		frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_linked_payments",
			// method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_linked_payments",
			args: {
				bank_transaction_name: this.bank_transaction_name,
				document_types: document_types,
				from_date: this.from_date,
				to_date: this.to_date,
				filter_by_reference_date: this.filter_by_reference_date,
				from_reference_date: this.from_reference_date,
				to_reference_date: this.to_reference_date,
			},

			callback: (result) => {
				console.log("get payment entries result", result.message.length);
				const data = result.message;

				if (data && data.length > 0) {
					this.vouchers = data;
					const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
					proposals_wrapper.show();
					this.dialog.fields_dict.no_matching_vouchers.$wrapper.hide();
					this.data = [];
					data.forEach((row) => {
						const reference_date = row[5] ? row[5] : row[8];
						this.data.push([
							row[1],
							row[2],
							reference_date,
							format_currency(row[3], row[9]),
							row[4],
							row[6],
						]);
					});
					this.get_dt_columns();
					this.get_datatable(proposals_wrapper);
				} else {
					const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
					proposals_wrapper.hide();
					this.dialog.fields_dict.no_matching_vouchers.$wrapper.show();
				}
				this.dialog.show();
			},
		});
	}

	show_selected_transactions(transactions) {
		if (!this.bank_transaction) return;

		const transactions_wrapper = this.dialog.fields_dict.selected_transactions.$wrapper;
		if (!transactions.length) {
			transactions_wrapper.hide();
		} else {
			transactions_wrapper.show();
		}

		let total = 0;
		let currency = "";
		for (let i = 0; i < transactions.length; i++) {
			const x = transactions[i];
			total += x[3];
			currency = x[9];
		}
		this.dialog.set_value("allocated_amount", total + this.bank_transaction.allocated_amount);
		this.dialog.set_value("unallocated_amount", this.bank_transaction.unallocated_amount - total);
		transactions_wrapper.html(`
			<div class="text-center pb-2">
				<h5 class="font-bold">Total (${transactions.length} selected): ${format_currency(total, currency)}</h5>
			</div>
		`);
	}

	get_dt_columns() {
		this.columns = [
			{
				name: __("Document Type"),
				editable: false,
				width: 125,
			},
			{
				name: __("Document Name"),
				editable: false,
				width: 150,
				format: (value, row) => {
					return frappe.form.formatters.Link(value, { options: row[2].content });
				},
			},
			{
				name: __("Reference Date"),
				editable: false,
				width: 120,
			},
			{
				name: __("Remaining"),
				editable: false,
				width: 100,
			},
			{
				name: __("Reference Number"),
				editable: false,
				width: 200,
			},
			{
				name: __("Party"),
				editable: false,
				width: 200,
			},
		];
	}

	get_datatable(proposals_wrapper) {
		if (!this.datatable) {
			console.log("Creating data table");
			const datatable_options = {
				columns: this.columns,
				data: this.data,
				dynamicRowHeight: true,
				checkboxColumn: true,
				inlineFilters: true,
				events: {
					onCheckRow: (row) => {
						let selected_map = this.datatable.rowmanager.checkMap;
						let rows = [];
						selected_map.forEach((val, index) => {
							if (val == 1) {
								rows.push(this.vouchers[index]);
							}
						});
						console.log('Selected rows', rows);
						this.show_selected_transactions(rows);
					}
				}
			};
			this.datatable = new frappe.DataTable(proposals_wrapper.get(0), datatable_options);
		} else {
			console.log("Refreshing data table");
			this.datatable.refresh(this.data, this.columns);
			this.datatable.rowmanager.checkMap = [];
		}
	}

	reset_datatable() {
		if (this.datatable) {
			this.datatable.rowmanager.checkMap = [];
		}
	}

	make_dialog() {
		const me = this;
		me.selected_payment = null;

		const fields = [
			{
				label: __("Action"),
				fieldname: "action",
				fieldtype: "Select",
				options: `Match Against Voucher\nCreate Voucher\nUpdate Bank Transaction`,
				default: "Match Against Voucher",
			},
			{
				fieldname: "column_break_4",
				fieldtype: "Column Break",
			},
			{
				label: __("Document Type"),
				fieldname: "document_type",
				fieldtype: "Select",
				options: `Payment Entry\nJournal Entry`,
				default: "Payment Entry",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_1",
				label: __("Filters"),
				depends_on: "eval:doc.action=='Match Against Voucher'",
			},
		];

		frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_doctypes_for_bank_reconciliation",
			callback: (r) => {
				$.each(r.message, (_i, entry) => {
					if (_i % 3 == 0) {
						fields.push({
							fieldtype: "Column Break",
						});
					}
					fields.push({
						fieldtype: "Check",
						label: entry,
						fieldname: frappe.scrub(entry),
						onchange: () => this.update_options(),
					});
				});

				fields.push(...this.get_voucher_fields());

				me.dialog = new frappe.ui.Dialog({
					title: __("Reconcile the Bank Transaction"),
					fields: fields,
					size: "extra-large",
					primary_action: (values) => this.reconciliation_dialog_primary_action(values),
				});
			},
		});
	}

	get_voucher_fields() {
		return [
			{
				fieldtype: "Check",
				label: "Show Only Exact Amount",
				fieldname: "exact_match",
				onchange: () => this.update_options(),
			},
			{
				fieldname: "column_break_5",
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Check",
				label: "Bank Transaction",
				fieldname: "bank_transaction",
				onchange: () => this.update_options(),
			},
			{
				fieldtype: "Date",
				label: "From Date",
				fieldname: "from_date",
				default: this.from_date,
				onchange: (e) => {
					console.log('Date changed', e.target.value);
					this.from_date = frappe.datetime.user_to_str(e.target.value);
					this.update_options()
				},
			},
			{
				fieldtype: "Date",
				label: "To Date",
				fieldname: "from_date",
				default: this.to_date,
				onchange: (e) => {
					console.log('Date changed', e.target.value);
					this.to_date = frappe.datetime.user_to_str(e.target.value);
					this.update_options()
				},
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_1",
				label: __("Select Vouchers to Match"),
				depends_on: "eval:doc.action=='Match Against Voucher'",
			},
			{
				fieldtype: "HTML",
				fieldname: "selected_transactions",
			},
			{
				fieldtype: "HTML",
				fieldname: "payment_proposals",
			},
			{
				fieldtype: "HTML",
				fieldname: "no_matching_vouchers",
				options: __('<div class="text-muted text-center">{0}</div>', [
					__("No Matching Vouchers Found"),
				]),
			},
			{
				fieldtype: "Section Break",
				fieldname: "details",
				label: "Details",
				depends_on: "eval:doc.action!='Match Against Voucher'",
			},
			{
				fieldname: "reference_number",
				fieldtype: "Data",
				label: "Reference Number",
				mandatory_depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				default: "Today",
				fieldname: "posting_date",
				fieldtype: "Date",
				label: "Posting Date",
				reqd: 1,
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "reference_date",
				fieldtype: "Date",
				label: "Cheque/Reference Date",
				mandatory_depends_on: "eval:doc.action=='Create Voucher'",
				depends_on: "eval:doc.action=='Create Voucher'",
				reqd: 1,
			},
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				label: "Mode of Payment",
				options: "Mode of Payment",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "edit_in_full_page",
				fieldtype: "Button",
				label: "Edit in Full Page",
				click: () => {
					this.edit_in_full_page();
				},
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "column_break_7",
				fieldtype: "Column Break",
			},
			{
				default: "Bank Entry",
				fieldname: "journal_entry_type",
				fieldtype: "Select",
				label: "Journal Entry Type",
				options:
					"Journal Entry\nInter Company Journal Entry\nBank Entry\nCash Entry\nCredit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry\nExchange Rate Revaluation\nDeferred Revenue\nDeferred Expense",
				depends_on: "eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
			},
			{
				fieldname: "second_account",
				fieldtype: "Link",
				label: "Account",
				options: "Account",
				depends_on: "eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Journal Entry'",
				get_query: () => {
					return {
						filters: {
							is_group: 0,
							company: this.company,
						},
					};
				},
			},
			{
				fieldname: "party_type",
				fieldtype: "Link",
				label: "Party Type",
				options: "DocType",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' &&  doc.document_type=='Payment Entry'",
				get_query: function () {
					return {
						filters: {
							name: ["in", Object.keys(frappe.boot.party_account_types)],
						},
					};
				},
			},
			{
				fieldname: "party",
				fieldtype: "Dynamic Link",
				label: "Party",
				options: "party_type",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldname: "project",
				fieldtype: "Link",
				label: "Project",
				options: "Project",
				depends_on: "eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldname: "cost_center",
				fieldtype: "Link",
				label: "Cost Center",
				options: "Cost Center",
				depends_on: "eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "details_section",
				label: "Transaction Details",
			},
			{
				fieldname: "date",
				fieldtype: "Date",
				label: "Date",
				read_only: 1,
			},
			{
				fieldname: "deposit",
				fieldtype: "Currency",
				label: "Deposit",
				options: "account_currency",
				read_only: 1,
			},
			{
				fieldname: "withdrawal",
				fieldtype: "Currency",
				label: "Withdrawal",
				options: "account_currency",
				read_only: 1,
			},
			{
				fieldname: "column_break_17",
				fieldtype: "Column Break",
				read_only: 1,
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: "Description",
				read_only: 1,
			},
			{
				fieldname: "allocated_amount",
				fieldtype: "Currency",
				label: "Allocated Amount",
				options: "account_currency",
				read_only: 1,
			},
			{
				fieldname: "unallocated_amount",
				fieldtype: "Currency",
				label: "Unallocated Amount",
				options: "account_currency",
				read_only: 1,
			},
			{
				fieldname: "account_currency",
				fieldtype: "Link",
				label: "Currency",
				options: "Currency",
				read_only: 1,
				hidden: 1,
			},
		];
	}

	get_selected_attributes() {
		let selected_attributes = [];
		this.dialog.$wrapper.find(".checkbox input").each((i, col) => {
			if ($(col).is(":checked")) {
				selected_attributes.push($(col).attr("data-fieldname"));
			}
		});

		return selected_attributes;
	}

	update_options() {
		let selected_attributes = this.get_selected_attributes();
		this.get_linked_vouchers(selected_attributes);
		this.show_selected_transactions([]);
	}

	reconciliation_dialog_primary_action(values) {
		if (values.action == "Match Against Voucher") this.match(values);
		if (values.action == "Create Voucher" && values.document_type == "Payment Entry")
			this.add_payment_entry(values);
		if (values.action == "Create Voucher" && values.document_type == "Journal Entry")
			this.add_journal_entry(values);
		else if (values.action == "Update Bank Transaction") this.update_transaction(values);
	}

	match() {
		var selected_map = this.datatable.rowmanager.checkMap;
		let rows = [];
		let selectedRows = [];
		selected_map.forEach((val, index) => {
			if (val == 1) {
				rows.push(this.datatable.datamanager.rows[index]);
				selectedRows.push(this.vouchers[index]);
			}
		});
		console.log("Selected vouchers", selectedRows);
		
		if (selectedRows.length === 0) {
			frappe.msgprint(__("Please select at least one voucher to match"));
			return;
		}
		
		// Separate unpaid invoices from regular vouchers
		let unpaidInvoices = [];
		let regularVouchers = [];
		
		selectedRows.forEach((x) => {
			if (x[1] === "Unpaid Sales Invoice" || x[1] === "Unpaid Purchase Invoice") {
				unpaidInvoices.push({
					doctype: x[1],
					name: x[2],
					allocated_amount: x[3],
				});
			} else {
				regularVouchers.push({
					payment_doctype: x[1],
					payment_name: x[2],
					amount: x[3],
				});
			}
		});
		
		// Process in sequence: unpaid invoices first, then regular vouchers
		this.processUnpaidInvoices(unpaidInvoices, regularVouchers);
	}
	
	processUnpaidInvoices(unpaidInvoices, regularVouchers) {
		if (unpaidInvoices.length > 0) {
			// First, create payment entries for unpaid invoices
			// Don't auto-reconcile if we have regular vouchers to process too
			let autoReconcile = regularVouchers.length === 0;
			
			frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entries_for_invoices",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					invoices: unpaidInvoices,
					auto_reconcile: autoReconcile
				},
				callback: (response) => {
					console.log("Payment entries created for unpaid invoices");
					
					if (autoReconcile) {
						// Payment entries were created and auto-reconciled, we're done
						const alert_string = __("Payment Entries created and Bank Transaction {0} Matched", [this.bank_transaction.name]);
						frappe.show_alert(alert_string);
						this.update_dt_cards(response.message);
						this.reset_datatable();
						this.dialog.hide();
					} else {
						// Payment entries created but not reconciled, now combine with regular vouchers
						let createdVouchers = response.message.vouchers || [];
						let allVouchers = [...createdVouchers, ...regularVouchers];
						this.reconcileAllVouchers(allVouchers);
					}
				},
				error: (error) => {
					frappe.msgprint(__("Error creating payment entries for unpaid invoices: {0}", [error.message]));
				},
			});
		} else {
			// No unpaid invoices, directly process regular vouchers
			this.processRegularVouchers(regularVouchers, false);
		}
	}
	
	reconcileAllVouchers(vouchers) {
		if (vouchers.length === 0) {
			frappe.msgprint(__("No vouchers to reconcile"));
			return;
		}
		
		frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.reconcile_vouchers",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				vouchers: vouchers,
			},
			callback: (response) => {
				const alert_string = __("Payment Entries created for unpaid invoices and all vouchers matched with Bank Transaction {0}", [this.bank_transaction.name]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.reset_datatable();
				this.dialog.hide();
			},
			error: (error) => {
				frappe.msgprint(__("Error reconciling vouchers: {0}", [error.message]));
			},
		});
	}
	
	processRegularVouchers(regularVouchers, hasProcessedInvoices) {
		if (regularVouchers.length > 0) {
			// Process regular vouchers (Payment Entry, Journal Entry, etc.)
			frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.reconcile_vouchers",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					vouchers: regularVouchers,
				},
				callback: (response) => {
					let alert_string;
					if (hasProcessedInvoices) {
						alert_string = __("Payment Entries created for unpaid invoices and all vouchers matched with Bank Transaction {0}", [this.bank_transaction.name]);
					} else {
						alert_string = __("Bank Transaction {0} Matched", [this.bank_transaction.name]);
					}
					frappe.show_alert(alert_string);
					this.update_dt_cards(response.message);
					this.reset_datatable();
					this.dialog.hide();
				},
				error: (error) => {
					frappe.msgprint(__("Error reconciling regular vouchers: {0}", [error.message]));
				},
			});
		} else if (hasProcessedInvoices) {
			// Only unpaid invoices were processed, no regular vouchers
			const alert_string = __("Payment Entries created and Bank Transaction {0} Matched", [this.bank_transaction.name]);
			frappe.show_alert(alert_string);
			this.reset_datatable();
			this.dialog.hide();
		} else {
			// This shouldn't happen if validation is working correctly
			frappe.msgprint(__("No vouchers selected for reconciliation"));
		}
	}

	add_payment_entry(values) {
		frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entry_bts",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				reference_date: values.reference_date,
				party_type: values.party_type,
				party: values.party,
				posting_date: values.posting_date,
				mode_of_payment: values.mode_of_payment,
				project: values.project,
				cost_center: values.cost_center,
			},
			callback: (response) => {
				const alert_string = __("Bank Transaction {0} added as Payment Entry", [
					this.bank_transaction.name,
				]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	add_journal_entry(values) {
		frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_journal_entry_bts",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				reference_date: values.reference_date,
				party_type: values.party_type,
				party: values.party,
				posting_date: values.posting_date,
				mode_of_payment: values.mode_of_payment,
				entry_type: values.journal_entry_type,
				second_account: values.second_account,
			},
			callback: (response) => {
				const alert_string = __("Bank Transaction {0} added as Journal Entry", [
					this.bank_transaction.name,
				]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	update_transaction(values) {
		frappe.call({
			method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_bank_transaction",
			args: {
				bank_transaction_name: this.bank_transaction.name,
				reference_number: values.reference_number,
				party_type: values.party_type,
				party: values.party,
			},
			callback: (response) => {
				const alert_string = __("Bank Transaction {0} updated", [this.bank_transaction.name]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				this.dialog.hide();
			},
		});
	}

	edit_in_full_page() {
		const values = this.dialog.get_values(true);
		if (values.document_type == "Payment Entry") {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_payment_entry_bts",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					reference_number: values.reference_number,
					reference_date: values.reference_date,
					party_type: values.party_type,
					party: values.party,
					posting_date: values.posting_date,
					mode_of_payment: values.mode_of_payment,
					project: values.project,
					cost_center: values.cost_center,
					allow_edit: true,
				},
				callback: (r) => {
					const doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				},
			});
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_journal_entry_bts",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					reference_number: values.reference_number,
					reference_date: values.reference_date,
					party_type: values.party_type,
					party: values.party,
					posting_date: values.posting_date,
					mode_of_payment: values.mode_of_payment,
					entry_type: values.journal_entry_type,
					second_account: values.second_account,
					allow_edit: true,
				},
				callback: (r) => {
					var doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				},
			});
		}
	}
};
