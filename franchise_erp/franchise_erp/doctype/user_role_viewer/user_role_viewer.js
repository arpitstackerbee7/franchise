frappe.ui.form.on("User Role Viewer", {

    role_profile(frm) {
        load_roles_from_profile(frm);
    },

    module_profile(frm) {
        load_roles_from_module_profile(frm);
    }

});


function load_roles_from_profile(frm) {

    if (!frm.doc.role_profile) {
        frm.clear_table("table_vjxt");
        frm.refresh_field("table_vjxt");
        return;
    }

    frappe.call({
        method:
            "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_roles_from_profile",

        args: {
            role_profile: frm.doc.role_profile
        },

        callback(r) {

            const roles = r.message || [];

            frm.clear_table("table_vjxt");

            roles.forEach(d => {

                if (!d.role) {
                    return;
                }

                let row = frm.add_child("table_vjxt");

                row.role = d.role;
                row.check = 1;
            });

            frm.refresh_field("table_vjxt");
        }
    });
}

function load_roles_from_module_profile(frm) {

    if (!frm.doc.module_profile) {
        frm.clear_table("module_profile_role");
        frm.refresh_field("module_profile_role");
        return;
    }

    frappe.call({
        method:
            "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_roles_from_module_profile",

        args: {
            module_profile: frm.doc.module_profile
        },

        callback(r) {

            const roles = r.message || [];

            frm.clear_table("module_profile_role");

            roles.forEach(d => {

                if (!d.role) {
                    return;
                }

                let row = frm.add_child("module_profile_role");

                row.role = d.role;
                row.check = 1;
            });

            frm.refresh_field("module_profile_role");
        }
    });
}