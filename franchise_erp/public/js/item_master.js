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
    }
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

