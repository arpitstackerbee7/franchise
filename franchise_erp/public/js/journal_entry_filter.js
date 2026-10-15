(() => {
    const original_add_field_option =
        frappe.ui.FieldSelect.prototype.add_field_option;

    frappe.ui.FieldSelect.prototype.add_field_option = function (df) {
        // Remove only Is System Generated
        // from Journal Entry filter dropdown
        if (
            this.doctype === "Journal Entry" &&
            df.fieldname === "is_system_generated"
        ) {
            return;
        }

        return original_add_field_option.call(this, df);
    };
})();