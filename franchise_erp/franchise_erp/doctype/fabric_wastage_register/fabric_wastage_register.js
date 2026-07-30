frappe.ui.form.on("Fabric Wastage Register", {
    onload(frm) {
        if (frm.is_new()) {
            frm.set_value("posting_date", frappe.datetime.get_today());
            frm.set_value("posting_time", frappe.datetime.now_time());
        }
    },
    subcontracting_receipt(frm) {

        if (!frm.doc.subcontracting_receipt) return;

        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.fabric_wastage_register.fabric_wastage_register.get_subcontracting_receipt_data",
            args: {
                subcontracting_receipt: frm.doc.subcontracting_receipt
            },
            freeze: true,
            callback: function(r) {

                if (!r.message) return;

                frm.set_value("supplier", r.message.supplier);

                frm.clear_table("fabric_wastage_detail");

                (r.message.items || []).forEach(item => {

                    let row = frm.add_child("fabric_wastage_detail");

                    row.item_code = item.item_code;
                    row.size = item.size;
                    row.color = item.color;
                    row.top_fabrics = item.top_fabrics;
                    row.fabric_sent_qty = item.fabric_sent_qty;
                    row.finished_qty_received = item.finished_qty_received;
                    row.standard_consumption = item.standard_consumption;
                    row.actual_consumption = item.actual_consumption;
                    row.uom = item.uom;

                });

                frm.refresh_field("fabric_wastage_detail");
            }
        });

    }
});