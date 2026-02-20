// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Gate Entry", {
// 	refresh(frm) {

// 	},
// });


// get box barcode list

// frappe.ui.form.on("Gate Entry", {
//     incoming_logistics(frm) {
//         if (!frm.doc.incoming_logistics) {
//             frm.clear_table("purchase_orders");
//             frm.clear_table("gate_entry_box_barcode");
//             frm.refresh_fields();
//             return;
//         }

//         frappe.call({
//             method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_data_for_gate_entry",
//             args: {
//                 incoming_logistics: frm.doc.incoming_logistics
//             },
//             callback(r) {
//                 if (!r.message) return;

//                 const data = r.message;

//                 // -------- Header Fields --------
//                 frm.set_value("lr_quantity", data.lr_quantity);
//                 frm.set_value("document_no", data.document_no);
//                 frm.set_value("declaration_amount", data.declaration_amount);
//                 frm.set_value("quantity_as_per_invoice", data.qty_as_per_invoice);

//                 // -------- Purchase Orders --------
//                 frm.clear_table("purchase_ids");
//                 (data.purchase_orders || []).forEach(row => {
//                     let child = frm.add_child("purchase_ids");
//                     Object.assign(child, row);
//                 });

//                 // -------- Box Barcodes --------
//                 frm.clear_table("gate_entry_box_barcode");
//                 (data.box_barcodes || []).forEach(row => {
//                     let child = frm.add_child("gate_entry_box_barcode");
//                     Object.assign(child, row);
//                 });

//                 frm.refresh_fields();
//             }
//         });
//     }
// });
// frappe.ui.form.on("Gate Entry", {
//     onload(frm) {
//         if (!frappe.route_options) return;

//         // only set incoming_logistics
//         if (frappe.route_options.incoming_logistics) {
//             frm.set_value(
//                 "incoming_logistics",
//                 frappe.route_options.incoming_logistics
//             );
//         }

//         frappe.route_options = null;
//     },

//     incoming_logistics(frm) {
//         if (!frm.doc.incoming_logistics) {
//             frm.clear_table("references");
//             frm.clear_table("gate_entry_box_barcode");
//             frm.refresh_fields();
//             return;
//         }

//         frappe.call({
//             method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_data_for_gate_entry",
//             args: {
//                 incoming_logistics: frm.doc.incoming_logistics
//             },
//             callback(r) {
//                 if (!r.message) return;

//                 const data = r.message;

//                 // Header
//                 frm.set_value("type", data.type);
//                 frm.set_value("consignor", data.party);
//                 frm.set_value("consignor_customer", data.party);
//                 frm.set_value("lr_quantity", data.lr_quantity);
//                 frm.set_value("document_no", data.document_no);
//                 frm.set_value("declaration_amount", data.declaration_amount);
//                 frm.set_value("quantity_as_per_invoice", data.qty_as_per_invoice);

//                 // Purchase IDs
//                 frm.clear_table("references");
//                 (data.source_name || []).forEach(row => {
//                     let child = frm.add_child("references");
//                     child.source_name = row.source_name;
//                     child.source_doctype = row.source_doctype;
//                 });

//                 // Box Barcodes
//                 frm.clear_table("gate_entry_box_barcode");
//                 (data.box_barcodes || []).forEach(row => {
//                     let child = frm.add_child("gate_entry_box_barcode");
//                     Object.assign(child, row);
//                 });

//                 frm.refresh_fields();
//             }
//         });
//     }
// });
frappe.ui.form.on("Gate Entry", {
    onload(frm) {
        if (!frappe.route_options) return;

        if (frappe.route_options.incoming_logistics) {
            frm.set_value(
                "incoming_logistics",
                frappe.route_options.incoming_logistics
            );
        }

        frappe.route_options = null;
    },

    incoming_logistics(frm) {
        if (!frm.doc.incoming_logistics) {
            frm.clear_table("references");
            frm.clear_table("gate_entry_box_barcode");

            frm.set_value("consignor", null);
            frm.set_value("consignor_customer", null);

            frm.refresh_fields();
            return;
        }

        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_data_for_gate_entry",
            args: {
                incoming_logistics: frm.doc.incoming_logistics
            },
            callback(r) {
                if (!r.message) return;

                const data = r.message;

                // -------------------------------
                // Header fields
                // -------------------------------
                frm.set_value("type", data.type);
                frm.set_value("lr_quantity", data.lr_quantity);
                frm.set_value("document_no", data.document_no);
                frm.set_value("declaration_amount", data.declaration_amount);
                frm.set_value("quantity_as_per_invoice", data.qty_as_per_invoice);

                // -------------------------------
                // ✅ PARTY LOGIC (IMPORTANT FIX)
                // -------------------------------
                frm.set_value("consignor", data.party);

                // -------------------------------
                // References (Purchase / Job etc)
                // -------------------------------
               frm.clear_table("references");

(data.purchase_orders || []).forEach(row => {
    let child = frm.add_child("references");
    child.source_doctype = row.reference_doctype;
    child.source_name = row.reference_name;
});

frm.refresh_field("references");

                // -------------------------------
                // Box Barcodes
                // -------------------------------
                frm.clear_table("gate_entry_box_barcode");
                (data.box_barcodes || []).forEach(row => {
                    let child = frm.add_child("gate_entry_box_barcode");
                    Object.assign(child, row);
                });

                frm.refresh_fields();
            }
        });
    }
});


// scan box barcode
frappe.ui.form.on("Gate Entry", {

    scan_barcode(frm) {
        let barcode = frm.doc.scan_barcode;
        if (!barcode) return;

        let row = frm.doc.gate_entry_box_barcode.find(
            r => r.box_barcode === barcode
        );

        if (!row) {
            frappe.msgprint({
                title: "Invalid Barcode",
                message: "Barcode not found in this Gate Entry",
                indicator: "red"
            });
            frm.set_value("scan_barcode", "");
            return;
        }

        if (row.status === "Received") {
            frappe.msgprint({
                title: "Already Scanned",
                message: "This box is already Received",
                indicator: "orange"
            });
            frm.set_value("scan_barcode", "");
            return;
        }

        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.mark_box_barcode_received",
            args: {
                box_barcode: barcode,
                incoming_logistics_no: frm.doc.incoming_logistics
            },
            callback: function(r) {

                // update child row locally
                row.status = "Received";
                row.scan_date_time = frappe.datetime.now_datetime();

                frm.refresh_field("gate_entry_box_barcode");

                frappe.show_alert({
                    message: __("Box marked as Received"),
                    indicator: "green"
                });

                frm.set_value("scan_barcode", "");
            }
        });
    },
    

    //BLOCK SUBMIT IF ANY BOX IS PENDING
    before_submit(frm) {
        let pending = frm.doc.gate_entry_box_barcode.filter(
            r => r.status !== "Received"
        );

        if (pending.length > 0) {
            frappe.throw(
                `You cannot submit Gate Entry.<br>
                 Pending Boxes: <b>${pending.length}</b>`
            );
        }
    }
});


// // set current date and disabled futur date
frappe.ui.form.on("Gate Entry", {

    document_date(frm) {
        validate_not_future(frm, "document_date");
    },

    lr_entry_date(frm) {
        validate_not_future(frm, "lr_entry_date");
    }

});

// Manual typing validation
function validate_not_future(frm, fieldname) {
    if (!frm.doc[fieldname]) return;

    const today = frappe.datetime.get_today();

    if (frm.doc[fieldname] > today) {
        frappe.msgprint({
            title: __("Invalid Date"),
            message: __("Future dates are not allowed."),
            indicator: "red"
        });
        frm.set_value(fieldname, today);
    }
}

// frappe.ui.form.on("Gate Entry", {
//     refresh(frm) {
//         // Only Submitted Gate Entry
//         if (frm.doc.docstatus !== 1) return;

//         // Child table mandatory
//         if (!frm.doc.purchase_ids || !frm.doc.purchase_ids.length) return;

//         let show_button = false;
//         let promises = [];

//         // 🔥 loop child table POs
//         (frm.doc.purchase_ids || []).forEach(row => {
//             if (!row.purchase_order) return;

//             promises.push(
//                 frappe.db.get_doc("Purchase Order", row.purchase_order).then(po => {
//                     (po.items || []).forEach(item => {
//                         let ordered_qty = flt(item.qty);
//                         let received_qty = flt(item.received_qty);

//                         if (ordered_qty !== received_qty) {
//                             show_button = true;
//                         }
//                     });
//                 })
//             );
//         });

//         Promise.all(promises).then(() => {
//             if (!show_button) return;

//             frm.add_custom_button(
//                 __("Create Purchase Receipt"),
//                 () => {
//                     frappe.call({
//                         method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.create_purchase_receipt",
//                         args: {
//                             gate_entry: frm.doc.name
//                         },
//                         callback(r) {
//                             if (!r.message) return;

//                             let doc = frappe.model.sync(r.message)[0];
//                             frappe.set_route("Form", doc.doctype, doc.name);
//                         }
//                     });
//                 },
//                 __("Create")
//             );
//         });
//     }
// });

frappe.ui.form.on("Gate Entry", {
    onload(frm) {
        set_transport_service_item(frm);
    },

    refresh(frm) {
        set_transport_service_item(frm);
    }
});

function set_transport_service_item(frm) {
    // Don't override if already set
    if (frm.doc.transport_service_item) {
        return;
    }

    frappe.db.get_single_value(
        "TZU Setting",
        "transport_service_item"
    ).then(value => {
        if (value) {
            frm.set_value("transport_service_item", value);
        }
    });
}

frappe.ui.form.on("Gate Entry", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(
                __("Purchase Invoice"),
                () => {
                    frappe.call({
                        method: "franchise_erp.custom.purchase_invoice.create_pi_from_gate_entry",
                        args: {
                            gate_entry: frm.doc.name
                        },
                        callback(r) {
                            if (r.message) {
                                frappe.msgprint({
                                    title: __("Success"),
                                    message: __("Purchase Invoice created successfully"),
                                    indicator: "green"
                                });

                                frappe.set_route(
                                    "Form",
                                    "Purchase Invoice",
                                    r.message
                                );
                            }
                        }
                    });
                },
                __("Create")
            );
        }
    }
});