
frappe.ui.form.on('Sales Invoice', {
    custom_scan_product_bundle(frm) {
        if (!frm.doc.custom_scan_product_bundle) return;

        let bundle_serial = frm.doc.custom_scan_product_bundle.trim();

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Product Bundle",
                filters: {
                    custom_bundle_serial_no: bundle_serial
                },
                fieldname: ["new_item_code"]
            },
            callback(r) {
                if (!r.message || !r.message.new_item_code) {
                    frappe.msgprint(__('No Item found for scanned bundle serial'));
                    frm.set_value('custom_scan_product_bundle', '');
                    return;
                }

                let item_code = r.message.new_item_code;

                // Find empty row or create new
                let row = frm.doc.items.find(d => !d.item_code);
                if (!row) row = frm.add_child('items');

                // 🔥 THIS IS THE KEY FIX
                frappe.model.set_value(row.doctype, row.name, 'item_code', item_code);

                // qty AFTER item is set
                frappe.model.set_value(row.doctype, row.name, 'qty', row.qty || 1);

                frm.refresh_field('items');

                frm.set_value('custom_scan_product_bundle', '');
            }
        });
    }
});

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
// frappe.ui.form.on("Sales Invoice Item", {
//     custom_margins_: function(frm, cdt, cdn) {
//         frm.refresh_field("items");
//     },
//     custom_margin_amount: function(frm, cdt, cdn) {
//         frm.refresh_field("items");
//     },
//     custom_total_invoice_amount: function(frm, cdt, cdn) {
//         frm.refresh_field("items");
//     }
// });

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


frappe.ui.form.on("Sales Invoice Item", {
    rate(frm, cdt, cdn) {
        calculate_sis(frm, cdt, cdn);
    },
    qty(frm, cdt, cdn) {
        calculate_sis(frm, cdt, cdn);
    }
});


function calculate_sis(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (!row.rate || !frm.doc.customer) return;

    frappe.call({
        method: "franchise_erp.custom.sales_invoice.calculate_sis_values",
        args: {
            customer: frm.doc.customer,
            rate: row.rate
        },
       callback: function (r) {
    if (!r.message) return;

    let d = r.message;

    // Custom fields
    frappe.model.set_value(cdt, cdn, "custom_output_gst_", d.custom_output_gst_);
    frappe.model.set_value(cdt, cdn, "custom_output_gst_value", d.custom_output_gst_value);
    frappe.model.set_value(cdt, cdn, "custom_margins_", d.custom_margins_);
    frappe.model.set_value(cdt, cdn, "custom_margin_amount", d.custom_margin_amount);
    frappe.model.set_value(cdt, cdn, "custom_net_sale_value", d.custom_net_sale_value);
    frappe.model.set_value(cdt, cdn, "custom_total_invoice_amount", d.custom_total_invoice_amount);

   
}

    });
}




// arpit
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Inter Company GRN'), function() {
                frappe.call({
                    method: "franchise_erp.custom.sales_invoice.create_inter_company_purchase_receipt",
                    args: { sales_invoice: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route("Form", "Purchase Receipt", r.message);
                        }
                    }
                });
            }, __('Create'));
        }
    }
});
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        // Only after submit
        if (frm.doc.docstatus !== 1) return;

        frm.add_custom_button(
            __("Inter Company GRN"),
            () => {
                // Prepare items from Sales Invoice
                let pr_items = (frm.doc.items || []).map(row => ({
                    item_code: row.item_code,
                    item_name: row.item_name,
                    qty: row.qty,
                    uom: row.uom,
                    stock_uom: row.stock_uom,
                    conversion_factor: row.conversion_factor,
                    rate: row.rate,
                    amount: row.amount,
                    warehouse: row.warehouse,
                    sales_invoice_item: row.name   // optional reference
                }));

                // Create new Purchase Receipt
                frappe.new_doc("Purchase Receipt", {
                    supplier: frm.doc.customer,          // inter-company supplier
                    company: frm.doc.company,
                    posting_date: frm.doc.posting_date,
                    posting_time: frm.doc.posting_time,
                    set_posting_time: 1,

                    // Reference
                    bill_no: frm.doc.name,
                    remarks: `Inter Company GRN against Sales Invoice ${frm.doc.name}`,

                    items: pr_items
                });
            },
            __("Create")
        );
    }
});




frappe.ui.form.on("Sales Invoice", {
    customer: function (frm) {
        calculate_due_date(frm);
    },

    posting_date: function (frm) {
        if (frm.doc.customer) {
            calculate_due_date(frm);
        }
    }
});

function calculate_due_date(frm) {
    if (!frm.doc.customer || !frm.doc.posting_date) return;

    frappe.db.get_value(
        "Customer",
        frm.doc.customer,
        "custom_credit_days",
        function (r) {
            if (!r || r.custom_credit_days == null) return;

            let days = cint(r.custom_credit_days);
            let base_date = frm.doc.posting_date;

            frappe.after_ajax(() => {
                setTimeout(() => {
                    // safety check
                    if (!frm.doc.due_date || frm.is_new()) {
                        let due_date = frappe.datetime.add_days(base_date, days);
                        frm.set_value("due_date", due_date);
                    }
                }, 300);
            });
        }
    );
}


frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        toggle_incoming_logistic_button(frm);
    },

    is_return(frm) {   // 👈 if your field is `s_return`, replace is_return with s_return
        toggle_incoming_logistic_button(frm);
    }
});

function toggle_incoming_logistic_button(frm) {
    // Remove button first (avoid duplicates)
    frm.remove_custom_button("Incoming Logistic");

    // Show button only when Return is checked
    if (frm.doc.is_return) {   // or frm.doc.s_return
        frm.add_custom_button(
            __("Incoming Logistic"),
            () => {
                // Example action
                frappe.new_doc("Incoming Logistics", {
                    sales_invoice: frm.doc.name,
                    consignor: frm.doc.customer,
                    sales_inovice_no: frm.doc.name,
                    transporter:frm.doc.transporter,
                });
            }
        );
    }
}
