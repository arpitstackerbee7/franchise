frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Gate Entry"),
                () => open_gate_entry_mapper(frm),
                __("Get Items From")
            );
        }
    },
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
        let scanned_value = frm.doc.custom_scan_serial_no;
        if (!scanned_value) return;

        scanned_value = scanned_value.trim();

        // -----------------------------
        // 1️⃣ Check if scanned value is a BARCODE
        // -----------------------------
        frappe.call({
            method: "franchise_erp.custom.purchase_reciept.get_item_by_barcode",
            args: { barcode: scanned_value },
            callback: function(res) {

                // Barcode found
                if (res.message && res.message.item_code) {
                    let item_code = res.message.item_code;

                    // 🔹 Check if same item already exists in doc → increase qty
                    let existing_row = (frm.doc.items || []).find(d => d.item_code === item_code);
                    if (existing_row) {
                        let current_qty = existing_row.qty || 0;
                        frappe.model.set_value(existing_row.doctype, existing_row.name, "qty", current_qty + 1);
                        frm.refresh_field("items");
                        frm.set_value("custom_scan_serial_no", "");
                        return; // STOP further execution
                    }

                    // 🔹 Check for empty row
                    let empty_row = (frm.doc.items || []).find(d => !d.item_code);
                    let row;
                    if (empty_row) {
                        row = empty_row;
                    } else {
                        row = frm.add_child("items");
                    }

                    // Set item_code like manual selection
                    frappe.model.set_value(row.doctype, row.name, "item_code", item_code);
                    // Default qty 1
                    frappe.model.set_value(row.doctype, row.name, "qty", 1);

                    frm.refresh_field("items");
                    frm.set_value("custom_scan_serial_no", "");
                    return; // STOP further execution
                }

                // -----------------------------
                // 2️⃣ SERIAL NUMBER SCAN LOGIC (UNCHANGED)
                // -----------------------------
                for (let row of (frm.doc.items || [])) {
                    if (row.serial_no) {
                        let serials = row.serial_no.split("\n").map(s => s.trim());
                        if (serials.includes(scanned_value)) {
                            frm.set_value("custom_scan_serial_no", "");
                            frappe.throw(
                                `Serial No <b>${scanned_value}</b> already scanned in this GRN`
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
                        scanned_serial: scanned_value,
                        po_items
                    },
                    callback: function(r) {
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

                        serials.push(scanned_value);
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
    }
});

function open_gate_entry_mapper(frm) {
    // 🔒 Mandatory supplier
    if (!frm.doc.supplier) {
        frappe.throw({
            title: __("Mandatory"),
            message: __("Please select Supplier first"),
        });
    }

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Gate Entry",
        target: frm,

        // ❌ REMOVE non-existing setters
        setters: {
            purchase_order: undefined,
        },

        add_filters_group: 1,
        date_field: "posting_date",

        columns: [
            {
                fieldname: "name",
                label: __("Gate Entry"),
                fieldtype: "Link",
                options: "Gate Entry",
            },
            "purchase_order",
            "owner_site",
        ],

        get_query() {
            return {
                filters: {
                    docstatus: 1,
                    consignor: frm.doc.supplier,
                },
            };
        },

        action(selections) {
            if (!selections || !selections.length) {
                frappe.msgprint(__("Please select at least one Gate Entry"));
                return;
            }

            // 🔁 Map Gate Entries one-by-one
            selections.forEach((gate_entry) => {
                map_gate_entry_to_purchase_receipt(frm, gate_entry);
            });

            this.dialog.hide();
        },
    });
}

function map_gate_entry_to_purchase_receipt(frm, gate_entry) {
    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_po_items_from_gate_entry",
        args: {
            gate_entry_name: gate_entry
        },
        freeze: true,
        callback: function (r) {
            if (!r.exc && r.message && r.message.length) {

                // 🧹 Remove default empty row
                if (frm.doc.items?.length === 1 && !frm.doc.items[0].item_code) {
                    frm.clear_table("items");
                }

                // ➕ Append new rows
                r.message.forEach(item => {
                    let row = frm.add_child("items");
                    Object.assign(row, item);
                });

                frm.refresh_field("items");
            }
        }
    });
}
