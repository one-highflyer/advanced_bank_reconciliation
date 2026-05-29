(() => {
	const party_reference_types = ["Customer", "Supplier", "Employee"];
	const control_link = frappe.ui.form.ControlLink;

	if (!control_link || control_link.prototype.__abr_party_reference_query_patched) {
		return;
	}

	const standard_set_custom_query = control_link.prototype.set_custom_query;

	control_link.prototype.set_custom_query = function (args) {
		standard_set_custom_query.call(this, args);

		const is_journal_entry_reference =
			this.frm &&
			this.frm.doctype === "Journal Entry" &&
			this.df &&
			this.df.fieldname === "reference_name" &&
			(this.doctype === "Journal Entry Account" ||
				this.df.parent === "Journal Entry Account");

		if (!is_journal_entry_reference) {
			return;
		}

		const row =
			this.doc ||
			(this.doctype && this.docname ? frappe.get_doc(this.doctype, this.docname) : null);

		if (row && party_reference_types.includes(row.reference_type)) {
			args.filters = {};
			delete args.query;
		}
	};

	control_link.prototype.__abr_party_reference_query_patched = true;
})();
