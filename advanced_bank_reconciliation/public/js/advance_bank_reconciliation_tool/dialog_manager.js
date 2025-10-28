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
		console.log("get payment entries result", result.message.length);
		let data = result.message;

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

		const r = await frappe.call({
			method: "erpnext.accounts.doctype.bank_transaction.bank_transaction.get_doctypes_for_bank_reconciliation"
		});
		console.log("get_doctypes_for_bank_reconciliation", r.message);
		$.each(r.message, (_i, entry) => {
			// Create more balanced columns: 2-3-2 distribution for typical 7 checkboxes
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

		const filters_res = await frappe.call({
			method: "advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_additional_filters"
		});
		console.log("additional filters response", filters_res.message);
		this.additional_filters = filters_res.message;
		$.each(filters_res.message, (_i, entry) => {
			console.log("Adding custom filter", entry.fieldname);
			fields.push({
				fieldtype: entry.fieldtype,
				label: entry.label || entry.fieldname,
				fieldname: entry.fieldname,
				onchange: () => this.update_options()
			})
		});

		fields.push(...this.get_voucher_fields());

		me.dialog = new frappe.ui.Dialog({
			title: __("Reconcile the Bank Transaction"),
			fields: fields,
			size: "extra-large",
			primary_action: (values) => this.reconciliation_dialog_primary_action(values),
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
