frappe.ui.form.on("Item", {
    custom_colour_name(frm) {
        if (frm.doc.custom_colour_name) {

            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Color",
                    name: frm.doc.custom_colour_name
                },
                callback(r) {
                    if (r && r.message && r.message.custom_color_code) {
                        frm.set_value("custom_colour_code", r.message.custom_color_code);
                    } else {
                        frm.set_value("custom_colour_code", "");
                    }
                }
            });

        } else {
            frm.set_value("custom_colour_code", "");
        }
    }
});

// fetch according to custom_silvet
frappe.ui.form.on('Item', {
    custom_silvet(frm) {
        // If custom_silvet is empty, clear dependent fields
        if (!frm.doc.custom_silvet) {
            frm.set_value('custom_departments', '');
            frm.set_value('custom_group_collection', '');
            frm.set_value('item_group', '');
            return;
        }

        // If custom_silvet has a value, fetch parent groups
        frappe.call({
            method: 'franchise_erp.custom.item_group.get_item_group_parents',
            args: {
                child_group: frm.doc.custom_silvet
            },
            callback: function (r) {
                if (!r.message) return;

                frm.set_value('custom_departments', r.message.department || '');
                frm.set_value('custom_group_collection', r.message.collection || '');
                frm.set_value('item_group', r.message.main_group || '');
            }
        });
    }
});


// end fetch according to custom_silvet



// main code

frappe.ui.form.on('Item', {
    onload(frm) {
        frm.set_query("custom_silvet", function () {
            return {
                query: "franchise_erp.custom.item_group.get_child_item_groups"
            };
        });
    }
});

frappe.ui.form.on("Item", {
    refresh(frm) {
        frm.set_query("custom_silvet", function () {
            return {
                filters: {
                    custom_is_silhouette: 1
                }
            };
        });
        frm.set_query("item_group", function () {
            return {
                filters: {
                    custom_is_division: 1
                }
            };
        });
        // set_item_group(frm);
    },
    // custom_departments(frm) {
    //     set_item_group(frm);
    // }
});

// frappe.ui.form.on('Item', {
//     onload(frm) {
//         // Detect duplicate item (new doc but data already filled)
//         if (frm.is_new() && frm.doc.name && frm.doc.name.startsWith('new-item')) {

//             // Clear Barcodes child table
//             frm.clear_table('barcodes');

//             // Refresh table UI
//             frm.refresh_field('barcodes');
//         }
//     }
// });
frappe.ui.form.on('Item', {
    onload(frm) {
        // Only for Duplicate / New Item
        if (frm.is_new() && frm.doc.name && frm.doc.name.startsWith('new-item')) {

            // Clear Barcodes child table
            frm.clear_table('barcodes');
            frm.refresh_field('barcodes');
        }
    },

    is_stock_item(frm) {
        // Non-stock item → item_code blank
        if (frm.doc.is_stock_item == 0) {
            frm.set_value('item_code', '');
        }
    }
});

frappe.ui.form.on("Item", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});


//for item price Row
frappe.ui.form.on("Item", {
    item_code(frm) {
        // Jab item code change ho, sab rows update ho jaye
        (frm.doc.custom_item_prices || []).forEach(row => {
            row.item_code = frm.doc.item_code;
        });
        frm.refresh_field("custom_item_prices");
    }
});

frappe.ui.form.on("Item Price Row", {
    custom_item_prices_add(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Current item ka code auto fill
        row.item_code = frm.doc.item_code;

        frm.refresh_field("custom_item_prices");
    }
});

frappe.ui.form.on("Item", {
    refresh(frm) {
        // If document is already saved
        if (!frm.is_new()) {
            frm.set_df_property("item_code", "read_only", 1);
        }
    }
});



frappe.ui.form.on('Item', {
    onload(frm) {
        // Sirf new item ke liye
        if (frm.is_new()) {

            // Agar table empty hai
            if (!frm.doc.taxes || frm.doc.taxes.length === 0) {

                let row = frm.add_child('taxes');

                // OPTIONAL: default Item Tax Template set karna ho
                // row.item_tax_template = "GST 3%";  

                frm.refresh_field('taxes');
            }
        }
    }
});
frappe.ui.form.on("Item", {
    gst_hsn_code: function (frm) {
        if (!frm.doc.gst_hsn_code) return;

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "GST HSN Code",
                name: frm.doc.gst_hsn_code
            },
            callback: function (r) {

                // Clear Item → Tax table
                frm.clear_table("taxes");

                // Case 1: HSN me Taxes present hain
                if (r.message && r.message.taxes && r.message.taxes.length > 0) {

                    r.message.taxes.forEach(hsn_row => {
                        let row = frm.add_child("taxes");

                        row.item_tax_template = hsn_row.item_tax_template;
                        row.tax_category = hsn_row.tax_category || "";
                        row.valid_from = hsn_row.valid_from || "";

                        row.minimum_net_rate = hsn_row.minimum_net_rate || 0;
                        row.maximum_net_rate = hsn_row.maximum_net_rate || 0;
                    });

                } 
                // Case 2: HSN me ek bhi Tax row nahi
                else {
                    // Add one empty row for validation/manual entry
                    frm.add_child("taxes");
                }

                frm.refresh_field("taxes");
            }
        });
    }
});

frappe.ui.form.on("Item", {
    refresh(frm) {
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "User",
                name: frappe.session.user
            },
            callback(r) {
                if (
                    r.message &&
                    r.message.role_profile_name === "SIS Counter"
                ) {
                    // 🔥 THIS is the key
                    frm.fields_dict["custom_item_prices"].grid.wrapper.hide();
                }
            }
        });
    }
});



// Logic: Hide data if user is 'SIS Counter' AND NOT an Admin/System Manager
frappe.ui.form.on('Item', {
    refresh: function(frm) {
        let user_roles = frappe.user_roles;
        let is_privileged_user = (frappe.session.user === 'Administrator' || user_roles.includes('System Manager'));
        let is_sis_counter = user_roles.includes('SIS Counter');

        if (is_sis_counter && !is_privileged_user) {
            
            // Hide the Custom Item Prices table
            frm.toggle_display('custom_item_prices', false);
            
            // Hide specific purchasing fields
            frm.toggle_display('last_purchase_rate', false);
            frm.toggle_display('is_customer_provided_item', false);
            
        } else {
            
            // Explicitly show these fields for all other roles (Admin, Stock User, etc.)
            frm.toggle_display('custom_item_prices', true);
            frm.toggle_display('last_purchase_rate', true);
            frm.toggle_display('is_customer_provided_item', true);
            
        }
    }
});

// by mayuri - Dynamic Role Check via TZU Setting
frappe.ui.form.on('Item', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // TZU Setting se data fetch karein
            frappe.db.get_doc('TZU Setting', null).then(settings => {
                if (settings.item_restricted_roles && settings.item_restricted_roles.length > 0) {
                    
                    // Check karein ki kya current user ke paas koi restricted role hai
                    let user_has_restricted_role = settings.item_restricted_roles.some(row => 
                        frappe.user_roles.includes(row.role)
                    );

                    if (user_has_restricted_role) {
                        apply_item_restrictions(frm);
                    }
                }
            });
        }
    }
});

// Restriction apply karne ka function
function apply_item_restrictions(frm) {
    frm.disable_save();
    frm.set_read_only();
    frm.page.clear_menu();

    // Forcefully lock all fields
    frm.meta.fields.forEach(df => {
        frm.set_df_property(df.fieldname, "read_only", 1);
    });
    
    // Optional: User ko message dikhane ke liye
    // frappe.show_alert({message: __("You only have read-only access to Items."), indicator: 'orange'});
}


// function set_item_group(frm) {

//     if (frm.doc.custom_departments === "All Item Groups-Non-Inventory") {
        
//         // Only set if empty (optional safe check)
//         if (!frm.doc.item_group) {
//             frm.set_value('item_group', "All Item Groups");
//         }
//     }
// }

//by jaya
frappe.ui.form.on("Item", {
    refresh(frm) {

        

            // Upload button
            frm.fields_dict['custom_item_prices'].grid.add_custom_button(__('Upload'), function () {
                new frappe.ui.FileUploader({
                    allow_multiple: false,
                    on_success: (file) => {
                        frappe.call({
                            method: "franchise_erp.custom.item_master.smart_bulk_upload",
                            args: {
                                doc: JSON.stringify(frm.doc),
                                file_url: file.file_url
                            },
                            callback: function (r) {
                                if (r.message && r.message.data) {
                                    frm.set_value("custom_item_prices", r.message.data);
                                    frm.refresh_field("custom_item_prices");
                                    frappe.msgprint(r.message.message);
                                } else {
                                    frm.reload_doc();
                                    frappe.msgprint(r.message || "Upload complete");
                                }
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

            // Optional UI fix
            setTimeout(() => {
                let grid_wrapper = frm.fields_dict['custom_item_prices'].grid.wrapper;
                let grid_footer = grid_wrapper.find('.grid-footer');

                grid_footer.css({
                    'display': 'flex',
                    'justify-content': 'space-between',
                    'align-items': 'center'
                });

                let upload_btn = grid_footer.find('.btn-custom:contains("Upload")');
                upload_btn.css('margin-left', 'auto');
                grid_footer.append(upload_btn);

                let download_btn = grid_footer.find('.btn-custom:contains("Download")');
                grid_footer.append(download_btn);
            }, 300);
        
    }
});