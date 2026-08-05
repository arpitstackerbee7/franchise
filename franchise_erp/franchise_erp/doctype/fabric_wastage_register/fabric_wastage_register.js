frappe.ui.form.on("Fabric Wastage Register", {
    onload(frm) {
        if (frm.is_new()) {
            frm.set_value("posting_date", frappe.datetime.get_today());
            frm.set_value("posting_time", frappe.datetime.now_time());
        }
    },
    subcontracting_order(frm) {

        if (!frm.doc.subcontracting_order) return;

        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.fabric_wastage_register.fabric_wastage_register.get_subcontracting_order_data",
            args: {
                subcontracting_order: frm.doc.subcontracting_order
            },
            freeze: true,
            callback: function(r) {

                if (!r.message) return;

                frm.set_value("supplier", r.message.supplier);
                frm.set_value("warehouse", r.message.supplier_warehouse);

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
                    row.rate = item.rate;
                    row.amount = item.amount;

                });

                frm.refresh_field("fabric_wastage_detail");
            }
        });

    }
});