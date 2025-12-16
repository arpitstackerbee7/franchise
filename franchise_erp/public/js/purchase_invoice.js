// frappe.ui.form.on('Purchase Invoice', {
//     before_submit: function(frm) {
//         const current_user = frappe.session.user;
//         const is_return = frm.doc.is_return;
//         const owner = frm.doc.owner;
// console.log('cu:',current_user)
// console.log('ir:',is_return)
// console.log('o:',owner)
//         // Allow Administrator always
//         if (current_user === "Administrator") {
//             return;
//         }

//         // Normal PI: owner (supplier) cannot submit
//         if (is_return === 0 && current_user === owner) {
//             frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
//             frappe.validated = false;
//             return;
//         }


//         // Return PI: supplier (owner) cannot submit
//         if (is_return === 1 && current_user === owner) {
//             frappe.msgprint("Supplier cannot submit Return Purchase Invoice");
//             frappe.validated = false;
//             return;
//         }
//     }
// });
frappe.ui.form.on('Purchase Invoice', {
    before_submit: async function (frm) {
        const current_user = frappe.session.user;
        const is_return = frm.doc.is_return;
        const owner = frm.doc.owner;
        const represents_company = frm.doc.represents_company;

        // --- GET modified_by FROM PURCHASE INVOICE itself ---
        let modify = frm.doc.modified_by;

        console.log("cu:", current_user);
        console.log("ir:", is_return);
        console.log("o:", owner);
        console.log("modify:", modify);
        console.log("re c:", represents_company);
        // Allow Administrator
        if (current_user === "Administrator") {
            return;
        }

        // Normal PI: owner cannot submit
        if (is_return === 0 && current_user === owner && represents_company !== "") {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Return PI: owner cannot submit
        if (is_return === 1 && current_user === owner) {
            frappe.msgprint("Supplier cannot submit Return Purchase Invoice");
            frappe.validated = false;
            return;
        }
    }
});

// append value in item table
frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        if (!frm.doc.is_internal_supplier) return;
        apply_gst_on_items(frm);
    },

    items_add(frm) {
        if (!frm.doc.is_internal_supplier) return;
        apply_gst_on_items(frm);
    }
});

function apply_gst_on_items(frm) {
    (frm.doc.items || []).forEach(item => {

        if (!item.custom_total_invoice_amount) return;
        if (item.item_tax_template) return; // already applied

        let taxable = flt(item.custom_total_invoice_amount);
        let gst_rate = taxable <= 2500 ? 5 : 18;

        frappe.call({
            method: "franchise_erp.custom.purchase_invoice_hooks.get_item_tax_template",
            args: {
                company: frm.doc.company,
                gst_rate: gst_rate
            },
            callback(r) {
                if (!r.message) {
                    frappe.msgprint(`GST ${gst_rate}% Item Tax Template not found`);
                    return;
                }

                frappe.model.set_value(item.doctype, item.name, {
                    item_tax_template: r.message,
                    rate: taxable
                });

                // IMPORTANT
                frm.trigger("calculate_taxes_and_totals");
            }
        });
    });
}
