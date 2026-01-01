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
    },
    
    
});


// frappe.ui.form.on("Purchase Receipt", {
//     refresh(frm) {
// if (!this.frm.doc.is_return && this.frm.doc.status !== "Closed") {
//     if (this.frm.doc.docstatus === 0) {
//         this.frm.add_custom_button(
//             __("Purchase Order"),
//             function () {
//                 if (!me.frm.doc.supplier) {
//                     frappe.throw({
//                         title: __("Mandatory"),
//                         message: __("Please Select a Supplier"),
//                     });
//                 }

//                 erpnext.utils.map_current_doc({
//                     method: "franchise_erp.custom.purchase_order.make_purchase_receipt_with_gate_entry",
//                     source_doctype: "Purchase Order",
//                     target: me.frm,

//                     setters: {
//                         supplier: me.frm.doc.supplier,
//                         schedule_date: undefined,
//                     },

//                     get_query_filters: {
//                         docstatus: 1,
//                         status: ["not in", ["Closed", "On Hold"]],
//                         per_received: ["<", 99.99],
//                         company: me.frm.doc.company,
//                         has_submitted_gate_entry: 1   // 👈 custom filter
//                     },

//                     allow_child_item_selection: true,
//                     child_fieldname: "items",
//                     child_columns: ["item_code", "item_name", "qty", "received_qty"],
//                 });
//             },
//             __("Get Items From")
//         );
//     }
// }
//     }
// });
