frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        frm.set_df_property("title", "read_only", 1);
        // set_sales_person(frm);
        frm.__export_button_added = false;
        add_export_button(frm);
    },
    validate(frm) {
        frm.doc.items.forEach(row => {
            if ((row.rate || 0) <= 0) {
                frappe.throw(
                    `Row #${row.idx}: MRP cannot be 0 for Item ${row.item_code}`
                );
            }
        });
        handle_sis_calculation_on_dn(frm);
    }
});

frappe.ui.form.on('Delivery Note', {
    company: function(frm) {
        if (!frm.doc.company) return;

        frappe.db.get_value(
            'SIS Configuration',
            { company: frm.doc.company },
            'delivery_note_warehouse'
        ).then(r => {
            if (r && r.message && r.message.delivery_note_warehouse) {
                frm.set_value(
                    'set_warehouse',
                    r.message.delivery_note_warehouse
                );
            }
        });
        // if (frm.doc.docstatus === 0) {
        //     set_sales_person(frm);
        // }
    },

    onload: function(frm) {
        if (frm.doc.company && !frm.doc.set_warehouse) {
            frm.trigger('company');
        }
        // if (frm.is_new()) {
        //     set_sales_person(frm);
        // }
    }
});


frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        // SIS Counter Role Check
        if (frappe.user.has_role('SIS Counter')) {
            apply_sis_counter_minimal_ui(frm);
        }
    },

   

    // Handle re-rendering when customer is selected
    customer: function(frm) {
        if (frappe.user.has_role('SIS Counter')) {
            setTimeout(() => { apply_sis_counter_minimal_ui(frm); }, 500);
        }
    }
});

function apply_sis_counter_minimal_ui(frm) {
    // 1. Sections to Hide (Internal names from Customize Form JSON)
    const sections_to_hide = [
        'currency_and_price_list',
        'section_break_49',
        'taxes_section',
        'accounting_dimensions_section',
        'gst_section',
        'section_break_41',
        'customer_po_details',
        'sales_team_section_break',
        'printing_details'
    ];

    // 2. Individual Fields to Hide
    const fields_to_hide = [
        'naming_series',
        'posting_time',
        'set_posting_time', 'company', 'amended_from',
        'is_return',
        'tax_id',
        'total_taxes_and_charges',
        'base_total_taxes_and_charges'
    ];

    // Apply Hiding for sections
    sections_to_hide.forEach(sec => {
        frm.set_df_property(sec, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${sec}"]`).attr('style', 'display: none !important');
    });

    // Apply Hiding for fields
    fields_to_hide.forEach(field => {
        frm.set_df_property(field, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${field}"]`).hide();
    });

    // 3. Clean Items Table - FIX: Changed get_all_fields to docfields
    let grid = frm.get_field("items").grid;
    let show_list = ['item_code', 'qty', 'rate', 'discount_amount', 'amount',"custom_style"];

    if (grid && grid.docfields) {
        grid.docfields.forEach(df => {
            grid.set_column_disp(df.fieldname, show_list.includes(df.fieldname));
        });
        grid.refresh();
    }

    // Set simplified page title
    frm.page.set_title("SIS Counter Sale");
}


frappe.ui.form.on("Delivery Note Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code) {
            frappe.db.get_value("Item", row.item_code, [
                "custom_barcode_code",
                "custom_colour_name",
                "custom_size"
            ]).then(r => {

                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "custom_style", r.message.custom_barcode_code);
                    frappe.model.set_value(cdt, cdn, "custom_color", r.message.custom_colour_name);
                    frappe.model.set_value(cdt, cdn, "custom_size", r.message.custom_size);
                }

            });
        }
    }
});

// async function set_sales_person(frm) {
//     if (!frm.doc.company) return;

//     // ✅ STOP if submitted
//     if (frm.doc.docstatus !== 0) return;

//     try {
//         let user = frappe.session.user;

//         let res = await frappe.db.get_list("Sales Person", {
//             filters: {
//                 custom_user: user,
//                 custom_company: frm.doc.company
//             },
//             fields: ["name"],
//             limit: 1
//         });

//         if (res && res.length > 0) {
//             frm.set_value("custom_sales_person", res[0].name);
//         } else {
//             frm.set_value("custom_sales_person", "");
//         }

//     } catch (err) {
//         console.error(err);
//     }
// }

frappe.ui.form.on("Delivery Note", {

    onload_post_render(frm) {

        // sirf return DN ke liye
        if (frm.doc.is_return && frm.doc.custom_bulk_sales_return) {

            // 🔥 wait for ERPNext auto calculations
            setTimeout(() => {

                // remove dirty state
                frm.dirty = false;
                frm.doc.__unsaved = 0;

                // optional (safe)
                frm.refresh();

            },200); // thoda delay zaroori hai
        }
    }
});

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


function handle_sis_calculation_on_dn(frm) {

    if (!frm.doc.customer) return;

    // Check TZU Setting first
    frappe.db.get_single_value("TZU Setting", "is_margin_calculate_on_dn")
        .then(enabled => {

            if (!enabled) return;

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

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_output_gst_",
                            r.message.gst_percent
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_output_gst_value",
                            r.message.output_gst_value
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_net_sale_value",
                            r.message.net_sale_value
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_margins_",
                            r.message.margin_percent
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_margin_amount",
                            r.message.margin_amount
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_total_invoice_amount",
                            r.message.taxable_value
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "rate",
                            r.message.taxable_value
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "amount",
                            flt(current_qty * r.message.taxable_value)
                        );

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "custom_last_sis_qty",
                            current_qty
                        );

                        frm.refresh_field("items");
                    }
                });
            });

        });
}