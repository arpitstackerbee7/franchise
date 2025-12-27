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
                    frm.clear_table("box_barcodes");

                    if (r.message) {
                        r.message.forEach(row => {
                            let child = frm.add_child("box_barcodes");
                            child.box_barcode = row.box_barcode;
                            child.incoming_logistics_no = row.incoming_logistics_no;
                            child.status = row.status;
                        });
                    }

                    frm.refresh_field("box_barcodes");
                }
            });
        } else {
            frm.clear_table("box_barcodes");
            frm.refresh_field("box_barcodes");
        }
    }
});


// scan box barcode
frappe.ui.form.on("Gate Entry", {
    scan_barcode: function(frm) {
        let barcode = frm.doc.scan_barcode;
        if (!barcode) return;

        let row = frm.doc.box_barcodes.find(
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
                incoming_logistics_no: frm.doc.incoming_logistics,
                box_barcode: barcode
            },
            callback: function() {
                row.status = "Received";
                frm.refresh_field("box_barcodes");

                frappe.show_alert({
                    message: "Box marked as Received",
                    indicator: "green"
                });

                frm.set_value("scan_barcode", "");
            }
        });
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
