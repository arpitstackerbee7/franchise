/*************************************************
 * SALES INVOICE – FINAL CLIENT SCRIPT (v15.93)
 *************************************************/

/* ------------------------------------------------
   1. Scan Product Bundle → Auto add Item
------------------------------------------------ */
frappe.ui.form.on('Sales Invoice', {
    custom_scan_product_bundle(frm) {
        if (!frm.doc.custom_scan_product_bundle) return;

        const bundle_serial = frm.doc.custom_scan_product_bundle.trim();

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Product Bundle",
                filters: { custom_bundle_serial_no: bundle_serial },
                fieldname: ["new_item_code"]
            },
            callback(r) {
                if (!r.message?.new_item_code) {
                    frappe.msgprint(__('No Item found for scanned bundle serial'));
                    frm.set_value('custom_scan_product_bundle', '');
                    return;
                }

                let row = frm.doc.items.find(d => !d.item_code) || frm.add_child('items');

                frappe.model.set_value(row.doctype, row.name, 'item_code', r.message.new_item_code);
                frappe.model.set_value(row.doctype, row.name, 'qty', row.qty || 1);

                frm.refresh_field('items');
                frm.set_value('custom_scan_product_bundle', '');
            }
        });
    }
});

/* ------------------------------------------------
   2. Hide / Show Discount fields per Item
------------------------------------------------ */
frappe.ui.form.on('Sales Invoice Item', {
    item_code(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    },
    form_render(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    },
    // item(frm, cdt, cdn) {
    //     frappe.model.set_value(cdt, cdn, "custom_sis_calculated", 0);
    //     calculate_sis(frm, cdt, cdn);
    // },
    // rate(frm, cdt, cdn) {
    //     frappe.model.set_value(cdt, cdn, "custom_sis_calculated", 0);
    //     calculate_sis(frm, cdt, cdn);
    // },
    // qty(frm, cdt, cdn) {
    //     frappe.model.set_value(cdt, cdn, "custom_sis_calculated", 0);
    //     calculate_sis(frm, cdt, cdn);
    // },
    // serial_no(frm, cdt, cdn) {
    //     frappe.model.set_value(cdt, cdn, "custom_sis_calculated", 0);
    //     setTimeout(() => {
    //         calculate_sis(frm, cdt, cdn);
    //     }, 400);
    // }
});

function apply_discount_hide(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row?.item_code) return;

    frappe.db.get_value(
        'Item',
        row.item_code,
        'custom_discount_not_allowed',
        r => {
            const hide = r?.custom_discount_not_allowed == 1;
            const fields = [
                'margin_type',
                'margin_rate_or_amount',
                'discount_percentage',
                'discount_amount',
                'distributed_discount_amount'
            ];

            fields.forEach(f =>
                frm.fields_dict.items.grid.update_docfield_property(f, 'hidden', hide)
            );

            frm.refresh_field('items');
        }
    );
}

/* ------------------------------------------------
   3. SIS Calculation
------------------------------------------------ */
// function calculate_sis(frm, cdt, cdn) {
//     const row = locals[cdt][cdn];
//     if (!row?.rate || !frm.doc.customer) return;

//     frappe.call({
//         method: "franchise_erp.custom.sales_invoice.calculate_sis_values",
//         args: {
//             customer: frm.doc.customer,
//             rate: row.rate
//         },
//         callback(r) {
//             if (!r.message) return;
//             Object.keys(r.message).forEach(k => {
//                 frappe.model.set_value(cdt, cdn, k, r.message[k]);
//             });
//         }
//     });
// }
frappe.ui.form.on('Sales Invoice', {
    validate(frm) {
        if (!frm.doc.customer) return;

        (frm.doc.items || []).forEach(row => {

            let last_qty = flt(row.custom_last_sis_qty || 0);
            let current_qty = flt(row.qty || 0);

            // Agar qty increase nahi hui → kuch mat karo
            if (current_qty <= last_qty) return;

            // Newly added qty
            let delta_qty = current_qty - last_qty;

            // Rate missing
            if (!row.rate || row.rate <= 0) return;

            calculate_sis_delta(frm, row.doctype, row.name, delta_qty);
        });
    }
});



function calculate_sis_delta(frm, cdt, cdn, delta_qty) {
    const row = locals[cdt][cdn];

    frappe.call({
        method: "franchise_erp.custom.sales_invoice.calculate_sis_values",
        args: {
            customer: frm.doc.customer,
            rate: row.rate
        },
        async: false,
        callback(r) {
            if (!r.message) return;

            // 🔹 Values for ONE qty
            let taxable_rate = flt(r.message.taxable_value);

            // 🔹 Apply only on delta qty
            let incremental_amount = taxable_rate * delta_qty;

            // 🔹 Update row totals safely
            row.amount = flt(row.amount || 0) + incremental_amount;

            frappe.model.set_value(cdt, cdn, "custom_last_sis_qty", row.qty);
        }
    });
}


/* ------------------------------------------------
   4. Due Date auto calculation
------------------------------------------------ */
frappe.ui.form.on("Sales Invoice", {
    customer(frm) {
        calculate_due_date(frm);
    },
    posting_date(frm) {
        calculate_due_date(frm);
    }
});

function calculate_due_date(frm) {
    if (!frm.doc.customer || !frm.doc.posting_date) return;

    frappe.db.get_value(
        "Customer",
        frm.doc.customer,
        "custom_credit_days",
        r => {
            if (r?.custom_credit_days == null) return;
            frm.set_value(
                "due_date",
                frappe.datetime.add_days(frm.doc.posting_date, cint(r.custom_credit_days))
            );
        }
    );
}

/* ------------------------------------------------
   5. SAFE Create Buttons (v15.93 compliant)
------------------------------------------------ */
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        handle_inter_company_grn(frm);
        toggle_incoming_logistic_button(frm);
    },
    on_submit(frm) {
        toggle_incoming_logistic_button(frm);
    }
});

function handle_inter_company_grn(frm) {
    // SAFELY clear only CREATE buttons
    if (frm.page && frm.page.clear_custom_buttons) {
        frm.page.clear_custom_buttons(__("Create"));
    }

    if (frm.doc.docstatus === 1 && frm.doc.custom_outgoing_logistics_reference) {
        frm.add_custom_button(
            __("Inter Company GRN"),
            () => {
                frappe.call({
                    method: "franchise_erp.custom.sales_invoice.create_inter_company_purchase_receipt",
                    args: {
                        sales_invoice: frm.doc.name
                    },
                    callback(r) {
                        if (r.message) {
                            frappe.set_route("Form", "Purchase Receipt", r.message);
                        }
                    }
                });
            },
            __("Create")
        );
    }
}


// function toggle_incoming_logistic_button(frm) {
//     // SAFELY clear only CREATE buttons
//     if (frm.page && frm.page.clear_custom_buttons) {
//         frm.page.clear_custom_buttons(__("Create"));
//     }

//     if (frm.doc.is_return) {
//         frm.add_custom_button(
//             __("Incoming Logistic"),
//             () => {
//                 frappe.new_doc("Incoming Logistics", {
//                     sales_invoice: frm.doc.name,
//                     consignor: frm.doc.customer,
//                     sales_inovice_no: frm.doc.name,
//                     transporter: frm.doc.transporter
//                 });
//             },
//             __("Create")
//         );
//     }
// }
function toggle_incoming_logistic_button(frm) {
    // SAFELY clear only CREATE buttons
    if (frm.page && frm.page.clear_custom_buttons) {
        frm.page.clear_custom_buttons(__("Create"));
    }

    // Show ONLY after submit
    if (frm.doc.docstatus !== 1) {
        return;
    }

    // Condition 1: Sales Invoice is Return
    if (!frm.doc.is_return || !frm.doc.customer) {
        return;
    }

    // Fetch Customer custom field
    frappe.db.get_value(
        "Customer",
        frm.doc.customer,
        "custom_gate_in_applicable",
        (r) => {
            // Condition 2: Customer custom_gate_in_applicable is checked
            if (r && r.custom_gate_in_applicable) {
                frm.add_custom_button(
                    __("Incoming Logistic"),
                    () => {
                        frappe.new_doc("Incoming Logistics", {
                            sales_invoice: frm.doc.name,
                            consignor: frm.doc.customer,
                            sales_inovice_no: frm.doc.name,
                            transporter: frm.doc.transporter
                        });
                    },
                    __("Create")
                );
            }
        }
    );
}

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        // Only for submitted invoices
        if (frm.doc.docstatus !== 1) return;

        // Prevent duplicate Outgoing Logistics
        if (frm.doc.custom_outgoing_logistics_reference) return;

        if (!frm.doc.customer) return;

        frappe.db.get_value(
            "Customer",
            frm.doc.customer,
            "custom_outgoing_logistics_applicable"
        ).then(r => {
            if (!r.message?.custom_outgoing_logistics_applicable) return;

            frm.add_custom_button(
                __("Outgoing Logistics"),
                () => {
                    frappe.new_doc("Outgoing Logistics", {}, doc => {
                        // Set parent fields
                        doc.consignee = frm.doc.customer;
                        doc.owner_site = frm.doc.company;
                        doc.transporter = frm.doc.transporter;
                        doc.stock_point = frm.doc.set_warehouse;

                        // Append child row
                        let row = frappe.model.add_child(
                            doc,
                            "sales_invoice_no",
                            "sales_invoice_no"
                        );
                        row.sales_invoice = frm.doc.name;

                        frappe.set_route("Form", "Outgoing Logistics", doc.name);
                    });
                },
                __("Create")
            );
        });
    }
});


frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        frm.set_df_property("title", "read_only", 1);
    }
});



// frappe.ui.form.on("Sales Invoice Item", {
//     item_code: function(frm, cdt, cdn) {

//     let row = locals[cdt][cdn];
//     if (!row.item_code) return;

//     // Check Product Bundle
//         frappe.call({
//             method: "frappe.client.get",
//             args: {
//             doctype: "Product Bundle",
//             name: row.item_code
//             },
//             callback: function(r) {
//             if (!r.message) return;

//             let bundle = r.message;

//             // ❌ remove scanned bundle row
//             frm.get_field("items")
//             .grid.grid_rows[row.idx - 1].remove();

//             // ✅ add child items
//             bundle.items.forEach(function(it) {

//             let child = frm.add_child("items");

//             frappe.call({
//             method: "erpnext.stock.get_item_details.get_item_details",
//             args: {
//             args: {
//             item_code: it.item_code,
//             company: frm.doc.company,
//             customer: frm.doc.customer,
//             selling_price_list: frm.doc.selling_price_list,
//             price_list_currency: frm.doc.currency,
//             plc_conversion_rate: frm.doc.plc_conversion_rate,
//             conversion_rate: frm.doc.conversion_rate,
//             qty: it.qty,
//             doctype: frm.doc.doctype,
//             name: frm.doc.name || "",
//             child_docname: child.name
//             }
//             },
//             callback: function(res) {
//             if (!res.message) return;

//             let d = res.message;

//             // set values returned by ERPNext
//             frappe.model.set_value(child.doctype, child.name, "item_code", it.item_code);
//             frappe.model.set_value(child.doctype, child.name, "qty", it.qty);
//             frappe.model.set_value(child.doctype, child.name, "uom", d.uom);
//             frappe.model.set_value(child.doctype, child.name, "price_list_rate", d.price_list_rate);
//             frappe.model.set_value(child.doctype, child.name, "rate", d.rate);
//             frappe.model.set_value(child.doctype, child.name, "item_tax_template", d.item_tax_template);

//             // 🔥 store bundle name
//             frappe.model.set_value(
//             child.doctype,
//             child.name,
//             "custom_product_bundle",
//             bundle.name
//             );
//             }
//             });
//         });

//             frm.refresh_field("items");
//             }
//         });
//     }
// });


frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        toggle_update_stock(frm);
    }
});

frappe.ui.form.on('Sales Invoice Item', {
    item_code(frm, cdt, cdn) {
        toggle_update_stock(frm);
    },
    qty(frm) {
        toggle_update_stock(frm);
    }
});

function toggle_update_stock(frm) {
    let promises = [];
    let has_stock_item = false;

    (frm.doc.items || []).forEach(row => {
        if (row.item_code) {
            let p = frappe.db.get_value(
                "Item",
                row.item_code,
                "is_stock_item"
            ).then(r => {
                if (r && r.message && r.message.is_stock_item) {
                    has_stock_item = true;
                }
            });
            promises.push(p);
        }
    });

    Promise.all(promises).then(() => {
        frm.set_value("update_stock", has_stock_item ? 1 : 0);
    });
}




frappe.ui.form.on("Sales Invoice", {
    customer: function(frm) {
        if (!frm.doc.customer) return;

        frappe.db.get_value(
            "Customer",
            frm.doc.customer,
            "custom_credit_days",
            (r) => {
                if (!r || !r.custom_credit_days) return;

                setTimeout(() => {
                    let posting_date = frm.doc.posting_date || frappe.datetime.get_today();

                    let due_date = frappe.datetime.add_days(
                        posting_date,
                        r.custom_credit_days
                    );

                    frm.set_value("due_date", due_date);
                }, 1200); // ⏱️ ERPNext ko overwrite karne ka time do
            }
        );
    },

    posting_date: function(frm) {
        if (frm.doc.customer) {
            frm.trigger("customer");
        }
    }
});
