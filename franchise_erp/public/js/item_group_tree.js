frappe.after_ajax(() => {

    frappe.treeview_settings["Item Group"] = {

        method: "franchise_erp.custom.item_group.get_item_group_tree",

        get_label(node) {
            const parent_label = node.parent_label || null;

            if (!parent_label) {
                return `<b class="tree-label">.</b>`;
            }

            const title = node.data?.title || node.label || "Unnamed Group";
            return `<b>${title}</b>`;
        },

        on_click(node) {
            frappe.set_route("Form", "Item Group", node.name);
        },

        expand: true
    };

});
