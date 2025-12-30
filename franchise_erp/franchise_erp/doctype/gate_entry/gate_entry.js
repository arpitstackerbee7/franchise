// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Gate Entry", {
// 	refresh(frm) {

// 	},
// });

// get box barcode list

frappe.ui.form.on("Gate Entry", {
    incoming_logistics: function(frm) {
        if (frm.doc.incoming_logistics) {
            frappe.call({
                method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_box_barcodes_for_gate_entry",
                args: {
                    incoming_logistics: frm.doc.incoming_logistics
                },
                callback: function(r) {
                    frm.clear_table("gate_entry_box_barcode");

                    if (r.message) {
                        r.message.forEach(row => {
                            let child = frm.add_child("gate_entry_box_barcode");
                            child.box_barcode = row.box_barcode;
                            child.incoming_logistics_no = row.incoming_logistics_no;
                            child.status = row.status;
                            child.total_barcode_qty = row.total_barcode_qty;
                            child.scan_date_time = row.scan_date_time;
                        });
                    }

                    frm.refresh_field("gate_entry_box_barcode");
                }
            });
        } else {
            frm.clear_table("gate_entry_box_barcode");
            frm.refresh_field("gate_entry_box_barcode");
        }
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


// set current date and disabled futur date
frappe.ui.form.on("Gate Entry", {

    onload(frm) {
        const today = frappe.datetime.get_today();

        // 🔒 Disable future dates in calendar
        frm.set_df_property("document_date", "options", "Today");
        frm.set_df_property("lr_entry_date", "options", "Today");

        // ✅ Auto set today for new doc
        if (frm.is_new()) {
            frm.set_value("document_date", today);
            frm.set_value("lr_entry_date", today);
        }
    },

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


frappe.ui.form.on("Gate Entry", {
    refresh(frm) {
        // Only Submitted Gate Entry
        if (frm.doc.docstatus !== 1) return;

        // Check if Purchase Order is linked
        if (!frm.doc.purchase_order) {
            frappe.msgprint("Purchase Order not linked with this Gate Entry");
            return;
        }

        // Check if Purchase Receipt already exists
        if (frm.doc.received_details && frm.doc.received_details.length > 0) {
            // Don't show button if data already mapped
            return;
        }

        frm.add_custom_button(
            __("Create Purchase Receipt"),
            () => {
                frappe.call({
                    method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.create_purchase_receipt",
                    args: {
                        gate_entry: frm.doc.name
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
});
