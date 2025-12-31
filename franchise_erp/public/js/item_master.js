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