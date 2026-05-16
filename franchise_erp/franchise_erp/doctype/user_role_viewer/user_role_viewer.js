// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt
frappe.ui.form.on("User Role Viewer", {

    role_profile(frm) {
        load_roles_from_profile(frm);
    }
});

function load_roles_from_profile(frm) {

    if (!frm.doc.role_profile) {

        frm.clear_table("table_vjxt");
        frm.refresh_field("table_vjxt");
        return;
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_roles_from_profile",
        args: {
            role_profile: frm.doc.role_profile
        },
        callback(r) {

            if (!r.message) return;

            // prevent duplicate reload
            let existing_roles = (frm.doc.table_vjxt || []).map(d => d.role);

            let new_roles = (r.message || []).map(d => d.role);

            // if already same data, do nothing
            if (JSON.stringify(existing_roles.sort()) === JSON.stringify(new_roles.sort())) {
                return;
            }

            frm.clear_table("table_vjxt");

            (r.message || []).forEach(role => {

                let row = frm.add_child("table_vjxt");

                row.role = role.role;
                row.check = 1;
            });

            frm.refresh_field("table_vjxt");
        }
    });
}