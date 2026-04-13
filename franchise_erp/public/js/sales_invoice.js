(function () {

    const original_show_alert = frappe.show_alert;

    frappe.show_alert = function (opts) {

        let msg = typeof opts === "string" ? opts : opts?.message || "";

        // 🚫 BLOCK ONLY SCAN RELATED ALERTS
        if (
            msg.includes("Qty increased") ||
            msg.includes("Row #") ||
            msg.includes("desk-alert")
        ) {
            return; // ❌ STOP UI + STOP QUEUE
        }

        return original_show_alert.apply(this, arguments);
    };

})();
frappe.ui.form.on("Sales Invoice", {
    onload(frm) {
        frm.__disable_scan_alerts = true;
    }
});
/*************************************************
 * SALES INVOICE – ULTRA OPTIMIZED CLIENT SCRIPT
 *************************************************/

/* =====================================================
   🔥 GLOBAL CACHE + BATCH SYSTEM
===================================================== */

let ITEM_CACHE = {};
let ITEM_FETCH_QUEUE = new Set();
let FETCH_TIMER = null;
let QTY_TIMER = null;

/* =====================================================
   MAIN FORM EVENTS
===================================================== */

frappe.ui.form.on("Sales Invoice", {

    refresh(frm) {
        frm.set_df_property("title", "read_only", 1);

        handle_inter_company_grn(frm);
        toggle_incoming_logistic_button(frm);
        toggle_outgoing_logistics_button(frm);

        frm.__export_button_added = false;
        add_export_button(frm);
        check_delivery_note(frm);
        // Default warehouse (only once)
        if (!frm.is_new() || !frm.doc.company || frm.doc.set_warehouse) return;

        frappe.db.get_value("SIS Configuration",
            { company: frm.doc.company },
            "warehouse"
        ).then(r => {
            if (r.message?.warehouse) {
                frm.set_value("set_warehouse", r.message.warehouse);
            }
        });

        make_total_qty_bold(frm);
    },
    on_submit(frm) {
        // ✅ ensure button appears immediately after submit
        toggle_outgoing_logistics_button(frm);
    },
    items_add(frm) {
        check_delivery_note(frm);
    },
    onload(frm) {
        make_total_qty_bold(frm);

        if (!frm.doc.is_return) return;

        frm.set_query("custom_gate_entry", function () {
            return {
                query: "franchise_erp.custom.sales_invoice.get_available_gate_entries_sales"
            };
        });
    },

    customer(frm) {
        // frm.set_value("payment_terms_template", "");
        // setTimeout(() => set_custom_due_date(frm), 300);
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

    // is_return(frm) {
    //     if (frm.doc.is_return) make_items_negative(frm);
    // },

    validate(frm) {
        handle_sis_calculation(frm);
        check_delivery_note(frm);
        // check_duplicate_serials(frm);
    },

    scan_barcode(frm) {
        if (!frm.doc.scan_barcode) return;

        frm.__barcode_scanning = true;

        setTimeout(() => {
            frm.__barcode_scanning = false;
        }, 400);
    }
});

/* =====================================================
   ITEM EVENTS (🔥 OPTIMIZED)
===================================================== */

frappe.ui.form.on("Sales Invoice Item", {

    item_code(frm, cdt, cdn) {

        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        // 🔥 Add to queue instead of API call
        ITEM_FETCH_QUEUE.add(row.item_code);

        clearTimeout(FETCH_TIMER);

        FETCH_TIMER = setTimeout(() => {
            fetch_items_bulk(frm);
        }, 250);
        apply_discount_hide(frm, cdt, cdn);
    },

    // qty(frm, cdt, cdn) {

    //     if (!frm.doc.is_return) return;

    //     let row = locals[cdt][cdn];
    //     if (row.qty > 0) {
    //         frappe.model.set_value(cdt, cdn, "qty", -Math.abs(row.qty));
    //     }
    // },
    delivery_note(frm, cdt, cdn) {
        check_delivery_note(frm);
    },

    dn_detail(frm, cdt, cdn) {
        check_delivery_note(frm);
    }
});

/* =====================================================
   🔥 BULK FETCH (MAIN FIX)
===================================================== */

function fetch_items_bulk(frm) {

    if (!ITEM_FETCH_QUEUE.size) return;

    let items = Array.from(ITEM_FETCH_QUEUE);
    ITEM_FETCH_QUEUE.clear();

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Item",
            filters: { name: ["in", items] },
            fields: [
                "name",
                "custom_barcode_code",
                "custom_colour_name",
                "custom_size",
                "custom_departments"
            ],
            limit_page_length: items.length
        },
        callback(r) {

            (r.message || []).forEach(d => {
                ITEM_CACHE[d.name] = d;
            });

            apply_item_data(frm);
        }
    });
}

/* =====================================================
   APPLY ITEM DATA (NO MULTIPLE CALLS)
===================================================== */

function apply_item_data(frm) {

    (frm.doc.items || []).forEach(row => {

        if (!row.item_code) return;

        let d = ITEM_CACHE[row.item_code];
        if (!d) return;

        frappe.model.set_value(row.doctype, row.name, "custom_style", d.custom_barcode_code);
        frappe.model.set_value(row.doctype, row.name, "custom_color", d.custom_colour_name);
        frappe.model.set_value(row.doctype, row.name, "custom_size", d.custom_size);
        frappe.model.set_value(row.doctype, row.name, "custom_department", d.custom_departments);
    });

    smart_refresh(frm);
}

/* =====================================================
   SMART REFRESH (NO LAG)
===================================================== */

function smart_refresh(frm) {

    if (frm.__refreshing) return;

    frm.__refreshing = true;

    setTimeout(() => {
        frm.refresh_field("items");
        frm.__refreshing = false;
    }, 150);
}

/* =====================================================
   SIS CALCULATION (ASYNC FIX)
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
            callback(r) {

                if (!r.message) return;

                let taxable = flt(r.message.taxable_value);
                row.amount = flt(row.amount || 0) + (taxable * delta);

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

            let days = cint(r.message?.custom_credit_days || 0);
            if (!days) return;

            frm.set_value(
                "due_date",
                frappe.datetime.add_days(frm.doc.posting_date, days)
            );
        });
}

/* =====================================================
   RETURN NEGATIVE
===================================================== */

// function make_items_negative(frm) {

//     (frm.doc.items || []).forEach(row => {

//         if (row.serial_no) {
//             let count = row.serial_no.split("\n").filter(s => s.trim()).length;
//             frappe.model.set_value(row.doctype, row.name, "qty", -Math.abs(count));
//         } else if (row.qty > 0) {
//             frappe.model.set_value(row.doctype, row.name, "qty", -Math.abs(row.qty));
//         }
//     });
// }

/* =====================================================
   BUTTONS (UNCHANGED – SAFE)
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
                    consignor: frm.doc.customer
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

/* =====================================================
   TOTAL QTY UI (DEBOUNCED)
===================================================== */

function make_total_qty_bold(frm) {

    clearTimeout(QTY_TIMER);

    QTY_TIMER = setTimeout(() => {

        if (frm.fields_dict.total_qty?.$wrapper) {
            frm.fields_dict.total_qty.$wrapper
                .find(".control-value")
                .css({
                    "font-weight": "bold",
                    "font-size": "18px",
                    "color": "rgb(99 175 244)"
                });
        }

    }, 250);
}


function add_export_button(frm) {

    if (frm.__export_button_added) return;
    frm.__export_button_added = true;

    frm.add_custom_button("Export Packing Excel", async () => {

        if (!frm.doc.items?.length) {
            frappe.msgprint("No items found to export.");
            return;
        }

        let item_codes = [
            ...new Set(frm.doc.items.map(i => i.item_code).filter(Boolean))
        ];

        try {
            frappe.dom.freeze("Preparing Excel...");

            let items = await get_items_in_chunks(item_codes);

            let item_map = {};
            (items || []).forEach(d => item_map[d.name] = d);

            generate_fixed_excel(frm, item_map);

        } catch (e) {
            console.error(e);
            frappe.msgprint("Excel generation failed");
        } finally {
            frappe.dom.unfreeze();
        }

    }, "Actions");
}
async function get_items_in_chunks(item_codes) {

    let all_items = [];
    let chunk_size = 100; // 🔥 increased (faster)

    for (let i = 0; i < item_codes.length; i += chunk_size) {

        let chunk = item_codes.slice(i, i + chunk_size);

        let res = await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item",
                filters: { name: ["in", chunk] },
                fields: [
                    "name",
                    "custom_group_collection",
                    "custom_top_fabrics",
                    "custom_colour_name",
                    "custom_size",
                    "custom_barcode_code"
                ],
                limit_page_length: chunk.length
            }
        });

        all_items.push(...(res.message || []));
    }

    return all_items;
}
function generate_fixed_excel(frm, item_map) {

    let totalQty = 0;
    let totalAmt = 0;

    let rows = [];

    for (let item of (frm.doc.items || [])) {

        let m = item_map[item.item_code] || {};

        let qty = flt(item.qty);
        let amt = flt(item.amount);

        totalQty += qty;
        totalAmt += amt;

        rows.push(`
            <tr>
                <td>${frm.doc.name || ''}</td>
                <td>${frm.doc.posting_date || ''}</td>
                <td>${item.serial_no?.split('\n')[0] || ''}</td>
                <td>${item.gst_hsn_code || ''}</td>
                <td>${m.custom_barcode_code || ''}</td>
                <td>${m.custom_group_collection || ''}</td>
                <td>${m.custom_top_fabrics || ''}</td>
                <td>${m.custom_colour_name || ''}</td>
                <td>${m.custom_size || ''}</td>
                <td align="center">${qty}</td>
                <td align="right">${flt(item.price_list_rate)}</td>
                <td align="right">${amt.toFixed(2)}</td>
            </tr>
        `);
    }

    let html = `
        <table border="1">
            <tr>
                <th colspan="12" style="background:yellow;">
                    ${(frm.doc.customer_name || '').toUpperCase()} - PACKING SLIP
                </th>
            </tr>

            <tr>
                <th>Invoice</th><th>Date</th><th>Serial</th><th>HSN</th>
                <th>Style</th><th>Dept</th><th>Fabric</th>
                <th>Color</th><th>Size</th><th>Qty</th>
                <th>MRP</th><th>Amount</th>
            </tr>

            ${rows.join("")}

            <tr>
                <td colspan="9" align="right"><b>Total</b></td>
                <td>${totalQty}</td>
                <td></td>
                <td>${totalAmt.toFixed(2)}</td>
            </tr>
        </table>
    `;

    let blob = new Blob([html], { type: 'application/vnd.ms-excel' });

    let link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${frm.doc.name}_Packing.xls`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
// function add_outgoing_logistics_button(frm) {

//     // if (frm.__outgoing_btn_added) return;
//     if (frm.custom_buttons && frm.custom_buttons["Outgoing Logistics"]) return;
//     frm.__outgoing_btn_added = true;

//     frappe.db.get_value("Customer", frm.doc.customer,
//         "custom_outgoing_logistics_applicable"
//     ).then(r => {

//         if (!r.message?.custom_outgoing_logistics_applicable) return;

//         frm.add_custom_button("Outgoing Logistics", async () => {

//             let address_name =
//                 frm.doc.shipping_address_name ||
//                 frm.doc.customer_address;

//             if (!address_name) {
//                 frappe.msgprint("Address missing");
//                 return;
//             }

//             let addr = await frappe.db.get_value("Address",
//                 address_name,
//                 ["city", "custom_citytown"]
//             );

//             let city = addr.message?.custom_citytown || addr.message?.city || "";

//             frappe.new_doc("Outgoing Logistics", {}, doc => {

//                 doc.consignee = frm.doc.customer;
//                 doc.owner_site = frm.doc.company;
//                 doc.transporter = frm.doc.transporter;
//                 doc.stock_point = frm.doc.set_warehouse;
//                 doc.type = "Sales Invoice";
//                 doc.station_to = city;

//                 let row = frappe.model.add_child(doc, "references");
//                 row.source_doctype = "Sales Invoice";
//                 row.source_name = frm.doc.name;
//             });

//         }, "Create");

//     });
// }
async function add_outgoing_logistics_button(frm) {

    if (frm.doc.docstatus !== 1 || !frm.doc.customer) return;

    // prevent duplicate button
    if (frm.custom_buttons && frm.custom_buttons["Outgoing Logistics"]) return;

    let r = await frappe.db.get_value(
        "Customer",
        frm.doc.customer,
        "custom_outgoing_logistics_applicable"
    );

    if (!r.message?.custom_outgoing_logistics_applicable) return;

    frm.add_custom_button("Outgoing Logistics", async () => {

        let address_name =
            frm.doc.shipping_address_name ||
            frm.doc.customer_address;

        if (!address_name) {
            frappe.msgprint("Address missing");
            return;
        }

        let addr = await frappe.db.get_value(
            "Address",
            address_name,
            ["city", "custom_citytown"]
        );

        let city = addr.message?.custom_citytown || addr.message?.city || "";

        frappe.new_doc("Outgoing Logistics", {}, doc => {

            doc.consignee = frm.doc.customer;
            doc.owner_site = frm.doc.company;
            doc.transporter = frm.doc.transporter;
            doc.stock_point = frm.doc.set_warehouse;
            doc.type = "Sales Invoice";
            doc.station_to = city;

            let row = frappe.model.add_child(doc, "references");
            row.source_doctype = "Sales Invoice";
            row.source_name = frm.doc.name;
        });

    }, "Create");
}
let DISCOUNT_CACHE = {};

function apply_discount_hide(frm, cdt, cdn) {

    let row = locals[cdt][cdn];
    if (!row?.item_code) return;

    if (DISCOUNT_CACHE[row.item_code] !== undefined) {
        toggle_discount(frm, DISCOUNT_CACHE[row.item_code]);
        return;
    }

    frappe.db.get_value("Item", row.item_code, "custom_discount_not_allowed")
        .then(r => {

            let hide = r.message?.custom_discount_not_allowed == 1;

            DISCOUNT_CACHE[row.item_code] = hide;

            toggle_discount(frm, hide);
        });
}

function toggle_discount(frm, hide) {

    let fields = [
        "margin_type",
        "margin_rate_or_amount",
        "discount_percentage",
        "discount_amount",
        "distributed_discount_amount"
    ];

    fields.forEach(f => {
        frm.fields_dict.items.grid.update_docfield_property(f, "hidden", hide);
    });

    frm.refresh_field("items");
}
// function check_duplicate_serials(frm) {

//     let seen = new Set();

//     for (let row of (frm.doc.items || [])) {

//         if (!row.serial_no) continue;

//         let serials = row.serial_no.split("\n");

//         for (let s of serials) {

//             s = s.trim();
//             if (!s) continue;

//             if (seen.has(s)) {
//                 frappe.msgprint({
//                     title: "Duplicate Serial",
//                     message: `Duplicate Serial: ${s}`,
//                     indicator: "red"
//                 });
//                 return;
//             }

//             seen.add(s);
//         }
//     }
// }

function check_delivery_note(frm) {

    let has_dn = false;

    (frm.doc.items || []).forEach(row => {
        if (row.delivery_note || row.dn_detail) {
            has_dn = true;
        }
    });

    // 👉 Agar kisi bhi item me DN hai → Update Stock = 0
    if (has_dn) {
        if (frm.doc.update_stock) {
            frm.set_value('update_stock', 0);
        }
    }
}