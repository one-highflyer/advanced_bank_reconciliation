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
		if (!this.dialog) {
			frappe.msgprint(__("The reconciliation dialog failed to initialize. Please reload the page."));
			return;
		}
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
					"custom_particulars",
					"custom_code",
					"bank_party_name",
				],
			},
			callback: (r) => {
				if (r.message) {
					this.bank_transaction = r.message;
					r.message.payment_entry = 1;
					r.message.journal_entry = 1;
					r.message.bt_reference_number = r.message.reference_number || "";
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

	async get_linked_vouchers(document_types) {
		if (!this.bank_transaction_name) {
			console.log("Bank Transaction Name not found. Skip getting linked vouchers.");
			return;
		}

		console.log("get_linked_payments", this.bank_transaction_name, document_types, this.from_date, this.to_date, this.filter_by_reference_date, this.from_reference_date, this.to_reference_date);
		const result = await frappe.call({
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
		});
		let data = (result && result.message) || [];

		if (data && data.length > 0) {
			data = await this.apply_customer_group_filter(data);
			this.vouchers = data;
			console.log("Applied additional filters. Filtered length: ", data.length);
			this.display_filtered_data(data)
		} else {
			const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
			proposals_wrapper.hide();
			this.dialog.fields_dict.no_matching_vouchers.$wrapper.show();
			this.dialog.show();
		}
	}

	async apply_customer_group_filter(data) {
		const customer_group_filter = this.dialog.get_value('customer_group');

		// Get all unique customers from the data where party_type is 'Customer'
		const customers = [];
		data.forEach((row) => {
			// row[7] is party_type, row[6] is party
			if (row[7] === 'Customer' && row[6] && !customers.includes(row[6])) {
				customers.push(row[6]);
			}
		});

		if (customers.length === 0) {
			// No customer entries, show all data
			return data;
		}

		const additional_customer_fields = {};
		if (this.additional_filters) {
			this.additional_filters
				.filter(fil => fil.dt == "Customer")
				.forEach(fil => {
					const value = this.dialog.get_value(fil.fieldname);
					console.log("Custom filter value", fil.fieldname, value);
					if (value) {
						additional_customer_fields[fil.fieldname] = value;
					}
				});
		}

		// Fetch customer groups for all customers using POST to avoid query parameter limits
		try {
			const r = await frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Customer',
					filters: [['name', 'in', customers]],
					fields: ['name', 'customer_group', ...Object.keys(additional_customer_fields)],
					limit_page_length: 9999
				}
			});
			const response = r.message;
			if (!response || response.length == 0) {
				return data;
			}
			const customers_map = {};
			response.forEach((customer) => {
				customers_map[customer.name] = customer;
			});

			let filtered_data = data;
			if (customer_group_filter) {
				// Filter data based on customer group
				filtered_data = filtered_data.filter((row) => {
					return row[7] == "Customer" && customers_map[row[6]] && customers_map[row[6]].customer_group == customer_group_filter;
				});
				console.log("Applied customer group filter: ", customer_group_filter, filtered_data.length);
			}
			
			console.log("Applying additional customer fields filters", additional_customer_fields);
			for (let additional_filter of Object.keys(additional_customer_fields)) {
				const value = additional_customer_fields[additional_filter];
				filtered_data = filtered_data.filter((row) => {
					return row[7] == "Customer" && customers_map[row[6]] && customers_map[row[6]][additional_filter] == value;
				})
				console.log("Applied additional filter: ", additional_filter, "length: ", filtered_data.length)
			}

			return filtered_data;
		} catch (err) {
			// If there's an error fetching customer groups, show all data
			return data
		}
	}

	display_filtered_data(data) {
		const proposals_wrapper = this.dialog.fields_dict.payment_proposals.$wrapper;
		
		if (data && data.length > 0) {
			proposals_wrapper.show();
			this.dialog.fields_dict.no_matching_vouchers.$wrapper.hide();
			this.data = [];
			data.forEach((row) => {
				const reference_date = row[5] ? row[5] : row[8];
				// Format party display: show party_name (party_code) only when they differ, otherwise show whichever is present
				let party_display;
				if (row[10] && row[6] && row[10] !== row[6]) {
					party_display = `${row[10]} (${row[6]})`;
				} else {
					party_display = row[10] || row[6] || '';
				}
				this.data.push([
					row[1],
					row[2],
					reference_date,
					format_currency(row[3], row[9]),
					row[4],
					party_display,
				]);
			});
			this.get_dt_columns();
			this.get_datatable(proposals_wrapper);
		} else {
			proposals_wrapper.hide();
			this.dialog.fields_dict.no_matching_vouchers.$wrapper.show();
		}
		this.dialog.show();
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
						// Clear any pending timeout
						if (this._checkRowTimeout) {
							clearTimeout(this._checkRowTimeout);
						}

						// Debounce: wait for checkRow events to stop firing
						this._checkRowTimeout = setTimeout(() => {
							let selected_map = this.datatable.rowmanager.checkMap;
							let rows = [];
							selected_map.forEach((val, index) => {
								if (val == 1) {
									const filteredRowData = this.datatable.datamanager.data[index];
									const voucher = this.vouchers.find(v =>
										v[1] === filteredRowData[0] && v[2] === filteredRowData[1]
									);
									if (voucher) {
										rows.push(voucher);
									}
								}
							});
							this.show_selected_transactions(rows);
						}, 100); // Wait 100ms after last checkRow event
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

	async make_dialog() {
		const me = this;
		me.selected_payment = null;

		try {
			const settings_res = await frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_abr_default_settings"
			});
			this.default_settings = (settings_res && settings_res.message) || {};
		} catch (e) {
			console.error("Failed to load ABR default settings", e);
			this.default_settings = {};
		}

		try {
			const dims_res = await frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_accounting_dimensions_for_dialog"
			});
			this.accounting_dimensions = (dims_res && dims_res.message) || [];
		} catch (e) {
			console.error("Failed to load accounting dimensions", e);
			this.accounting_dimensions = [];
		}

		const fields = [
			{
				label: __("Action"),
				fieldname: "action",
				fieldtype: "Select",
				options: `Match Against Voucher\nCreate Voucher\nUpdate Bank Transaction`,
				default: this.default_settings.default_reconciliation_action || "Match Against Voucher",
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
				default: this.default_settings.default_document_type || "Payment Entry",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_1",
				label: __("Filters"),
				depends_on: "eval:doc.action=='Match Against Voucher'",
			},
		];

		try {
			const r = await frappe.call({
				method: "erpnext.accounts.doctype.bank_transaction.bank_transaction.get_doctypes_for_bank_reconciliation"
			});
			$.each((r && r.message) || [], (_i, entry) => {
				if (fields.length % 4 == 0) {
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
		} catch (e) {
			console.error("Failed to load reconciliation doctypes", e);
		}

		try {
			const filters_res = await frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_additional_filters"
			});
			this.additional_filters = (filters_res && filters_res.message) || [];
			$.each(this.additional_filters, (_i, entry) => {
				fields.push({
					fieldtype: entry.fieldtype,
					label: entry.label || entry.fieldname,
					fieldname: entry.fieldname,
					onchange: () => this.update_options()
				})
			});
		} catch (e) {
			console.error("Failed to load additional filters", e);
			this.additional_filters = [];
		}

		fields.push(...this.get_voucher_fields());

		me.dialog = new frappe.ui.Dialog({
			title: __("Reconcile the Bank Transaction"),
			fields: fields,
			size: "extra-large",
			primary_action: (values) => this.reconciliation_dialog_primary_action(values),
		});
	}

	get_voucher_fields() {
		const voucher_fields = [
			{
				fieldtype: "Check",
				label: "Show Only Exact Amount",
				fieldname: "exact_match",
				onchange: () => this.update_options(),
			},
			{
				fieldtype: "Check",
				label: "Bank Transaction",
				fieldname: "bank_transaction",
				onchange: () => this.update_options(),
			},
			{
				fieldname: "column_break_5",
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				label: "Customer Group",
				fieldname: "customer_group",
				options: "Customer Group",
				depends_on: "eval:doc.payment_entry || doc.journal_entry || doc.sales_invoice || doc.unpaid_sales_invoice",
				onchange: () => this.update_options(),
			},
			{
				fieldtype: "Date",
				label: "From Date",
				fieldname: "from_date",
				default: this.from_date,
				onchange: (e) => {
					this.from_date = frappe.datetime.user_to_str(e.target.value);
					this.update_options()
				},
			},
			{
				fieldtype: "Date",
				label: "To Date",
				fieldname: "to_date",
				default: this.to_date,
				onchange: (e) => {
					this.to_date = frappe.datetime.user_to_str(e.target.value);
					this.update_options()
				},
			},
			{
				fieldtype: "Section Break",
				fieldname: "section_break_vouchers",
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
				default: this.default_settings.default_journal_entry_type || "Bank Entry",
				fieldname: "journal_entry_type",
				fieldtype: "Select",
				label: "Journal Entry Type",
				options:
					"Journal Entry\nInter Company Journal Entry\nBank Entry\nCash Entry\nCredit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\nWrite Off Entry\nOpening Entry\nDepreciation Entry\nExchange Rate Revaluation\nDeferred Revenue\nDeferred Expense",
				depends_on: "eval:doc.action=='Create Voucher' && doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Journal Entry'",
			},
			{
				fieldname: "second_account",
				fieldtype: "Link",
				label: "Account",
				options: "Account",
				depends_on: "eval:doc.action=='Create Voucher' && doc.document_type=='Journal Entry'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Journal Entry'",
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
				depends_on: "eval:doc.action=='Create Voucher'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
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
				depends_on: "eval:doc.action=='Create Voucher'",
				mandatory_depends_on:
					"eval:doc.action=='Create Voucher' && doc.document_type=='Payment Entry'",
			},
			{
				fieldname: "project",
				fieldtype: "Link",
				label: "Project",
				options: "Project",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				fieldname: "cost_center",
				fieldtype: "Link",
				label: "Cost Center",
				options: "Cost Center",
				depends_on: "eval:doc.action=='Create Voucher'",
				get_query: () => {
					return {
						filters: {
							is_group: 0,
							company: this.company,
						},
					};
				},
			},
		];

		if (this.accounting_dimensions && this.accounting_dimensions.length) {
			for (const dim of this.accounting_dimensions) {
				const field_def = {
					fieldname: dim.fieldname,
					fieldtype: dim.fieldtype,
					label: dim.label,
					options: dim.options,
					depends_on: "eval:doc.action=='Create Voucher'",
				};
				if (dim.has_company_field) {
					field_def.get_query = () => {
						return {
							filters: {
								company: this.company,
							},
						};
					};
				}
				voucher_fields.push(field_def);
			}
		}

		voucher_fields.push(
			{
				fieldtype: "Section Break",
				fieldname: "save_rule_section",
				depends_on: "eval:doc.action=='Create Voucher'",
			},
			{
				label: __("Save as Bank Rule"),
				fieldname: "save_as_bank_rule",
				fieldtype: "Check",
				default: 0,
				depends_on: "eval:doc.action=='Create Voucher'",
				description: __("Save this allocation as a bank rule for future auto-matching"),
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
			},
			{
				fieldname: "bank_party_name",
				fieldtype: "Data",
				label: "Bank Party",
				read_only: 1,
			},
			{
				fieldname: "bt_reference_number",
				fieldtype: "Data",
				label: "Reference Number",
				read_only: 1,
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: "Description",
				read_only: 1,
			},
			{
				fieldtype: "Section Break",
				fieldname: "details_section_2",
			},
			{
				fieldname: "custom_particulars",
				fieldtype: "Data",
				label: "Particulars",
				read_only: 1,
			},
			{
				fieldname: "custom_code",
				fieldtype: "Data",
				label: "Code",
				read_only: 1,
			},
			{
				fieldname: "column_break_18",
				fieldtype: "Column Break",
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
		);

		return voucher_fields;
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
		if (values.action == "Match Against Voucher") {
			this.match(values);
		} else if (values.action == "Create Voucher" && values.document_type == "Payment Entry") {
			this.add_payment_entry(values);
		} else if (values.action == "Create Voucher" && values.document_type == "Journal Entry") {
			this.add_journal_entry(values);
		} else if (values.action == "Update Bank Transaction") {
			this.update_transaction(values);
		}
	}

	match() {
		var selected_map = this.datatable.rowmanager.checkMap;
		let selectedRows = [];
		selected_map.forEach((val, index) => {
			if (val == 1) {
				const filteredRowData = this.datatable.datamanager.data[index];
				const voucher = this.vouchers.find(v =>
					v[1] === filteredRowData[0] && v[2] === filteredRowData[1]
				);
				if (voucher) {
					selectedRows.push(voucher);
				}
			}
		});

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
		
		// Unified processing: always use background job (small or large)
		this.processUnpaidInvoices(unpaidInvoices, regularVouchers);
	}
	
	processUnpaidInvoices(unpaidInvoices, regularVouchers) {
		const startJob = () => {
			frappe.call({
				method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entries_bulk",
				args: {
					bank_transaction_name: this.bank_transaction.name,
					invoices: unpaidInvoices,
					regular_vouchers: regularVouchers
				},
				callback: (response) => {
					if (response.message) {
						if (response.message.status === "completed") {
							// Synchronous completion - show success and refresh
							frappe.show_alert({
								message: response.message.message || __("Reconciliation completed successfully"),
								indicator: "green"
							}, 10);

							// Refresh the bank transaction data
							if (this.update_dt_cards) {
								frappe.call({
									method: "frappe.client.get",
									args: {
										doctype: "Bank Transaction",
										name: response.message.bank_transaction || this.bank_transaction.name
									},
									callback: (r) => {
										if (r.message) {
											this.update_dt_cards(r.message);
										}
									}
								});
							}

							this.dialog.hide();
						} else if (response.message.status === "queued") {
							// Asynchronous - show progress dialog
							this.showBulkProgressDialog(response.message.job_id, response.message.total_invoices);
							this.dialog.hide();
						}
					}
				},
				error: (error) => {
					frappe.msgprint(__("Error starting reconciliation: {0}", [error.message || "Unknown error"]));
				},
			});
		};

		// Ask for confirmation only when processing invoices
		if ((unpaidInvoices || []).length > 0) {
			frappe.confirm(
				__("You are about to reconcile {0} unpaid invoices. Continue?", [unpaidInvoices.length]),
				() => startJob()
			);
		} else {
			startJob();
		}
	}
	
	showBulkProgressDialog(jobId, totalInvoices) {
		// Helper function to cleanup event subscriptions
		const cleanupRealtimeEvents = () => {
			frappe.realtime.off("bulk_reconciliation_progress");
			frappe.realtime.off("bulk_reconciliation_complete");
		};

		// Create progress dialog
		const progressDialog = new frappe.ui.Dialog({
			title: __("Bulk Reconciliation in Progress"),
			indicator: "blue",
			size: "small",
			static: true,
			primary_action_label: __("Run in Background"),
			primary_action: () => {
				progressDialog.hide();
				frappe.show_alert({
					message: __("Bulk reconciliation is running in background. You will be notified when complete."),
					indicator: "blue"
				});
			}
		});

		// Add progress HTML
		progressDialog.$body.html(`
			<div class="bulk-reconciliation-progress">
				<p class="text-muted mb-3">
					<span class="progress-message">Starting bulk reconciliation...</span>
				</p>
				<div class="progress" style="height: 25px;">
					<div class="progress-bar progress-bar-striped progress-bar-animated"
						role="progressbar"
						style="width: 0%"
						aria-valuenow="0"
						aria-valuemin="0"
						aria-valuemax="100">
						<span class="progress-text">0%</span>
					</div>
				</div>
				<p class="text-muted mt-2 text-center">
					<small>
						<span class="current-count">0</span> of <span class="total-count">${totalInvoices}</span> invoices processed
					</small>
				</p>
			</div>
		`);

		// Cleanup event handlers when dialog is hidden/closed
		progressDialog.$wrapper.on('hidden.bs.modal', () => {
			cleanupRealtimeEvents();
		});

		progressDialog.show();

		// Subscribe to progress updates
		frappe.realtime.on("bulk_reconciliation_progress", (data) => {
			if (data.job_id === jobId) {
				// Update progress bar
				const progressBar = progressDialog.$body.find(".progress-bar");
				const progressText = progressDialog.$body.find(".progress-text");
				const currentCount = progressDialog.$body.find(".current-count");
				const progressMessage = progressDialog.$body.find(".progress-message");

				progressBar.css("width", data.percentage + "%");
				progressBar.attr("aria-valuenow", data.percentage);
				progressText.text(data.percentage + "%");
				currentCount.text(data.current);
				progressMessage.text(data.message);
			}
		});

		// Subscribe to completion notification
		frappe.realtime.on("bulk_reconciliation_complete", (data) => {
			if (data.job_id === jobId) {
				progressDialog.hide();

				if (data.success) {
					frappe.show_alert({
						message: data.message,
						indicator: "green"
					}, 10);

					// Refresh the data table
					if (this.update_dt_cards) {
						// Reload the bank transaction
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Bank Transaction",
								name: data.bank_transaction
							},
							callback: (r) => {
								if (r.message) {
									this.update_dt_cards(r.message);
								}
							}
						});
					}
				} else {
					frappe.msgprint({
						title: __("Bulk Reconciliation Failed"),
						message: data.message,
						indicator: "red"
					});
				}

				// Cleanup is now handled by the hidden.bs.modal event
				// which fires automatically when progressDialog.hide() is called above
			}
		});
	}
	
	// reconcileAllVouchers removed (handled by background job)
	
	// processRegularVouchers removed (handled by background job)

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
				dimensions: this._get_dimensions_from_dialog(values),
			},
			callback: (response) => {
				if (!response || !response.message) return;
				const alert_string = __("Bank Transaction {0} added as Payment Entry", [
					this.bank_transaction.name,
				]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				if (values.save_as_bank_rule) {
					this._show_save_bank_rule_dialog("Payment Entry", values);
				} else {
					this.dialog.hide();
				}
			},
		});
	}

	_get_dimensions_from_dialog(values) {
		if (!this.accounting_dimensions || !this.accounting_dimensions.length) return null;
		const dims = {};
		for (const dim of this.accounting_dimensions) {
			if (values[dim.fieldname]) {
				dims[dim.fieldname] = values[dim.fieldname];
			}
		}
		return Object.keys(dims).length ? JSON.stringify(dims) : null;
	}

	_show_save_bank_rule_dialog(entry_type, dialog_values) {
		// Build condition rows from bank transaction fields
		const bt = this.bank_transaction;
		const text_operator_options = "Equals\nContains\nNot Equals\nNot Contains";
		const numeric_operator_options = "Greater than\nGreater than or Equals\nEquals\nNot Equals\nLess Than\nLess Than or Equals";

		const condition_fields = [
			{ key: "reference_number", label: "Reference Number", field_name: "Reference Number", default_op: "Equals", default_checked: true, operators: text_operator_options },
			{ key: "custom_particulars", label: "Particulars", field_name: "Particulars", default_op: "Equals", default_checked: true, operators: text_operator_options },
			{ key: "custom_code", label: "Code", field_name: "Code", default_op: "Equals", default_checked: true, operators: text_operator_options },
			{ key: "description", label: "Description", field_name: "Description", default_op: "Contains", default_checked: false, operators: text_operator_options },
			{ key: "bank_party_name", label: "Other Party", field_name: "Other Party", default_op: "Equals", default_checked: true, operators: text_operator_options },
		];

		// Add deposit or withdrawal condition based on the transaction direction
		if (bt.deposit > 0) {
			condition_fields.push({ key: "deposit", label: "Deposit > 0", field_name: "Deposit", default_op: "Greater than", default_checked: false, operators: numeric_operator_options, fixed_value: "0" });
		} else if (bt.withdrawal > 0) {
			condition_fields.push({ key: "withdrawal", label: "Withdrawal > 0", field_name: "Withdrawal", default_op: "Greater than", default_checked: false, operators: numeric_operator_options, fixed_value: "0" });
		}

		// Only include fields that have non-empty values (deposit/withdrawal use fixed_value so always pass)
		const available_conditions = condition_fields.filter(f => f.fixed_value !== undefined || bt[f.key]);

		// If no condition fields are available, skip the prompt and hide the main dialog
		if (available_conditions.length === 0) {
			this.dialog.hide();
			return;
		}

		// Pre-fill title from first non-empty of: particulars, other party, description
		const default_title = (bt.custom_particulars || bt.bank_party_name || bt.description || "").substring(0, 140);

		// Build dialog fields
		const fields = [
			{
				label: __("Rule Title"),
				fieldname: "rule_title",
				fieldtype: "Data",
				reqd: 1,
				default: default_title,
			},
			{ fieldtype: "Section Break", label: __("Match Conditions") },
			{
				label: __("Match Any Condition"),
				fieldname: "match_any_condition",
				fieldtype: "Check",
				default: 0,
				description: __("If checked, the rule matches when ANY condition is met (OR logic). If unchecked, ALL conditions must match (AND logic)."),
			},
			{ fieldtype: "Section Break" },
		];

		// One row per available condition field
		available_conditions.forEach((cf, idx) => {
			const val = cf.fixed_value !== undefined ? cf.fixed_value : (bt[cf.key] || "").toString().substring(0, 140);
			fields.push(
				{
					label: __(cf.label),
					fieldname: `match_${cf.key}`,
					fieldtype: "Check",
					default: cf.default_checked ? 1 : 0,
					description: cf.fixed_value !== undefined ? "" : val,
				},
				{ fieldtype: "Column Break" },
				{
					label: __("Operator"),
					fieldname: `op_${cf.key}`,
					fieldtype: "Select",
					options: cf.operators,
					default: cf.default_op,
					depends_on: `eval:doc.match_${cf.key}`,
				},
				{ fieldtype: "Column Break" },
				{
					label: __("Value"),
					fieldname: `val_${cf.key}`,
					fieldtype: "Data",
					default: val,
					read_only: 1,
					depends_on: `eval:doc.match_${cf.key}`,
				}
			);
			// Add section break between condition rows (not after the last one)
			if (idx < available_conditions.length - 1) {
				fields.push({ fieldtype: "Section Break" });
			}
		});

		// Action section (all read-only, pre-filled from what was just created)
		fields.push({ fieldtype: "Section Break", label: __("Action") });
		fields.push({
			label: __("Entry Type"),
			fieldname: "action_entry_type",
			fieldtype: "Data",
			default: entry_type,
			read_only: 1,
		});

		if (entry_type === "Journal Entry" && dialog_values.second_account) {
			fields.push({ fieldtype: "Column Break" });
			fields.push({
				label: __("Account"),
				fieldname: "action_account",
				fieldtype: "Link",
				options: "Account",
				default: dialog_values.second_account,
				read_only: 1,
			});
		}

		if (dialog_values.party_type) {
			fields.push({ fieldtype: "Column Break" });
			fields.push({
				label: __("Party Type"),
				fieldname: "action_party_type",
				fieldtype: "Data",
				default: dialog_values.party_type,
				read_only: 1,
			});
		}

		if (dialog_values.party) {
			fields.push({ fieldtype: "Column Break" });
			fields.push({
				label: __("Party"),
				fieldname: "action_party",
				fieldtype: "Data",
				default: dialog_values.party,
				read_only: 1,
			});
		}

		if (dialog_values.cost_center) {
			fields.push({ fieldtype: "Column Break" });
			fields.push({
				label: __("Cost Center"),
				fieldname: "action_cost_center",
				fieldtype: "Link",
				options: "Cost Center",
				default: dialog_values.cost_center,
				read_only: 1,
			});
		}

		if (dialog_values.project) {
			fields.push({ fieldtype: "Column Break" });
			fields.push({
				label: __("Project"),
				fieldname: "action_project",
				fieldtype: "Link",
				options: "Project",
				default: dialog_values.project,
				read_only: 1,
			});
		}

		// Accounting dimensions
		if (this.accounting_dimensions && this.accounting_dimensions.length) {
			this.accounting_dimensions.forEach(dim => {
				const dim_val = dialog_values[dim.fieldname];
				if (dim_val) {
					fields.push({ fieldtype: "Column Break" });
					fields.push({
						label: dim.label,
						fieldname: `action_dim_${dim.fieldname}`,
						fieldtype: "Link",
						options: dim.options,
						default: dim_val,
						read_only: 1,
					});
				}
			});
		}

		const me = this;
		const rule_dialog = new frappe.ui.Dialog({
			title: __("Save as Bank Rule"),
			size: "large",
			fields: fields,
			primary_action_label: __("Save Rule"),
			primary_action(values) {
				// Validate at least one condition is checked
				const conditions = [];
				available_conditions.forEach(cf => {
					if (values[`match_${cf.key}`]) {
						conditions.push({
							field_name: cf.field_name,
							condition: values[`op_${cf.key}`],
							value: values[`val_${cf.key}`],
						});
					}
				});

				if (conditions.length === 0) {
					frappe.msgprint(__("Please select at least one match condition."));
					return;
				}

				// Build dimensions dict
				const dimensions = {};
				if (me.accounting_dimensions && me.accounting_dimensions.length) {
					me.accounting_dimensions.forEach(dim => {
						const dim_val = dialog_values[dim.fieldname];
						if (dim_val) {
							dimensions[dim.fieldname] = dim_val;
						}
					});
				}

				frappe.call({
					method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.abr_bank_rule.abr_bank_rule.create_bank_rule_from_voucher",
					args: {
						bank_transaction_name: me.bank_transaction.name,
						title: values.rule_title,
						entry_type: entry_type,
						match_any_condition: values.match_any_condition ? 1 : 0,
						conditions: JSON.stringify(conditions),
						second_account: (entry_type === "Journal Entry") ? dialog_values.second_account : null,
						party_type: dialog_values.party_type || null,
						party: dialog_values.party || null,
						cost_center: dialog_values.cost_center || null,
						project: dialog_values.project || null,
						dimensions: JSON.stringify(dimensions),
					},
					freeze: true,
					freeze_message: __("Saving bank rule..."),
					callback(r) {
						if (r.message) {
							const title = frappe.utils.escape_html(r.message.title);
							frappe.show_alert({
								message: __("Bank Rule {0} created", [`<a href="/app/abr-bank-rule/${r.message.name}">${title}</a>`]),
								indicator: "green",
							});
						}
						rule_dialog.hide();
						me.dialog.hide();
					},
					error() {
						rule_dialog.get_primary_btn().prop("disabled", false);
					},
				});
			},
			secondary_action_label: __("Skip"),
			secondary_action() {
				rule_dialog.hide();
				me.dialog.hide();
			},
		});

		rule_dialog.onhide = () => {
			me.dialog.hide();
		};

		rule_dialog.show();
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
				cost_center: values.cost_center,
				project: values.project,
				dimensions: this._get_dimensions_from_dialog(values),
			},
			callback: (response) => {
				if (!response || !response.message) return;
				const alert_string = __("Bank Transaction {0} added as Journal Entry", [
					this.bank_transaction.name,
				]);
				frappe.show_alert(alert_string);
				this.update_dt_cards(response.message);
				if (values.save_as_bank_rule) {
					this._show_save_bank_rule_dialog("Journal Entry", values);
				} else {
					this.dialog.hide();
				}
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
					dimensions: this._get_dimensions_from_dialog(values),
					allow_edit: true,
				},
				callback: (r) => {
					const doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				},
			});
		} else {
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
					cost_center: values.cost_center,
					project: values.project,
					dimensions: this._get_dimensions_from_dialog(values),
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
