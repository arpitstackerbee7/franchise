// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.ui.form.on("User Role Viewer", {

    refresh(frm) {
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_logged_user_roles",

            callback(r) {

                if (!r.message) return;

                let d = r.message;

                frm.doc.user = d.user;

                frm.refresh_field("user");

                frappe.db.get_doc("User", d.user)
                    .then(user => {

                        frm.doc.enabled = cint(user.enabled);
                        frm.doc.full_name = user.full_name;
                        frm.doc.username = user.username;
                        frm.doc.company = user.company;

                        frm.refresh_field("enabled");
                        frm.refresh_field("full_name");
                        frm.refresh_field("username");
                        frm.refresh_field("company");

                        frm.page.set_indicator(
                            user.enabled ? __("Enabled") : __("Disabled"),
                            user.enabled ? "green" : "red"
                        );

                        frm.dirty = false;
                    });

                let roles_html = `

                    <div class="role-editor">

                        <div class="frappe-control" data-fieldtype="MultiCheck">

                            <div class="checkbox-options"
                                style="
                                    --checkbox-options-columns: 15rem;
                                    padding: 1em;
                                ">
                `;

                d.roles.forEach(role => {

                    roles_html += `

                        <div class="checkbox unit-checkbox">

                            <label
                                style="
                                    display:flex;
                                    align-items:center;
                                ">

                                <input
                                    type="checkbox"
                                    ${role.checked ? "checked" : ""}
                                    disabled
                                    style="flex-shrink:0;">

                                <span
                                    class="label-area"
                                    style="margin-left:8px;">

                                    ${role.role}
                                </span>
                            </label>
                        </div>
                    `;
                });

                roles_html += `

                            </div>
                        </div>
                    </div>
                `;

                frm.get_field("roles_html").$wrapper.html(roles_html);

                frm.get_field("modules_html").$wrapper.html("");

            }
        });
    }

});