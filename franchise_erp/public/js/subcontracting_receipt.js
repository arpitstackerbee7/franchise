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

frappe.ui.form.on("Subcontracting Receipt", {

    custom_scan_barcode(frm) {
        let scanned_value = frm.doc.custom_scan_barcode;
        if (!scanned_value) return;
        scanned_value = scanned_value.trim();

        // -------------------------------
        // 1️⃣ BARCODE SCAN → Get Item Code
        // -------------------------------
        frappe.call({
            method: "franchise_erp.custom.purchase_reciept.get_item_by_barcode",
            args: { barcode: scanned_value },
            callback: function(res) {
                if (res.message && res.message.item_code) {
                    let item_code = res.message.item_code;

                    // Check if item already exists → increase qty
                    let existing_row = (frm.doc.items || []).find(d => d.item_code === item_code);

                    if (existing_row) {
                        let current_qty = existing_row.qty || 0;
                        frappe.model.set_value(existing_row.doctype, existing_row.name, "qty", current_qty + 1);
                        frm.refresh_field("items");
                        update_total_qty(frm);
                        frm.set_value("custom_scan_barcode", "");
                        return;
                    }

                    // Use empty row or add new
                    let empty_row = (frm.doc.items || []).find(d => !d.item_code);
                    let row = empty_row || frm.add_child("items");

                    frappe.model.set_value(row.doctype, row.name, "item_code", item_code);
                    frappe.model.set_value(row.doctype, row.name, "qty", 1);

                    frm.refresh_field("items");
                    update_total_qty(frm);
                    frm.set_value("custom_scan_barcode", "");
                    return;
                }

                // -------------------------------
                // 2️⃣ DUPLICATE SERIAL CHECK (CURRENT GRN)
                // -------------------------------
                for (let row of (frm.doc.items || [])) {
                    if (row.serial_no) {
                        let serials = row.serial_no.split("\n").map(s => s.trim());
                        if (serials.includes(scanned_value)) {
                            frm.set_value("custom_scan_barcode", "");
                            frappe.throw(`Serial No <b>${scanned_value}</b> already scanned in this GRN`);
                        }
                    }
                }

                // -------------------------------
                // 3️⃣ SERIAL VALIDATION FROM PO
                // -------------------------------
                let po_items = (frm.doc.items || [])
                    .filter(d => d.purchase_order_item)
                    .map(d => d.purchase_order_item);

                if (!po_items.length) {
                    frm.set_value("custom_scan_barcode", "");
                    frappe.throw("No Purchase Order linked in items");
                }

                frappe.call({
                    method: "franchise_erp.custom.purchase_reciept.validate_po_serial",
                    args: {
                        scanned_serial: scanned_value,
                        po_items
                    },
                    callback: function(r) {
                        if (!r.message) return;

                        let { purchase_order_item } = r.message;
                        let row = frm.doc.items.find(d => d.purchase_order_item === purchase_order_item);

                        if (!row) frappe.throw("Matching GRN item row not found");

                        let serials = row.serial_no ? row.serial_no.split("\n").map(s => s.trim()) : [];
                        serials.push(scanned_value);

                        row.serial_no = serials.join("\n");
                        row.qty = (row.qty || 0) + 1;

                        frm.refresh_field("items");
                        update_total_qty(frm);
                    },
                    always() {
                        frm.set_value("custom_scan_barcode", "");
                    }
                });
            }
        });
    },

    
});


// frappe.ui.form.on("Subcontracting Receipt", {
//     validate(frm) {
//         // Zero-qty rows
//         let zero_qty_rows = (frm.doc.items || []).filter(row =>
//             (row.accepted_qty || 0) === 0 && (row.rejected_qty || 0) === 0
//         );

//         if (zero_qty_rows.length) {
//             frappe.validated = false; // stop save

//             frappe.confirm(
//                 `
//                 <b>Following items have Accepted Qty = 0 AND Rejected Qty = 0:</b><br><br>
//                 ${zero_qty_rows.map(d => d.item_code).join("<br>")}
//                 <br><br>
//                 Do you want to remove them and continue saving manually?
//                 `,
//                 function() {
//                     // ✅ Remove only zero-qty rows
//                     zero_qty_rows.forEach(row => {
//                         let grid_row = frm.get_field("items").grid.grid_rows_by_docname[row.name];
//                         if (grid_row) grid_row.remove();
//                     });

//                     frm.refresh_field("items");

//                     frappe.msgprint("Zero-qty items removed. Please click Save again.");
//                 },
//                 function() {
//                     frappe.validated = false; // No → stay
//                 }
//             );
//         }

//         // Make Accepted Qty read-only
//         frm.fields_dict.items.grid.update_docfield_property("accepted_qty", "read_only", 1);
//     }
// });