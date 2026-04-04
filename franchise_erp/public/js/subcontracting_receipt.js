frappe.ui.form.on("Subcontracting Receipt", {
    refresh(frm) {

        // sirf submitted document ke liye
        if (frm.doc.docstatus !== 1 || !frm.doc.supplier) return;

        // Supplier master se custom_gate_out_applicable check
        frappe.db.get_value(
            "Supplier",
            frm.doc.supplier,
            "custom_gate_out_applicable",
            (r) => {
                if (r && r.custom_gate_out_applicable) {
                    // ✅ sirf tab button dikhega
                    frm.add_custom_button(
                        __("Incoming Logistics"),
                        () => {
                            frappe.call({
                                method: "franchise_erp.custom.subcontracting_receipt.create_incoming_logistics_from_scr",
                                args: {
                                    subcontracting_receipt: frm.doc.name
                                },
                                callback: function (res) {
                                    if (res.message) {
                                        const doc = frappe.model.sync(res.message)[0];
                                        frappe.set_route("Form", doc.doctype, doc.name);
                                    }
                                }
                            });
                        },
                        __("Create")
                    );
                }
            }
        );
    }
});

frappe.ui.form.on("Subcontracting Receipt", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    },
     onload(frm) {

        if (frm.is_new()) {

            frappe.after_ajax(() => {

                if (frm.doc.items) {

                    frm.doc.items.forEach(function(row) {
                        row.received_qty = 0;
                        row.qty = 0;
                    });

                    frm.refresh_field("items");
                }

            });

        }
    },
});




let scan_in_progress = false;

frappe.ui.form.on("Subcontracting Receipt", {

    custom_scan_barcode: async function(frm) {

        if (scan_in_progress) return;

        let scanned_value = frm.doc.custom_scan_barcode;

        if (!scanned_value) return;

        scanned_value = scanned_value.replace(/\n/g, "").trim();

        if (!scanned_value) return;

        scan_in_progress = true;

        try {

            // -------------------------
            // DUPLICATE SERIAL CHECK
            // -------------------------
            for (let row of (frm.doc.items || [])) {

                if (row.serial_no) {

                    let serials = row.serial_no.split("\n").map(s => s.trim());

                    if (serials.includes(scanned_value)) {
                        frappe.throw(`Serial No <b>${scanned_value}</b> already scanned`);
                    }
                }
            }

            // -------------------------
            // CHECK ITEM BARCODE
            // -------------------------

            let item_res = await frappe.call({
                method: "franchise_erp.custom.subcontracting_receipt.get_item_by_barcode",
                args: { barcode: scanned_value }
            });

            if (item_res.message && item_res.message.item_code) {

                let item_code = item_res.message.item_code;

                let row = (frm.doc.items || []).find(d => d.item_code === item_code);

                if (!row) {

                    row = frm.add_child("items");

                    await frappe.model.set_value(row.doctype, row.name, "item_code", item_code);

                    await frappe.model.set_value(row.doctype, row.name, "qty", 0);
                }

                await increase_qty(frm, row);

                frm.refresh_field("items");

                clear_barcode_field(frm);

                scan_in_progress = false;

                return;
            }


            // -------------------------
            // SERIAL VALIDATION
            // -------------------------

            let po_items = (frm.doc.items || [])
                .filter(d => d.purchase_order_item)
                .map(d => d.purchase_order_item);

            if (!po_items.length) {
                frappe.throw("No Purchase Order linked in items");
            }

            let serial_res = await frappe.call({
                method: "franchise_erp.custom.subcontracting_receipt.validate_po_serial",
                args: {
                    scanned_serial: scanned_value,
                    po_items
                }
            });

            if (!serial_res.message) {
                frappe.throw("Invalid Serial No");
            }

            let { purchase_order_item } = serial_res.message;

            let row = frm.doc.items.find(
                d => d.purchase_order_item === purchase_order_item
            );

            if (!row) {
                frappe.throw("Matching GRN item row not found");
            }

            // -------------------------
            // ADD SERIAL
            // -------------------------

            let serials = row.serial_no
                ? row.serial_no.split("\n").map(s => s.trim())
                : [];

            serials.push(scanned_value);

            await frappe.model.set_value(
                row.doctype,
                row.name,
                "serial_no",
                serials.join("\n")
            );

            // -------------------------
            // UPDATE QTY BASED ON SERIAL COUNT
            // -------------------------

            await frappe.model.set_value(
                row.doctype,
                row.name,
                "qty",
                serials.length
            );

            frm.refresh_field("items");

            update_total_qty(frm);

        }

        catch (e) {

            frappe.msgprint(e.message);

        }

        finally {

            clear_barcode_field(frm);

            scan_in_progress = false;

        }

    }

});


async function increase_qty(frm, row) {

    let res = await frappe.call({
        method: "franchise_erp.custom.subcontracting_receipt.get_po_item_qty",
        args: {
            po_item: row.purchase_order_item
        }
    });

    let po_qty = res.message || 0;

    let current_qty = row.qty || 0;

    if (current_qty + 1 > po_qty) {

        frappe.throw(
            `You cannot scan more than PO Qty (${po_qty}) for Item <b>${row.item_code}</b>`
        );
    }

    await frappe.model.set_value(
        row.doctype,
        row.name,
        "qty",
        current_qty + 1
    );

}

function clear_barcode_field(frm) {

    frm.set_value("custom_scan_barcode", "");

    setTimeout(() => {

        if (frm.fields_dict.custom_scan_barcode) {
            frm.fields_dict.custom_scan_barcode.$input.focus();
        }

    }, 100);

}

function update_total_qty(frm) {

    let total = 0;

    (frm.doc.items || []).forEach(row => {
        total += row.qty || 0;
    });

    frm.set_value("total_qty", total);

}

// frappe.ui.form.on("Subcontracting Receipt", {
//     setup(frm) {
//         frm.set_query("custom_gate_entry", () => {
//             return {
//                 filters: {
//                     consignor: frm.doc.supplier,
//                     type: "Job Receipt"
//                 }
//             };
//         });
//     }
// });
frappe.ui.form.on('Subcontracting Receipt', {
    onload: function(frm) {
        frm.fields_dict.items.grid.get_field('custom_gate_entry').get_query = function() {
            return {
                query: "franchise_erp.custom.subcontracting_receipt.get_available_gate_entries"
            };
        };
    }
});