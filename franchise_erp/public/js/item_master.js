frappe.ui.form.on("Item", {

    // ── onload (runs once) ──────────────────────────────────────────
    onload(frm) {
        frm.set_query("custom_silvet", function () {
            return {
                query: "franchise_erp.custom.item_group.get_child_item_groups"
            };
        });

        // Clear barcodes on duplicate
        if (frm.is_new() && frm.doc.name && frm.doc.name.startsWith('new-item')) {
            frm.clear_table('barcodes');
            frm.refresh_field('barcodes');
        }

        // Add empty tax row for new items
        if (frm.is_new() && (!frm.doc.taxes || frm.doc.taxes.length === 0)) {
            frm.add_child('taxes');
            frm.refresh_field('taxes');
        }
    },

    // ── SINGLE MERGED refresh handler ──────────────────────────────
    refresh(frm) {

        // 1. Filters
        frm.set_query("custom_silvet", function () {
            return { filters: { custom_is_silhouette: 1 } };
        });
        frm.set_query("item_group", function () {
            return { filters: { custom_is_division: 1 } };
        });

        // 2. Disable rename
        frm.disable_rename = true;
        $(".page-title .editable-title").css("pointer-events", "none");

        // 3. Read-only item_code after save
        if (!frm.is_new()) {
            frm.set_df_property("item_code", "read_only", 1);
        }

        // 4. Upload + Download buttons inside grid
        if (!frm.is_new()) {

            
            frm.fields_dict['custom_item_prices'].grid.add_custom_button(__('Upload'), function () {
                new frappe.ui.FileUploader({
                    allow_multiple: false,
                    on_success: (file) => {
                        frappe.call({
                            method: "franchise_erp.custom.item_master.smart_bulk_upload",
                            args: {
                                item_code: frm.doc.name,
                                file_url: file.file_url
                            },
                            callback: function (r) {
                                frm.reload_doc();
                                frappe.msgprint(r.message || "Upload complete");
                            }
                        });
                    }
                });
            });

            // Download button
            frm.fields_dict['custom_item_prices'].grid.add_custom_button(__('Download'), function () {
                let rows = frm.doc.custom_item_prices || [];

                if (rows.length === 0) {
                    frappe.msgprint("No data to download.");
                    return;
                }

                let csv = "Item Code,Price List,Rate\n";
                rows.forEach(row => {
                    csv += `${row.item_code || ""},${row.price_list || ""},${row.rate || ""}\n`;
                });

                let blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
                let url = URL.createObjectURL(blob);
                let a = document.createElement("a");
                a.href = url;
                a.download = `Item_Prices_${frm.doc.name}.csv`;
                a.click();
                URL.revokeObjectURL(url);
            });

        
            setTimeout(() => {
                let grid_wrapper = frm.fields_dict['custom_item_prices'].grid.wrapper;
                let grid_footer = grid_wrapper.find('.grid-footer');

                // Make footer flex so both sides work
                grid_footer.css({
                    'display': 'flex',
                    'justify-content': 'space-between',
                    'align-items': 'center'
                });

                // Move Upload to far right
                let upload_btn = grid_footer.find('.btn-custom:contains("Upload")');
                upload_btn.css('margin-left', 'auto');
                grid_footer.append(upload_btn);

                // Move Download after Upload
                let download_btn = grid_footer.find('.btn-custom:contains("Download")');
                grid_footer.append(download_btn);
            }, 300);
        }

        // 5. SIS Counter role — hide price table
        let user_roles = frappe.user_roles;
        let is_privileged = (frappe.session.user === 'Administrator' || user_roles.includes('System Manager'));
        let is_sis = user_roles.includes('SIS Counter');

        if (is_sis && !is_privileged) {
            frm.toggle_display('custom_item_prices', false);
            frm.toggle_display('last_purchase_rate', false);
            frm.toggle_display('is_customer_provided_item', false);
        } else {
            frm.toggle_display('custom_item_prices', true);
            frm.toggle_display('last_purchase_rate', true);
            frm.toggle_display('is_customer_provided_item', true);
        }

        // 6. TZU Setting dynamic role restriction
        if (!frm.is_new()) {
            frappe.db.get_doc('TZU Setting', null).then(settings => {
                if (settings.item_restricted_roles && settings.item_restricted_roles.length > 0) {
                    let restricted = settings.item_restricted_roles.some(row =>
                        frappe.user_roles.includes(row.role)
                    );
                    if (restricted) apply_item_restrictions(frm);
                }
            });
        }
    },

    // ── Other field events ──────────────────────────────────────────
    custom_colour_name(frm) {
        if (frm.doc.custom_colour_name) {
            frappe.call({
                method: "frappe.client.get",
                args: { doctype: "Color", name: frm.doc.custom_colour_name },
                callback(r) {
                    frm.set_value("custom_colour_code",
                        r?.message?.custom_color_code || "");
                }
            });
        } else {
            frm.set_value("custom_colour_code", "");
        }
    },

    custom_silvet(frm) {
        if (!frm.doc.custom_silvet) {
            frm.set_value('custom_departments', '');
            frm.set_value('custom_group_collection', '');
            frm.set_value('item_group', '');
            return;
        }
        frappe.call({
            method: 'franchise_erp.custom.item_group.get_item_group_parents',
            args: { child_group: frm.doc.custom_silvet },
            callback: function (r) {
                if (!r.message) return;
                frm.set_value('custom_departments', r.message.department || '');
                frm.set_value('custom_group_collection', r.message.collection || '');
                frm.set_value('item_group', r.message.main_group || '');
            }
        });
    },

    is_stock_item(frm) {
        if (frm.doc.is_stock_item == 0) frm.set_value('item_code', '');
    },

    item_code(frm) {
        (frm.doc.custom_item_prices || []).forEach(row => {
            row.item_code = frm.doc.item_code;
        });
        frm.refresh_field("custom_item_prices");
    },

    gst_hsn_code(frm) {
        if (!frm.doc.gst_hsn_code) return;
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "GST HSN Code", name: frm.doc.gst_hsn_code },
            callback: function (r) {
                frm.clear_table("taxes");
                if (r.message?.taxes?.length > 0) {
                    r.message.taxes.forEach(hsn_row => {
                        let row = frm.add_child("taxes");
                        row.item_tax_template = hsn_row.item_tax_template;
                        row.tax_category = hsn_row.tax_category || "";
                        row.valid_from = hsn_row.valid_from || "";
                        row.minimum_net_rate = hsn_row.minimum_net_rate || 0;
                        row.maximum_net_rate = hsn_row.maximum_net_rate || 0;
                    });
                } else {
                    frm.add_child("taxes");
                }
                frm.refresh_field("taxes");
            }
        });
    }
});

// ── Child table events ──────────────────────────────────────────────
frappe.ui.form.on("Item Price Row", {
    custom_item_prices_add(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.item_code = frm.doc.item_code;
        frm.refresh_field("custom_item_prices");
    }
});

// ── Helper function ─────────────────────────────────────────────────
function apply_item_restrictions(frm) {
    frm.disable_save();
    frm.set_read_only();
    frm.page.clear_menu();
    frm.meta.fields.forEach(df => {
        frm.set_df_property(df.fieldname, "read_only", 1);
    });
}