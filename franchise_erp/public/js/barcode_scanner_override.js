frappe.provide("erpnext.utils");

(function () {
    const original_prepare = erpnext.utils.BarcodeScanner.prototype.prepare_item_for_scan;

    erpnext.utils.BarcodeScanner.prototype.prepare_item_for_scan = function (
        row,
        item_code,
        barcode,
        batch_no,
        serial_no
    ) {
        // ❌ popup show nahi karenge

        let item_data = { item_code: item_code };
        item_data[this.qty_field] = 1; // default scanned qty
        item_data["has_item_scanned"] = 1;

        frappe.model.set_value(row.doctype, row.name, item_data);

        frappe.run_serially([
            () => this.set_batch_no(row, batch_no),
            () => this.set_barcode(row, barcode),
            () => this.set_serial_no(row, serial_no),
            () => this.clean_up(),
        ]);
    };
})();