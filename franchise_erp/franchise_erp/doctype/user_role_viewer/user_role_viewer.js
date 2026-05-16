// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt
frappe.ui.form.on("User Role Viewer", {
    refresh(frm) {
        let grid = frm.fields_dict.table_vjxt.grid;

        grid.cannot_add_rows = true;
        grid.cannot_delete_rows = true;

        grid.wrapper.find('.grid-add-row').hide();
        grid.wrapper.find('.grid-remove-rows').hide();

        if (!frm.is_new()) {
            return;
        }
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_logged_user_roles",
            callback(r) {
                if (!r.message) return;
                let d = r.message;
                frm.set_value("user", d.user);

                frappe.db.get_doc("User", d.user)
                    .then(user => {

                        frm.set_value("enabled", cint(user.enabled));
                        frm.set_value("full_name", user.full_name);
                        frm.set_value("username", user.username);
                        frm.set_value("company", user.company);

                        frm.page.set_indicator(
                            user.enabled ? __("Enabled") : __("Disabled"),
                            user.enabled ? "green" : "red"
                        );
                    });
                frm.clear_table("table_vjxt");

                (d.roles || []).forEach(role => {

                    let row = frm.add_child("table_vjxt");

                    row.role = role.name;
                    row.check = 0;
                });

                frm.refresh_field("table_vjxt");

                // hide again after render
                grid.wrapper.find('.grid-add-row').hide();
                grid.wrapper.find('.grid-remove-rows').hide();

                grid.wrapper.find('.grid-row-check').hide();
                grid.wrapper.find('.row-check').hide();
                grid.wrapper.find('.grid-heading-row .grid-row-check').hide();
            }
        });
    }
});