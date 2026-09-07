(() => {
    const OriginalRoleEditor = frappe.RoleEditor;

    frappe.RoleEditor = class extends OriginalRoleEditor {
        show() {
            if (this.frm.doctype !== "Role Profile") {
                return super.show();
            }

            frappe.call({
                method:
                    "franchise_erp.overrides.role_profile.get_current_user_roles",
            }).then((r) => {
                const allowed_roles = r.message || [];

                const selected_roles = (this.frm.doc.roles || [])
                    .map((row) => row.role)
                    .filter(Boolean);

                // Role Profile ke liye __onload.all_roles set nahi hota,
                // isliye base class multicheck banata hi nahi — force karo.
                if (!this.multicheck) {
                    this.make(true);
                }

                this.multicheck.df.get_data = () => {
                    return allowed_roles.map((role) => ({
                        label: __(role),
                        value: role,
                        checked: selected_roles.includes(role),
                    }));
                };

                this.multicheck.refresh();

                this.set_enable_disable();
            });
        }
    };

    frappe.ui.form.on("Role Profile", {
        refresh(frm) {
            if (!frm.roles_editor) {
                const role_area = $(frm.fields_dict.roles_html.wrapper);

                frm.roles_editor = new frappe.RoleEditor(role_area, frm);
            }

            frm.roles_editor.show();
        },
    });
})();