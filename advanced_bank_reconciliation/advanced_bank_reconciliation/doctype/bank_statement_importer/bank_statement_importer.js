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
				
				// Apply bank mapping if available
				const bank_mapping = data?.message?.bank || {};
				console.log("BANK MAPPING", bank_mapping);
				
				// Extract file field names directly from bank mapping (now bank fields are keys)
				const dateField = bank_mapping.date;
				const depositField = bank_mapping.deposit;
				const withdrawalField = bank_mapping.withdrawal;
				const descriptionField = bank_mapping.description;
				const referenceField = bank_mapping.reference_number;
				
				// Set field options
				frm.set_df_property("date_select", "options", options);
				frm.set_df_property("deposit_select", "options", options);
				frm.set_df_property("withdrawal_select", "options", options);
				frm.set_df_property("amount_select", "options", options);
				frm.set_df_property("description_select", "options", options);
				frm.set_df_property("reference_number_select", "options", options);


				// Check if deposit and withdrawal use the same field
				// This happens when both depositField and withdrawalField exist and point to the same file column
				const isSameAmountField = depositField && withdrawalField && depositField === withdrawalField;
				
				if (isSameAmountField) {
					frm.set_value('same_amount_field', 1);
					
					// Set amount_select to the shared field
					const sharedField = depositField || withdrawalField;
					frm.set_value('amount_select', sharedField);
                    
					// Clear deposit_select and withdrawal_select to avoid redundancy
					frm.set_value('deposit_select', '');
					frm.set_value('withdrawal_select', '');
                    
					// Default positive field to Deposit - this means positive values in the amount column
					// will be treated as deposits (money coming in) and negative values as withdrawals (money going out)
					// This is the most common banking convention where positive = credit/deposit, negative = debit/withdrawal
					frm.set_value('positive_field', 'Deposit');
				} else {
					frm.set_value('same_amount_field', 0);
					frm.set_value('positive_field', '');
				}

				// Set form field values directly from bank mapping
				if (dateField) {
					frm.set_value('date_select', dateField);
				}
				if (!isSameAmountField) {
					// Only set individual deposit/withdrawal fields if not using same amount field
					if (depositField) {
						frm.set_value('deposit_select', depositField);
					}
					if (withdrawalField) {
						frm.set_value('withdrawal_select', withdrawalField);
					}
				}
				if (descriptionField) {
					frm.set_value('description_select', descriptionField);
				}
				if (referenceField) {
					frm.set_value('reference_number_select', referenceField);
				}
				
				// Set date format from bank
				if (bank_mapping.date_format) {
					frm.set_value('date_format', bank_mapping.date_format);
				}
				
				// Refresh all fields consistently
				frm.refresh_field("same_amount_field");
				frm.refresh_field("positive_field");
				frm.refresh_field("date_select");
				frm.refresh_field("deposit_select");
				frm.refresh_field("amount_select");
				frm.refresh_field("withdrawal_select");
				frm.refresh_field("description_select");
				frm.refresh_field("reference_number_select");
                frm.refresh_field("date_format");
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
	},
	
	same_amount_field(frm) {
		// Handle manual changes to same_amount_field checkbox
		if (frm.doc.same_amount_field) {
			// When checked, clear individual deposit/withdrawal selects to avoid redundancy
			frm.set_value('deposit_select', '');
			frm.set_value('withdrawal_select', '');
			
			// Set default positive field if not already set
			if (!frm.doc.positive_field) {
				frm.set_value('positive_field', 'Deposit');
			}
		} else {
			// When unchecked, clear amount_select and positive_field
			frm.set_value('amount_select', '');
			frm.set_value('positive_field', '');
		}
		
		// Refresh all related fields consistently
		frm.refresh_field("deposit_select");
		frm.refresh_field("withdrawal_select");
		frm.refresh_field("amount_select");
		frm.refresh_field("positive_field");
	},
	
	amount_select(frm) {
		// When amount_select changes and same_amount_field is checked
		if (frm.doc.same_amount_field && frm.doc.amount_select) {
			// Ensure deposit and withdrawal selects remain clear
			frm.set_value('deposit_select', '');
			frm.set_value('withdrawal_select', '');
			frm.refresh_field("deposit_select");
			frm.refresh_field("withdrawal_select");
		}
	},
	
	positive_field(frm) {
		// Refresh the field when positive_field changes
		frm.refresh_field("positive_field");
	}
});
