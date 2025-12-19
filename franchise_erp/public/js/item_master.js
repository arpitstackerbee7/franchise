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
// frappe.ui.form.on('Item', {
//     setup(frm) {
//         frm.set_query("custom_silvet", function () {
//             return {
//                 query: "franchise_erp.custom.item_master.item_group_query",
//                 filters: {
//                     is_group: 0
//                 }
//             };
//         });
//     }
// });




frappe.ui.form.on('Item', {

    onload(frm) {
        set_item_group_query(frm);
    },
    refresh(frm) {
        set_item_group_query(frm);
    }
});


function set_item_group_query(frm) {
    frm.set_query('custom_silvet', () => {
        return {
            query: 'franchise_erp.custom.item_group.all_item_group_for_silvet'
        };
    });
}

// frappe.ui.form.on('Item', {
//     refresh(frm) {
//         frm.add_custom_button('Print Label', () => {
//             frappe.utils.print(
//                 frm.doctype,
//                 frm.docname,
//                 "Garment Label"
//             );
//         });
//     }
// });




// item code generate
// frappe.ui.form.on("Item", {
//     before_save(frm) {
//         generate_item_code(frm);
//     }
// });

// // Collection → F
// function getCollectionCode(text) {
//     if (!text) return "";
//     return text.trim().toUpperCase()[0];
// }

// // Department → 3PC SET
// function getDepartmentCode(text) {
//     if (!text) return "";
//     return text.trim().toUpperCase().replace(/\s+/g, " ");
// }

// // Silvet / Style → AK
// function getStyleCode(text) {
//     if (!text) return "";
//     let words = text.trim().toUpperCase().split(" ");
//     if (words.length >= 2) {
//         return words[0][0] + words[1][0];
//     }
//     return text.substring(0, 2).toUpperCase();
// }

// // MAIN FUNCTION
// function generate_item_code(frm) {

//     // 🔹 EXACT SAME FIELDS as working console code
//     let collection = frm.doc.custom_group_collection || "";
//     let dept = frm.doc.custom_departments || "";
//     let silvet = frm.doc.custom_silvet || "";
//     let auto_no = frm.doc.custom_auto_no || 31;
//     let colour_code = frm.doc.custom_colour_code || "MV";

//     let final_code = `${getCollectionCode(collection)}-${getDepartmentCode(dept)}-${getStyleCode(silvet)}-${auto_no
//         .toString()
//         .padStart(3, "0")}-${colour_code}`;

//     console.log("Generated Item Code:", final_code);

//     frm.set_value("item_code", final_code);
// }

// frappe.ui.form.on("Item", {
//     before_save(frm) {
//         generate_item_code(frm);
//     }
// });

// // Helper functions
// function getCollectionCode(text) {
//     if (!text) return "";
//     return text.trim().toUpperCase()[0];
// }

// function getDepartmentCode(text) {
//     if (!text) return "";
//     return text.trim().toUpperCase().replace(/\s+/g, " ");
// }

// function getStyleCode(text) {
//     if (!text) return "";
//     let words = text.trim().toUpperCase().split(" ");
//     if (words.length >= 2) {
//         return words[0][0] + words[1][0];
//     }
//     return text.substring(0, 2).toUpperCase();
// }

// // MAIN FUNCTION
// function generate_item_code(frm) {

//     // New item ke liye hi auto_no generate karo
//     if (!frm.is_new()) return;

//     frappe.call({
//         method: "franchise_erp.custom.item_master.get_next_item_no",
//         callback: function (r) {
//             if (!r.message) return;

//             let auto_no = r.message; // 25
//             let padded_no = auto_no.toString().padStart(3, "0"); // 025

//             let collection = frm.doc.custom_group_collection || "";
//             let dept = frm.doc.custom_departments || "";
//             let silvet = frm.doc.custom_silvet || "";
//             let colour_code = frm.doc.custom_colour_code || "MV";

//             let final_code = `${getCollectionCode(collection)}-${getDepartmentCode(dept)}-${getStyleCode(silvet)}-${padded_no}-${colour_code}`;

//             console.log("Generated Item Code:", final_code);

//             frm.set_value("item_code", final_code);
//         }
//     });
// }

