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
        console.log("Silvet selected:", frm.doc.custom_silvet);

        if (!frm.doc.custom_silvet) return;

        frappe.call({
            method: 'franchise_erp.custom.item_group.get_item_group_parents',
            args: {
                child_group: frm.doc.custom_silvet
            },
            callback: function (r) {
                console.log("Server response:", r.message);

                if (!r.message) return;

                frm.set_value('custom_departments', r.message.department || '');
                frm.set_value('custom_group_collection', r.message.collection || '');
                frm.set_value('item_group', r.message.main_group || '');
            }
        });
    }
});

// end fetch according to custom_silvet






// frappe.ui.form.on('Item', {
//     setup(frm) {
//         frm.set_query("custom_silvet", function () {
//             return {
//                 filters: {
//                     is_group: 0
//                 }
//             };
//         });
//     }
// });


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
// frappe.ui.form.on('Item', {
//     setup: function(frm) {
//         frm.fields_dict.custom_silvet.get_query = function(doc, cdt, cdn) {
//             return {
//                 query: "franchise_erp.custom.item_group.get_dropdown_options"
//             }
//         }
//     }
// });


// end main code


    // frappe.ui.form.on("Item", {
    //     custom_silvet(frm) {
    //         if (!frm.doc.custom_silvet) return;

    //         frappe.db.get_value(
    //             "Item Group",
    //             frm.doc.custom_silvet,
    //             "item_group_name",
    //             (r) => {
    //                 if (r) {
    //                     frm.set_value("custom_silvet", r.item_group_name);
    //                 }
    //             }
    //         );
    //     }
    // });

