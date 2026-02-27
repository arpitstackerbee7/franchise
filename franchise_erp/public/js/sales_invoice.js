/*************************************************
 * SALES INVOICE – OPTIMIZED CLIENT SCRIPT
 *************************************************/

/* =====================================================
   MAIN FORM EVENTS (Single Block – No Override)
===================================================== */
frappe.ui.form.on("Sales Invoice", {

    refresh(frm) {

        // Read Only Title
        frm.set_df_property("title", "read_only", 1);

        // Button handlers
        handle_inter_company_grn(frm);
        toggle_incoming_logistic_button(frm);
        toggle_outgoing_logistics_button(frm);

        // Update stock auto check
        toggle_update_stock(frm);

        // Make negative for return
        if (frm.doc.is_return) {
            make_items_negative(frm);
        }

        // Export Button
        add_export_button(frm);
    },

    customer(frm) {

        if (frm.doc.payment_terms_template) {
            frm.set_value("payment_terms_template", "");
        }

        setTimeout(() => {
            set_custom_due_date(frm);
        }, 500);
    },

    posting_date(frm) {
        calculate_due_date(frm);
    },

    is_return(frm) {
        if (frm.doc.is_return) {
            make_items_negative(frm);
        }
    },

    validate(frm) {
        handle_sis_calculation(frm);
    },

    // custom_scan_product_bundle(frm) {
    //     scan_product_bundle(frm);
    // },
    
    
});


/* =====================================================
   SALES INVOICE ITEM EVENTS
===================================================== */
// frappe.ui.form.on("Sales Invoice Item", {

//     item_code(frm, cdt, cdn) {

//         let row = locals[cdt][cdn];

//         if (!row.item_code) return;

//         // ❌ Agar scan se nahi aaya hai
//         if (!frm.__from_barcode_scan) {

//             frappe.msgprint({
//                 title: "Not Allowed",
//                 message: "Please scan barcode/item name",
//                 indicator: "red"
//             });

//             row.item_code = "";
//             frm.refresh_field("items");
//             return;
//         }

//         apply_discount_hide(frm, cdt, cdn);
//         toggle_update_stock(frm);
//     },

//     qty(frm, cdt, cdn) {
//         toggle_update_stock(frm);

//         if (frm.doc.is_return) {
//             let row = locals[cdt][cdn];
//             if (row.qty > 0) {
//                 frappe.model.set_value(cdt, cdn, "qty", -Math.abs(row.qty));
//             }
//         }
//     },

//     serial_no(frm, cdt, cdn) {
//         if (!frm.doc.is_return) return;

//         setTimeout(() => {
//             let row = locals[cdt][cdn];
//             if (!row.serial_no) return;

//             let count = row.serial_no.split("\n").filter(s => s.trim()).length;

//             frappe.model.set_value(cdt, cdn, "qty", -Math.abs(count));
//         }, 300);
//     }
// });

frappe.ui.form.on("Sales Invoice Item", {

    item_code(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.item_code) return;

        // ✅ Agar serial_no present hai (scan case) → allow
        if (row.serial_no && row.serial_no.trim() !== "") {

            apply_discount_hide(frm, cdt, cdn);
            toggle_update_stock(frm);
            return;
        }

        // ❌ Manual selection case
        frappe.msgprint({
            title: "Not Allowed",
            message: "Please scan barcode/item name",
            indicator: "red"
        });

        frappe.model.set_value(cdt, cdn, "item_code", "");
    },

    qty(frm, cdt, cdn) {
        toggle_update_stock(frm);

        if (frm.doc.is_return) {
            let row = locals[cdt][cdn];
            if (row.qty > 0) {
                frappe.model.set_value(cdt, cdn, "qty", -Math.abs(row.qty));
            }
        }
    },

    serial_no(frm, cdt, cdn) {
        if (!frm.doc.is_return) return;

        setTimeout(() => {
            let row = locals[cdt][cdn];
            if (!row.serial_no) return;

            let count = row.serial_no.split("\n").filter(s => s.trim()).length;
            frappe.model.set_value(cdt, cdn, "qty", -Math.abs(count));
        }, 300);
    }
});
/* =====================================================
   PRODUCT BUNDLE SCAN
===================================================== */
let scan_lock = false;

function scan_product_bundle(frm) {

    if (scan_lock) return;
    if (!frm.doc.custom_scan_product_bundle) return;

    scan_lock = true;

    let serial = frm.doc.custom_scan_product_bundle.trim();

    frappe.db.get_value(
        "Product Bundle",
        { custom_bundle_serial_no: serial },
        ["new_item_code"]
    ).then(r => {

        if (!r.message?.new_item_code) {
            frappe.msgprint("No Item found for scanned bundle serial");
            frm.set_value("custom_scan_product_bundle", "");
            scan_lock = false;
            return;
        }

        let row = frm.add_child("items");

        // ✅ MARK THIS ROW AS SCANNED
        row.__from_scan = true;

        frappe.model.set_value(row.doctype, row.name, "item_code", r.message.new_item_code);
        frappe.model.set_value(row.doctype, row.name, "serial_no", serial);
        frappe.model.set_value(row.doctype, row.name, "qty", 1);

        frm.refresh_field("items");
        frm.set_value("custom_scan_product_bundle", "");

        setTimeout(() => {
            scan_lock = false;
        }, 400);
    });
}

/* =====================================================
   DISCOUNT HIDE
===================================================== */
function apply_discount_hide(frm, cdt, cdn) {

    let row = locals[cdt][cdn];
    if (!row?.item_code) return;

    frappe.db.get_value("Item", row.item_code, "custom_discount_not_allowed")
        .then(r => {

            let hide = r.message?.custom_discount_not_allowed == 1;

            [
                "margin_type",
                "margin_rate_or_amount",
                "discount_percentage",
                "discount_amount",
                "distributed_discount_amount"
            ].forEach(f => {
                frm.fields_dict.items.grid.update_docfield_property(f, "hidden", hide);
            });

            frm.refresh_field("items");
        });
}


/* =====================================================
   SIS CALCULATION
===================================================== */
function handle_sis_calculation(frm) {

    if (!frm.doc.customer) return;

    (frm.doc.items || []).forEach(row => {

        let last_qty = flt(row.custom_last_sis_qty || 0);
        let current_qty = flt(row.qty || 0);

        if (current_qty <= last_qty || !row.rate) return;

        let delta = current_qty - last_qty;

        frappe.call({
            method: "franchise_erp.custom.sales_invoice.calculate_sis_values",
            args: {
                customer: frm.doc.customer,
                rate: row.rate
            },
            async: false,
            callback(r) {

                if (!r.message) return;

                let taxable_rate = flt(r.message.taxable_value);
                row.amount = flt(row.amount || 0) + (taxable_rate * delta);

                frappe.model.set_value(row.doctype, row.name, "custom_last_sis_qty", row.qty);
            }
        });
    });
}


/* =====================================================
   DUE DATE
===================================================== */
function set_custom_due_date(frm) {

    if (!frm.doc.customer || !frm.doc.posting_date) return;

    frappe.db.get_value("Customer", frm.doc.customer, "custom_credit_days")
        .then(r => {

            let credit_days = cint(r.message?.custom_credit_days || 0);
            if (!credit_days) return;

            frm.set_value(
                "due_date",
                frappe.datetime.add_days(frm.doc.posting_date, credit_days)
            );
        });
}

/* =====================================================
   UPDATE STOCK AUTO
===================================================== */
function toggle_update_stock(frm) {

    let promises = [];

    (frm.doc.items || []).forEach(row => {
        if (row.item_code) {
            promises.push(
                frappe.db.get_value("Item", row.item_code, "is_stock_item")
            );
        }
    });

    Promise.all(promises).then(results => {

        let has_stock = results.some(r => r.message?.is_stock_item);

        frm.set_value("update_stock", has_stock ? 1 : 0);
    });
}


/* =====================================================
   RETURN NEGATIVE
===================================================== */
function make_items_negative(frm) {

    (frm.doc.items || []).forEach(row => {

        if (row.serial_no) {

            let count = row.serial_no.split("\n").filter(s => s.trim()).length;

            frappe.model.set_value(row.doctype, row.name, "qty", -Math.abs(count));

        } else if (row.qty > 0) {

            frappe.model.set_value(row.doctype, row.name, "qty", -Math.abs(row.qty));
        }
    });
}


/* =====================================================
   BUTTONS
===================================================== */
function handle_inter_company_grn(frm) {

    if (frm.doc.docstatus !== 1 || !frm.doc.custom_outgoing_logistics_reference)
        return;

    frm.add_custom_button("Inter Company GRN", () => {

        frappe.call({
            method: "franchise_erp.custom.sales_invoice.create_inter_company_purchase_receipt",
            args: { sales_invoice: frm.doc.name },
            callback(r) {
                if (r.message) {
                    frappe.set_route("Form", "Purchase Receipt", r.message);
                }
            }
        });

    }, "Create");
}


function toggle_incoming_logistic_button(frm) {

    if (frm.doc.docstatus !== 1 || !frm.doc.is_return || !frm.doc.customer)
        return;

    frappe.db.get_value("Customer", frm.doc.customer, "custom_gate_in_applicable")
        .then(r => {

            if (!r.message?.custom_gate_in_applicable) return;

            frm.add_custom_button("Incoming Logistic", () => {

                frappe.new_doc("Incoming Logistics", {
                    sales_invoice: frm.doc.name,
                    consignor: frm.doc.customer,
                    sales_inovice_no: frm.doc.name,
                    transporter: frm.doc.transporter
                });

            }, "Create");
        });
}


function toggle_outgoing_logistics_button(frm) {

    if (frm.doc.docstatus !== 1 || !frm.doc.customer)
        return;

    let ref = frm.doc.custom_outgoing_logistics_reference;

    if (ref) {

        frappe.db.get_value("Outgoing Logistics", ref, "docstatus")
            .then(r => {
                if (r.message?.docstatus === 1) return;
                add_outgoing_logistics_button(frm);
            });

    } else {
        add_outgoing_logistics_button(frm);
    }
}


function add_outgoing_logistics_button(frm) {

    frappe.db.get_value("Customer", frm.doc.customer, "custom_outgoing_logistics_applicable")
        .then(r => {

            if (!r.message?.custom_outgoing_logistics_applicable) return;

            frm.add_custom_button("Outgoing Logistics", () => {

                let address_name =
                    frm.doc.shipping_address_name ||
                    frm.doc.customer_address;

                if (!address_name) {
                    frappe.msgprint("No Shipping or Billing Address found.");
                    return;
                }

                frappe.db.get_value("Address", address_name, ["city", "custom_citytown"])
                    .then(addr => {

                        let city =
                            addr.message?.custom_citytown ||
                            addr.message?.city || "";

                        frappe.new_doc("Outgoing Logistics", {}, doc => {

                            doc.consignee = frm.doc.customer;
                            doc.owner_site = frm.doc.company;
                            doc.transporter = frm.doc.transporter;
                            doc.stock_point = frm.doc.set_warehouse;
                            doc.type = "Sales Invoice";
                            doc.station_to = city;

                            let row = frappe.model.add_child(doc, "references", "references");
                            row.source_doctype = "Sales Invoice";
                            row.source_name = frm.doc.name;
                        });

                    });

            }, "Create");
        });
}


/* =====================================================
   EXPORT PACKING EXCEL (Final Optimized)
===================================================== */

function add_export_button(frm) {

    // Prevent duplicate button on refresh
    if (frm.__export_button_added) return;
    frm.__export_button_added = true;

    frm.add_custom_button("Export Packing Excel", async () => {

        if (!frm.doc.items || !frm.doc.items.length) {
            frappe.msgprint("No items found to export.");
            return;
        }

        // Unique + valid item codes
        let item_codes = [
            ...new Set(
                frm.doc.items
                    .map(i => i.item_code)
                    .filter(Boolean)
            )
        ];

        if (!item_codes.length) {
            frappe.msgprint("No valid item codes found.");
            return;
        }

        // Fetch item master data
        let items = await frappe.db.get_list("Item", {
            filters: { name: ["in", item_codes] },
            fields: [
                "name",
                "custom_group_collection",
                "custom_top_fabrics",
                "custom_colour_name",
                "custom_size"
            ],
            limit: 500
        });

        let item_map = {};
        (items || []).forEach(d => item_map[d.name] = d);

        generate_fixed_excel(frm, item_map);

    }, "Actions");
}



/* =====================================================
   GENERATE EXCEL FILE
===================================================== */

function generate_fixed_excel(frm, item_map) {

    let items = frm.doc.items || [];
    let totalQty = 0;
    let totalAmt = 0;

    let rows = [];

    items.forEach(item => {

        let m = item_map[item.item_code] || {};

        let qty = flt(item.qty);
        let amt = flt(item.amount);

        totalQty += qty;
        totalAmt += amt;

        rows.push(`
            <tr>
                <td>${frm.doc.name || ''}</td>
                <td>${frm.doc.posting_date || ''}</td>
                <td>${item.serial_no ? item.serial_no.split('\n')[0] : ''}</td>
                <td>${item.gst_hsn_code || ''}</td>
                <td>${item.item_code || ''}</td>
                <td>${m.custom_group_collection || ''}</td>
                <td>${m.custom_top_fabrics || ''}</td>
                <td>${m.custom_colour_name || ''}</td>
                <td>${m.custom_size || ''}</td>
                <td align="center">${qty}</td>
                <td align="right">${flt(item.price_list_rate)}</td>
                <td align="right">${amt.toFixed(2)}</td>
            </tr>
        `);
    });

    let excel_html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office"
              xmlns:x="urn:schemas-microsoft-com:office:excel"
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta http-equiv="content-type"
                  content="application/vnd.ms-excel; charset=UTF-8">
            <style>
                td, th {
                    border: 0.5pt solid #000;
                    font-family: Calibri, sans-serif;
                    font-size: 10pt;
                    padding: 5px;
                }
                .title {
                    font-size: 14pt;
                    font-weight: bold;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <table border="1">

                <tr>
                    <th colspan="12"
                        bgcolor="#FFFF00"
                        style="height:35pt; vertical-align:middle;"
                        class="title">
                        ${(frm.doc.customer_name || '').toUpperCase()} - PACKING SLIP FORMAT
                    </th>
                </tr>

                <tr bgcolor="#E0E0E0">
                    <th width="120">Invoice No.</th>
                    <th width="100">Invoice date</th>
                    <th width="200">Serial No./BARCODE</th>
                    <th width="90">HSN Code</th>
                    <th width="120">STYLE NO</th>
                    <th width="200">Department</th>
                    <th width="100">FABRIC</th>
                    <th width="100">COLOR</th>
                    <th width="100">SIZE</th>
                    <th width="70">QTY</th>
                    <th width="100">MRP</th>
                    <th width="120">Gross Amount</th>
                </tr>

                ${rows.join("")}

                <tr style="font-weight:bold;">
                    <td colspan="8" align="right">TOTAL</td>
                    <td></td>
                    <td align="center" bgcolor="#F2F2F2">${totalQty}</td>
                    <td></td>
                    <td align="right" bgcolor="#F2F2F2">${totalAmt.toFixed(2)}</td>
                </tr>

            </table>
        </body>
        </html>
    `;

    let blob = new Blob([excel_html], {
        type: 'application/vnd.ms-excel'
    });

    let url = URL.createObjectURL(blob);

    let link = document.createElement("a");
    link.href = url;
    link.download = `${frm.doc.name}_Packing_Slip.xls`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}
