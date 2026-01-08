frappe.after_ajax(() => {
    if (!frappe.views || !frappe.views.TreeView) return;

    const TreeView = frappe.views.TreeView;
    const original = TreeView.prototype.prepare_fields;

    TreeView.prototype.prepare_fields = function () {
        if (this.doctype !== "Item Group") {
            return original.call(this);
        }

        this.fields = [
            { fieldtype: "Data", fieldname: "item_group_name", label: __("Item Group Name"), reqd: 1 },
            { fieldtype: "Data", fieldname: "custom_code", label: __("Code"), reqd: 1},
            { fieldtype: "Check", fieldname: "is_group", label: __("Is Group")},
            { fieldtype: "Check", fieldname: "custom_is_silhouette", label: __("Is Silhouette") },
            { fieldtype: "Check", fieldname: "custom_is_departmnent", label: __("Is Departmnent") },
            { fieldtype: "Check", fieldname: "custom_is_collection", label: __("Is Collection") },
            { fieldtype: "Check", fieldname: "custom_is_division", label: __("Is Division") }
        ];
    };
});
