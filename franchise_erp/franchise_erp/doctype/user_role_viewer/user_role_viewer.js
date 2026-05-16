// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt
frappe.ui.form.on("User Role Viewer", {
    refresh(frm) {
        let grid = frm.fields_dict.table_vjxt.grid;

        grid.cannot_add_rows = true;
        grid.cannot_delete_rows = true;
        grid.only_sortable = false;
        grid.multiple_set = false;

        function apply_grid_lock() {

            let w = grid.wrapper;

            w.find('.grid-search').show();
            w.find('.grid-search-input').show();

            w.find('.grid-add-row').hide();
            w.find('.grid-remove-rows').hide();

            w.find('.grid-row-check').hide();
            w.find('.row-check').hide();
            w.find('.grid-heading-row .grid-row-check').hide();

            w.find('.grid-custom-buttons').hide();

            w.find('.grid-row').off('click');
            w.find('.btn-open-row').remove();

            w.find('.grid-static-col').css({
                "pointer-events": "none"
            });

            // ONLY allow your checkbox field
            w.find('[data-fieldname="check"]').css({
                "pointer-events": "auto"
            });

            // remove editable class if any
            w.find('.grid-row').removeClass('editable-row');
        }
        apply_grid_lock();

        setTimeout(apply_grid_lock, 300);
        setTimeout(apply_grid_lock, 1000);

        grid.wrapper.on('click', '.btn-paging', function () {
            setTimeout(apply_grid_lock, 300);
        });

        $(document).on('grid-row-render', function () {
            setTimeout(apply_grid_lock, 50);
        });

        if (!frm.is_new()) {
            return;
        }
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_logged_user_roles",

            callback(r) {
                if (!r.message) return;
                let d = r.message;

                frm.set_value("user", d.user);

                frappe.db.get_doc("User", d.user).then(user => {

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

                apply_grid_lock();
            }
        });
    }
});