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
    rate(frm, cdt, cdn) {
        calculate_sis(frm, cdt, cdn);
    },
    qty(frm, cdt, cdn) {
        calculate_sis(frm, cdt, cdn);
    }
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
function calculate_sis(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row?.rate || !frm.doc.customer) return;

    frappe.call({
        method: "franchise_erp.custom.sales_invoice.calculate_sis_values",
        args: {
            customer: frm.doc.customer,
            rate: row.rate
        },
        callback(r) {
            if (!r.message) return;
            Object.keys(r.message).forEach(k => {
                frappe.model.set_value(cdt, cdn, k, r.message[k]);
            });
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
    is_return(frm) {
        toggle_incoming_logistic_button(frm);
    }
});

function handle_inter_company_grn(frm) {
    // SAFELY clear only CREATE buttons
    if (frm.page && frm.page.clear_custom_buttons) {
        frm.page.clear_custom_buttons(__("Create"));
    }

    if (frm.doc.docstatus === 1) {
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


function toggle_incoming_logistic_button(frm) {
    // SAFELY clear only CREATE buttons
    if (frm.page && frm.page.clear_custom_buttons) {
        frm.page.clear_custom_buttons(__("Create"));
    }

    if (frm.doc.is_return) {
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

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (!frm.doc.customer || frm.doc.docstatus !== 1) return;

        frappe.db.get_value(
            "Customer",
            frm.doc.customer,
            "custom_outgoing_logistics_applicable"
        ).then(r => {
            if (r.message?.custom_outgoing_logistics_applicable) {
                frm.add_custom_button(
                    __("Outgoing Logistics"),
                    () => {
                        frappe.route_options = {
                            sales_invoice_no: frm.doc.name,          
                            consignee: frm.doc.customer,         
                            owner_site: frm.doc.company,
                            transporter: frm.doc.transporter,
                            stock_point: frm.doc.set_warehouse
                        };
                        frappe.new_doc("Outgoing Logistics");
                    },
                    __("Create")
                );
            }
        });
    }
});