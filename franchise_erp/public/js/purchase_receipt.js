frappe.ui.form.on("Purchase Receipt", {

    onload(frm) {
        if (!frm.is_new()) return;

        (frm.doc.items || []).forEach(row => {
            if (row.purchase_order_item) {
                row.qty = 0;
            }
        });
        (frm.doc.items || []).forEach(row => {
            if (row.purchase_order_item) {
                row.serial_no = "";
            }
        });

        frm.refresh_field("items");
    },

    custom_scan_serial_no(frm) {
        let scanned_serial = frm.doc.custom_scan_serial_no;
        if (!scanned_serial) return;

        scanned_serial = scanned_serial.trim();

        for (let row of (frm.doc.items || [])) {
            if (row.serial_no) {
                let serials = row.serial_no
                    .split("\n")
                    .map(s => s.trim());

                if (serials.includes(scanned_serial)) {
                    frm.set_value("custom_scan_serial_no", "");
                    frappe.throw(
                        `Serial No <b>${scanned_serial}</b> already scanned in this GRN`
                    );
                }
            }
        }

        let po_items = (frm.doc.items || [])
            .filter(d => d.purchase_order_item)
            .map(d => d.purchase_order_item);

        if (!po_items.length) {
            frm.set_value("custom_scan_serial_no", "");
            frappe.throw("No Purchase Order linked in items");
        }

        frappe.call({
            method: "franchise_erp.custom.purchase_reciept.validate_po_serial",
            args: {
                scanned_serial,
                po_items
            },
            callback: function (r) {
                if (!r.message) return;

                let { purchase_order_item } = r.message;

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
                row.qty = (row.qty || 0) + 1;

                frm.refresh_field("items");
            },
            always() {
                frm.set_value("custom_scan_serial_no", "");
            }
        });
    }
});
