frappe.treeview_settings['Item Group'] = {

    method: "franchise_erp.custom.item_group.get_item_group_tree",

    get_label: function (node) {
        // console.log("Node:", node);

        // 🔥 If parent_label is null or undefined → show "All Item Groups"
        const parent_label = node.parent_label || null;

        if (!parent_label) {
            return `<b class="tree-label">All Item Groups</b>`;
        }

        // 🔹 CHILD NODES
        const title = node.data?.title || node.label || "Unnamed Group";
        return `<b>${title}</b>`;
    },

    on_click: function (node) {
        frappe.set_route("Form", "Item Group", node.name);
    },

    expand: true
};
