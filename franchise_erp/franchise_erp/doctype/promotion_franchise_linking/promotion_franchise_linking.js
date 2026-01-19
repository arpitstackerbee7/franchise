// frappe.ui.form.on("Promotion Franchise linking", {
//     refresh : function(frm) {
//         frm.set_query("franchises_promotional_scheme", function() {
//             return {
//                 "filters": {
//                     "custom_is_template": 1,
                    
//                 }
//             };
//         });
//     },
//     create_promotions: function(frm) {
//         if (!frm.doc.franchises_promotional_scheme || !frm.doc.franchises.length) {
//             frappe.msgprint("Promotion aur Franchise select karo");
//             return;
//         }

//         frappe.call({
//             method: "franchise_erp.franchise_erp.doctype.promotion_franchise_linking.promotion_franchise_linking.create_promotion_for_companies",
//             args: {
//                 promotion_name: frm.doc.franchises_promotional_scheme,
//                 companies: frm.doc.franchises.map(row => row.franchise)
//             },
//             callback: function(r) {
//                 if (r.message && r.message.length) {
//                     frappe.msgprint({
//                         title: "Success",
//                         message: "Total " + r.message.length + " promotions created",
//                         indicator: "green"
//                     });
//                 } else {
//                     frappe.msgprint("No promotion created");
//                 }
//             }
//         });
//     }
// });





frappe.ui.form.on("Promotion Franchise linking", {

    refresh: function(frm) {
        frm.set_query("franchises_promotional_scheme", function() {
            return {
                filters: {
                    custom_is_template: 1
                }
            };
        });
    },

    // CREATE
    create_promotions: function(frm) {
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.promotion_franchise_linking.promotion_franchise_linking.create_promotion_for_companies",
            args: {
                promotion_name: frm.doc.franchises_promotional_scheme,
                companies: frm.doc.franchises,
                valid_from: frm.doc.valid_from,
                valid_upto: frm.doc.valid_upto
            },
            callback: function(r) {
                frappe.msgprint("Promotions Created Successfully");
            }
        });
    },
    
    sync_status: function(frm) {
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.promotion_franchise_linking.promotion_franchise_linking.sync_promotion_status",
            args: {
                promotion_name: frm.doc.franchises_promotional_scheme,
                franchises: frm.doc.franchises,
                valid_from: frm.doc.valid_from,
                valid_upto: frm.doc.valid_upto   
            },
            callback: function() {
                frappe.msgprint("Status & Dates Synced Successfully");
            }
        });
    },
    
    // DELETE
    delete_promotions: function(frm) {
        let selected = frm.get_selected();
    
        if (!selected || !selected.franchises || !selected.franchises.length) {
            frappe.msgprint("Pehle child table se koi row select karo");
            return;
        }
    
        // selected rows ka actual data nikaalo
        let selected_rows = selected.franchises.map(name => {
            return frm.doc.franchises.find(r => r.name === name);
        });
    
        frappe.confirm(
            "Selected promotions delete karni hain?",
            function() {
                frappe.call({
                    method: "franchise_erp.franchise_erp.doctype.promotion_franchise_linking.promotion_franchise_linking.delete_promotions",
                    args: {
                        promotion_name: frm.doc.franchises_promotional_scheme,
                        franchises: selected_rows
                    },
                    callback: function(r) {
                        if (r.message && r.message.length) {
    
                            // Child table se sirf selected rows hatao
                            let remaining = frm.doc.franchises.filter(row => {
                                return !r.message.includes(row.franchise);
                            });
    
                            frm.clear_table("franchises");
                            remaining.forEach(row => {
                                let child = frm.add_child("franchises");
                                Object.assign(child, row);
                            });
    
                            frm.refresh_field("franchises");
    
                            frappe.msgprint({
                                title: "Deleted",
                                message: "Deleted Promotions for: " + r.message.join(", "),
                                indicator: "red"
                            });
                        }
                    }
                });
            }
        );
    }
    

});
