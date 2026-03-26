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


// frappe.ui.form.on("Subcontracting Receipt", {

//     custom_scan_barcode: function(frm) {

//         if (!frm.doc.custom_scan_barcode) return;

//         let serial_no = frm.doc.custom_scan_barcode;

//         // Serial No fetch karo
//         frappe.db.get_doc("Serial No", serial_no).then(serial => {

//             if (!serial) {
//                 frappe.msgprint("Invalid Serial No");
//                 return;
//             }

//             // Check karo item already table me hai ya nahi
//             let existing_row = frm.doc.items.find(row => 
//                 row.item_code === serial.item_code
//             );

//             if (existing_row) {

//                 // ✅ Qty increase karo
//                 existing_row.qty = flt(existing_row.qty) + 1;
//                 existing_row.received_qty = flt(existing_row.received_qty) + 1;

//                 // Serial No append karo
//                 if (existing_row.serial_no) {
//                     existing_row.serial_no += "\n" + serial_no;
//                 } else {
//                     existing_row.serial_no = serial_no;
//                 }

//                 frm.refresh_field("items");

//             } else {

//                 // ✅ New row add karo
//                 let child = frm.add_child("items");

//                 child.item_code = serial.item_code;
//                 child.qty = 1;
//                 child.received_qty = 1;
//                 child.serial_no = serial_no;
//                 child.warehouse = serial.warehouse;

//                 frm.refresh_field("items");
//             }

//             // Scan field clear karo
//             frm.set_value("custom_scan_barcode", "");
//         });
//     }
// });


// frappe.ui.form.on("Subcontracting Receipt", {
    
//     custom_scan_barcode(frm) {
//         let scanned_value = frm.doc.custom_scan_barcode;
//         if (!scanned_value) return;

//         scanned_value = scanned_value.trim();

//         // ===================================
//         // 1️⃣ BARCODE SCAN CHECK
//         // ===================================
//         frappe.call({
//             method: "franchise_erp.custom.purchase_reciept.get_item_by_barcode",
//             args: { barcode: scanned_value },
//             callback: function(res) {

//                 if (res.message && res.message.item_code) {
//                     let item_code = res.message.item_code;

//                     // 🔹 If item already exists → increase qty
//                     let existing_row = (frm.doc.items || []).find(
//                         d => d.item_code === item_code
//                     );

//                     if (existing_row) {
//                         let current_qty = existing_row.qty || 0;

//                         frappe.model.set_value(
//                             existing_row.doctype,
//                             existing_row.name,
//                             "qty",
//                             current_qty + 1
//                         );

//                         frm.refresh_field("items");
//                         update_total_qty(frm);
//                         frm.set_value("custom_scan_barcode", "");
//                         return;
//                     }

//                     // 🔹 Use empty row or create new
//                     let empty_row = (frm.doc.items || []).find(d => !d.item_code);
//                     let row = empty_row || frm.add_child("items");

//                     frappe.model.set_value(row.doctype, row.name, "item_code", item_code);
//                     frappe.model.set_value(row.doctype, row.name, "qty", 1);

//                     frm.refresh_field("items");
//                     update_total_qty(frm);
//                     frm.set_value("custom_scan_barcode", "");
//                     return;
//                 }

//                 // ===================================
//                 // 2️⃣ DUPLICATE SERIAL CHECK (CURRENT GRN)
//                 // ===================================
//                 for (let row of (frm.doc.items || [])) {
//                     if (row.serial_no) {
//                         let serials = row.serial_no
//                             .split("\n")
//                             .map(s => s.trim());

//                         if (serials.includes(scanned_value)) {
//                             frm.set_value("custom_scan_barcode", "");
//                             frappe.throw(
//                                 `Serial No <b>${scanned_value}</b> already scanned in this GRN`
//                             );
//                         }
//                     }
//                 }

//                 // ===================================
//                 // 3️⃣ SERIAL VALIDATION FROM PO
//                 // ===================================
//                 let po_items = (frm.doc.items || [])
//                     .filter(d => d.purchase_order_item)
//                     .map(d => d.purchase_order_item);

//                 if (!po_items.length) {
//                     frm.set_value("custom_scan_barcode", "");
//                     frappe.throw("No Purchase Order linked in items");
//                 }

//                 frappe.call({
//                     method: "franchise_erp.custom.purchase_reciept.validate_po_serial",
//                     args: {
//                         scanned_serial: scanned_value,
//                         po_items
//                     },
//                     callback: function(r) {
//                         if (!r.message) return;

//                         let { purchase_order_item } = r.message;

//                         let row = frm.doc.items.find(
//                             d => d.purchase_order_item === purchase_order_item
//                         );

//                         if (!row) {
//                             frappe.throw("Matching GRN item row not found");
//                         }

//                         let serials = row.serial_no
//                             ? row.serial_no.split("\n").map(s => s.trim())
//                             : [];

//                         serials.push(scanned_value);

//                         row.serial_no = serials.join("\n");
//                         row.qty = (row.qty || 0) + 1;

//                         frm.refresh_field("items");
//                         update_total_qty(frm);
//                     },
//                     always() {
//                         frm.set_value("custom_scan_barcode", "");
//                     }
//                 });
//             }
//         });
//     }
// });

// frappe.ui.form.on("Subcontracting Receipt", {

//     custom_scan_barcode(frm) {

//         let scanned_value = frm.doc.custom_scan_barcode;

//         if (!scanned_value) return;

//         scanned_value = scanned_value.replace(/\n/g, "").trim();


//         // -------------------------------
//         // GET ITEM BY BARCODE
//         // -------------------------------

//         frappe.call({
//             method: "franchise_erp.custom.subcontracting_receipt.get_item_by_barcode",
//             args: { barcode: scanned_value },

//             callback: function(res) {

//                 if (res.message && res.message.item_code) {

//                     let item_code = res.message.item_code;

//                     let existing_row = (frm.doc.items || []).find(
//                         d => d.item_code === item_code
//                     );


//                     // -------------------------------
//                     // EXISTING ROW
//                     // -------------------------------

//                     if (existing_row) {

//                         check_po_qty_and_update(frm, existing_row);

//                         return;
//                     }


//                     // -------------------------------
//                     // NEW ROW
//                     // -------------------------------

//                     let empty_row = (frm.doc.items || []).find(d => !d.item_code);

//                     let row = empty_row || frm.add_child("items");

//                     frappe.model.set_value(
//                         row.doctype,
//                         row.name,
//                         "item_code",
//                         item_code
//                     );

//                     // start from 0 so validation works
//                     row.qty = 0;

//                     check_po_qty_and_update(frm, row);

//                     return;
//                 }


//                 // -------------------------------
//                 // DUPLICATE SERIAL CHECK
//                 // -------------------------------

//                 for (let row of (frm.doc.items || [])) {

//                     if (row.serial_no) {

//                         let serials = row.serial_no.split("\n").map(s => s.trim());

//                         if (serials.includes(scanned_value)) {

//                             clear_barcode_field(frm);

//                             frappe.throw(
//                                 `Serial No <b>${scanned_value}</b> already scanned in this GRN`
//                             );
//                         }
//                     }
//                 }


//                 // -------------------------------
//                 // SERIAL VALIDATION
//                 // -------------------------------

//                 let po_items = (frm.doc.items || [])
//                     .filter(d => d.purchase_order_item)
//                     .map(d => d.purchase_order_item);


//                 if (!po_items.length) {

//                     clear_barcode_field(frm);

//                     frappe.throw("No Purchase Order linked in items");
//                 }


//                 frappe.call({

//                     method: "franchise_erp.custom.subcontracting_receipt.validate_po_serial",

//                     args: {
//                         scanned_serial: scanned_value,
//                         po_items
//                     },

//                     callback: function(r) {

//                         if (!r.message) return;

//                         let { purchase_order_item } = r.message;

//                         let row = frm.doc.items.find(
//                             d => d.purchase_order_item === purchase_order_item
//                         );

//                         if (!row)
//                             frappe.throw("Matching GRN item row not found");


//                         check_po_qty_and_update(frm, row);


//                         let serials = row.serial_no
//                             ? row.serial_no.split("\n").map(s => s.trim())
//                             : [];

//                         serials.push(scanned_value);

//                         row.serial_no = serials.join("\n");

//                         frm.refresh_field("items");

//                         update_total_qty(frm);
//                     },

//                     always() {

//                         clear_barcode_field(frm);

//                     }

//                 });

//             }

//         });

//     }

// });

// function check_po_qty_and_update(frm, row) {

//     if (!row.purchase_order_item) {
//         clear_barcode_field(frm);

//         frappe.throw(
//             `Purchase Order Item missing for <b>${row.item_code}</b>`
//         );
//     }

//     frappe.call({

//         method: "franchise_erp.custom.subcontracting_receipt.get_po_item_qty",

//         args: {
//             po_item: row.purchase_order_item
//         },

//         callback: function(r) {

//             let po_qty = r.message || 0;

//             let current_qty = row.qty || 0;

//             if (current_qty + 1 > po_qty) {

//                 clear_barcode_field(frm);

//                 frappe.throw(
//                     `You cannot scan more than PO Qty (${po_qty}) for Item <b>${row.item_code}</b>`
//                 );
//             }

//             frappe.model.set_value(
//                 row.doctype,
//                 row.name,
//                 "qty",
//                 current_qty + 1
//             );

//             frm.refresh_field("items");

//             update_total_qty(frm);

//             clear_barcode_field(frm);
//         }

//     });
// }


// function clear_barcode_field(frm) {

//     frm.doc.custom_scan_barcode = "";

//     frm.refresh_field("custom_scan_barcode");

//     setTimeout(() => {

//         if (frm.fields_dict.custom_scan_barcode) {

//             frm.fields_dict.custom_scan_barcode.$input.focus();

//         }

//     }, 100);

// }

// function update_total_qty(frm) {

//     let total = 0;

//     (frm.doc.items || []).forEach(row => {

//         total += row.qty || 0;

//     });

//     frm.set_value("total_qty", total);

// }

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