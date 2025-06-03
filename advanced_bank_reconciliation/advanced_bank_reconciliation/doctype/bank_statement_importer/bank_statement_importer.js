// Copyright (c) 2024, High Flyer and contributors
// For license information, please see license.txt

var data_headers = []
var data_body = []
var tbl = []

frappe.ui.form.on('Bank Statement Importer', {
	setup(frm) {
		frm.trigger("bank_account");
	},
	refresh(frm) {
		frm.disable_save();
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_company_account: 1,
				},
			};
		});
	},
	bank_account(frm) {
		const wrapper = frm.get_field("last_transaction_html").$wrapper;
		wrapper.empty();
		if (!frm.doc.bank_account) {
			return;
		}

		frm.call({
			method: "get_last_transaction",
			args: { bank_account: frm.doc.bank_account },
			callback: function (data) {
				const last_transaction = data.message;
				let html = "";
				if (last_transaction) {
					const amount = last_transaction.deposit || last_transaction.withdrawal;
					const transactionType = last_transaction.deposit ? __("Deposit") : __("Withdrawal");
					html = `<div class="text-danger py-2">Last Transaction: ${format_currency(amount)} ${transactionType} on ${last_transaction.date}</div>`;
				} else {
					html = `<div class="py-2">${__("No previous transactions found")}</div>`;
				}
				wrapper.append(html);
			}
		});
		frm.set_value("import_file", '');
		frm.save()
	},
	upload_statement(frm) {
		if (!frm.doc.import_file) {
			frappe.msgprint({
				title: __('Error'),
				indicator: 'red',
				message: __('Please select a bank statement file to upload')
			});
			return;
		}

		frm.call({
			method: "form_start_import",
			args: { 
				data_import: frm.doc.import_file,
				bank_account: frm.doc.bank_account
			},
			btn: frm.page.btn_primary,
			freeze: true,
			callback: function (data) {
				frm.doc.data_fetched = true;
				frm.refresh_field("data_fetched");
				const options = data?.message?.header?.join('\n') ?? "";
				data_headers = data?.message?.header;
				data_body = data?.message?.body;
				
				// Set field options
				frm.set_df_property("date_select", "options", options);
				frm.set_df_property("deposit_select", "options", options);
				frm.set_df_property("withdrawal_select", "options", options);
				frm.set_df_property("amount_select", "options", options);
				frm.set_df_property("description_select", "options", options);
				frm.set_df_property("reference_number_select", "options", options);
				frm.set_df_property("bank_account_select", "options", options);
				
				// Apply bank mapping if available
				const bank_mapping = data?.message?.bank || {};
				if (Object.keys(bank_mapping).length > 0) {
					// Define field mapping configuration
					const field_mapping = {
						'date': 'date_select',
						'deposit': 'deposit_select',
						'withdrawal': 'withdrawal_select',
						'description': 'description_select',
						'reference_number': 'reference_number_select',
						'amount': 'amount_select'
					};
					
					// Map fields based on bank transaction mapping
					Object.entries(bank_mapping).forEach(([file_field, bank_field]) => {
						if (bank_field === 'date_format') return; // Skip date_format
						
						const form_field = field_mapping[bank_field];
						if (form_field && frm.fields_dict[form_field]) {
							frm.set_value(form_field, file_field);
						}
					});
					
					// Set date format from bank
					if (bank_mapping.date_format) {
						frm.set_value('date_format', bank_mapping.date_format);
					}
				}
				
				// Refresh all fields
				frm.refresh_field("date_select");
				frm.refresh_field("deposit_select");
				frm.refresh_field("amount_select");
				frm.refresh_field("withdrawal_select");
				frm.refresh_field("description_select");
				frm.refresh_field("reference_number_select");
			}
		}).then((r) => {
			if (r.message === true) {
				frm.disable_save();
			}
		});
	},

	map_fields(frm) {
		frm.call({
			method: "map_fields",
			args: {
				data: frm.doc,
				data_headers: data_headers,
				data_body: data_body
			},
			freeze: true,
			btn: frm.page.btn_primary,
			callback: function (data) {
				console.log("DATA", data);
				frm.doc.fields_mapped = true;
				frm.refresh_field("fields_mapped");
				tbl = data.message;
				let data_len = data.message?.length || 0;
				const rows = [];
				let duplicates = 0;
				for (let i = 0; i < data_len; i++) {
					const row = data.message[i];
					if (i > 0) {
						rows.push(row);
						if (row.length > 7 && row[7] == 1) {
							duplicates += 1;
						}
					}
				}

				console.log("WITHOUT DOC", frm.get_field("import_preview"));
				let wrapper = frm.get_field("import_preview").$wrapper;
				wrapper.empty();
				const columns = [
					{
						name: __("Date"),
						editable: false,
						width: 100,
					},
					{
						name: __("Deposit"),
						editable: false,
						width: 100,
					},
					{
						name: __("Withdrawal"),
						editable: false,
						width: 100,
					},
					{
						name: __("Description"),
						editable: false,
						width: 150,
					},
					{
						name: __("Reference Number"),
						editable: false,
						width: 150,
					},
					{
						name: __("Bank Account"),
						editable: false,
						width: 150,
					},
					{
						name: __("Currency"),
						editable: false,
						width: 100,
					},
					{
						name: __("Is Duplicated"),
						editable: false,
						width: 100,
					}
				];
				const datatable_options = {
					columns: columns,
					data: rows,
					dynamicRowHeight: true,
					checkboxColumn: false,
					inlineFilters: true,
				};
				this.datatable = new frappe.DataTable(wrapper.get(0), datatable_options);
				if (duplicates > 0) {
					frappe.msgprint({
						title: __('Warning'),
						indicator: 'yellow',
						message: __(`Duplicate records(${duplicates}) found. Please check and confirm the records prior to submission.`)
					});
				}
			}
		}).then((r) => {
			if (r.message === true) {
				frm.disable_save();
			}
		});
	},

	import_data(frm) {
		frm.call({
			method: "publish_records",
			args: { data_import: tbl },
			btn: frm.page.btn_primary,
			freeze: true,
			callback: function (data) {
				console.log(data);
				if (data.message === true) {
					frappe.msgprint({
						title: __('Success'),
						indicator: 'green',
						message: __('Bank statement uploaded successfully')
					});
					frm.trigger("reset");
				} else {
					frappe.msgprint({
						title: __('Error'),
						indicator: 'red',
						message: __('Bank statement uploaded unsuccessful')
					});
				}
			}
		}).then((r) => {
			if (r.message === true) {
				frm.disable_save();
			}
		});
	},
	reset(frm) {
		frm.doc.data_fetched = false;
		frm.doc.fields_mapped = false;
		frm.set_value("import_file", '');
		frm.refresh_field("data_fetched");
		frm.refresh_field("fields_mapped");
		frm.get_field("import_preview").$wrapper.empty();
	}
});
