frappe.ui.form.on("Purchase Receipt", {
    custom_scan_serial_no(frm) {
        let scanned_serial = frm.doc.custom_scan_serial_no;
        if (!scanned_serial) return;

        // ===============================
        // 1️⃣ Duplicate scan prevention  custom_scan_serial_no
        // ===============================
        let already_scanned = false;

        (frm.doc.items || []).forEach(row => {
            if (row.serial_no) {
                let serials = row.serial_no.split("\n").map(s => s.trim());
                if (serials.includes(scanned_serial)) {
                    already_scanned = true;
                }
            }
        });

        // ===============================
        // 2️⃣ Find PO & call server
        // ===============================
        let po_items = (frm.doc.items || []).filter(d => d.purchase_order_item);

        frappe.call({
            method: "franchise_erp.custom.purchase_reciept.validate_po_serial",
            args: {
                scanned_serial: scanned_serial,
                po_items: po_items.map(d => d.purchase_order_item)
            },
            callback: function (r) {
                if (!r.message) return;

                let { purchase_order_item } = r.message;

                // ===============================
                // 3️⃣ Add serial to correct GRN row
                // ===============================
                let row = frm.doc.items.find(
                    d => d.purchase_order_item === purchase_order_item
                );

                if (!row) {
                    frappe.throw("Matching GRN item row not found");
                }

                let serials = row.serial_no
                    ? row.serial_no.split("\n").map(s => s.trim())
                    : [];

                serials.push(scanned_serial);
                row.serial_no = serials.join("\n");

                frm.refresh_field("items");
            },
            always() {
        frm.set_value("custom_scan_serial_no", "");
    }
        });
    }
});