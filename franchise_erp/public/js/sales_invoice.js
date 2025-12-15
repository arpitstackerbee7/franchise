frappe.ui.form.on('Sales Invoice Item', {
    item_code: function(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    },

    form_render: function(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    }
});

function apply_discount_hide(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (!row || !row.item_code) return;

    frappe.db.get_value(
        'Item',
        row.item_code,
        'custom_discount_not_allowed',
        function(r) {
            if (r && r.custom_discount_not_allowed == 1) {

                // ✅ Hide Fields
                frm.fields_dict['items'].grid.update_docfield_property('margin_type', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('margin_rate_or_amount', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('discount_percentage', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('discount_amount', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('distributed_discount_amount', 'hidden', 1);

            } else {

                // ✅ Show Fields Again
                frm.fields_dict['items'].grid.update_docfield_property('margin_type', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('margin_rate_or_amount', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('discount_percentage', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('discount_amount', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('distributed_discount_amount', 'hidden', 0);

            }

            frm.refresh_field('items');
        }
    );
}

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        frm.refresh_field("items");
    },
    onload_post_render(frm) {
        frm.refresh_field("items");
    }
});

frappe.ui.form.on("Sales Invoice Item", {
    custom_margins_: function(frm, cdt, cdn) {
        frm.refresh_field("items");
    },
    custom_margin_amount: function(frm, cdt, cdn) {
        frm.refresh_field("items");
    },
    custom_total_invoice_amount: function(frm, cdt, cdn) {
        frm.refresh_field("items");
    }
});

// frappe.ui.form.on("Sales Invoice", {
//     refresh(frm) {
//         if (frm.doc.items && frm.doc.items.length > 0) {
//             // Recalculate totals on load/refresh
//             (frm.doc.items || []).forEach(row => {
//                 apply_margin_and_calculate(frm, row);
//             });
//         }
//     }
// });


// let selected_customer_company = null;

// frappe.ui.form.on("Sales Invoice", {
//     refresh(frm) {

//         // Customer company fetch again
//         if (frm.doc.customer) {
//             frappe.call({
//                 method: "frappe.client.get_value",
//                 args: {
//                     doctype: "Customer",
//                     filters: { name: frm.doc.customer },
//                     fieldname: "represents_company"
//                 },
//                 callback(r) {
//                     if (r.message?.represents_company) {
//                         selected_customer_company = r.message.represents_company;
//                     }
//                 }
//             });
//         }

//         // Recalculate margin & totals for all items
//         if (frm.doc.items?.length) {
//             frm.doc.items.forEach(row => {
//                 apply_margin_and_calculate(frm, row);
//             });
//         }
//     }
// });

// frappe.ui.form.on("Sales Invoice Item", {

//     item_code(frm, cdt, cdn) {
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },

//     rate(frm, cdt, cdn) {
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },

//     qty(frm, cdt, cdn) {
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },

//     net_rate(frm, cdt, cdn) {
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },

//     base_net_rate(frm, cdt, cdn) {
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },

//     item_tax_template(frm, cdt, cdn) { 
//         apply_margin_and_calculate(frm, frappe.get_doc(cdt, cdn));
//     },
// });
// function get_sis_margin(company, callback) {
//     frappe.call({
//         method: "frappe.client.get_list",
//         args: {
//             doctype: "SIS Configuration",
//             filters: { company: company },
//             fields: ["fresh_margin"],
//             limit_page_length: 1
//         },
//         callback(r) {
//             callback(flt(r.message?.length ? r.message[0].fresh_margin : 0));
//         }
//     });
// }
// function apply_margin_and_calculate(frm, row) {

//     frappe.timeout(0.1).then(() => {

//         let company = selected_customer_company || frm.doc.company;

//         let rate = flt(row.rate || 0);          // Base Rate
//         let qty = flt(row.qty || 1);            // Quantity
//         let net_rate = flt(row.net_rate || 0);  // Final rate after GST

//         if (!net_rate) return; // GST अभी calculate नहीं हुआ

//         get_sis_margin(company, function (margin_percent) {

//             row.custom_margins_ = margin_percent;

//             // ✔ Correct margin on NET RATE × QTY
//             let margin_amount = flt((rate * margin_percent / 100) * qty);
//             row.custom_margin_amount = margin_amount;

//             // ✔ Final formula (net total - margin)
//             let final_amount = flt((net_rate * qty) - margin_amount);
//             row.custom_total_invoice_amount = final_amount;

//             console.log("Rate:", rate);
//             console.log("Qty:", qty);
//             console.log("Net Rate:", net_rate);
//             console.log("Margin %:", margin_percent);
//             console.log("Margin Amt:", row.custom_margin_amount);
//             console.log("Final Amount:", final_amount);

//             frm.refresh_field("items");
//             update_total_invoice_amount(frm);
//         });

//     });
// }
// // function set_custom_round_total(frm, total) {
// //     // Round to 1 decimal correctly
// //     let rounded = Math.round(total * 10) / 10;

// //     // Optional: normalize floating point (make sure it's shown as 1 decimal)
// //     rounded = parseFloat(rounded.toFixed(1));

// //     frm.set_value("rounded_total", rounded);
// // }

// function update_total_invoice_amount(frm) {
//     let total = 0;

//     (frm.doc.items || []).forEach(item => {
//         total += flt(item.custom_total_invoice_amount || 0);
//     });

//     // Store only in YOUR custom field
//     frm.set_value("custom_total_invoice_amount", total);
//     frm.set_value("grand_total", total);
//     frm.set_value("rounded_total", total);

//     // DO NOT touch ERPNext system totals
//     frm.trigger("calculate_taxes_and_totals");
// }

// function update_total_invoice_amount(frm) {
//     let total = 0;

//     (frm.doc.items || []).forEach(item => {
//         total += flt(item.custom_total_invoice_amount || 0);
//     });

//     // Append to invoice grand total (you can change target field name)
//     // frm.set_value("custom_total_invoice_amount", total);
//     frm.set_value("grand_total", total);
//     frm.set_value("rounded_total", total);
//     // set_custom_round_total(frm, total);
//     frm.set_value("outstanding_amount", total);
// }

