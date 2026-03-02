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
    }
});


frappe.ui.form.on("Subcontracting Receipt", {

    custom_scan_barcode: function(frm) {

        if (!frm.doc.custom_scan_barcode) return;

        let serial_no = frm.doc.custom_scan_barcode;

        // Serial No fetch karo
        frappe.db.get_doc("Serial No", serial_no).then(serial => {

            if (!serial) {
                frappe.msgprint("Invalid Serial No");
                return;
            }

            // Check karo item already table me hai ya nahi
            let existing_row = frm.doc.items.find(row => 
                row.item_code === serial.item_code
            );

            if (existing_row) {

                // ✅ Qty increase karo
                existing_row.qty = flt(existing_row.qty) + 1;
                existing_row.received_qty = flt(existing_row.received_qty) + 1;

                // Serial No append karo
                if (existing_row.serial_no) {
                    existing_row.serial_no += "\n" + serial_no;
                } else {
                    existing_row.serial_no = serial_no;
                }

                frm.refresh_field("items");

            } else {

                // ✅ New row add karo
                let child = frm.add_child("items");

                child.item_code = serial.item_code;
                child.qty = 1;
                child.received_qty = 1;
                child.serial_no = serial_no;
                child.warehouse = serial.warehouse;

                frm.refresh_field("items");
            }

            // Scan field clear karo
            frm.set_value("custom_scan_barcode", "");
        });
    }
});