frappe.ui.form.on("Stock Reconciliation", {
    scan_barcode: function(frm) {
        setTimeout(() => {
            let row = frm.doc.items[frm.doc.items.length - 1];
            if (!row) return;

            // Agar serial numbers hain
            if (row.serial_no) {
                let serials = row.serial_no
                    .split("\n")
                    .map(s => s.trim())
                    .filter(s => s);

                let qty = serials.length;

                // Qty ko serial count ke equal rakho
                if (row.qty !== qty) {
                    frappe.model.set_value(
                        row.doctype,
                        row.name,
                        "qty",
                        qty
                    );
                }
            }
        }, 300);
    }
});
