frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Gate Entry"),
                () => {
                    open_gate_entry_mapper(frm);
                },
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
function map_gate_entry_to_purchase_receipt(frm, gate_entry) {
    // 🧹 Remove default empty row only once
    if (frm.doc.items?.length === 1 && !frm.doc.items[0].item_code) {
        frm.clear_table("items");
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_po_items_from_gate_entry",
        args: {
            gate_entry: gate_entry
        },
        callback(res) {
            if (!res.message) {
                frappe.msgprint(__("No response received for Gate Entry {0}", [gate_entry]));
                return;
            }

            // Extract items and totals from the response safely
            const items = res.message.items || res.message || [];
            const po_totals = res.message.totals || null;

            if (!items.length) {
                frappe.msgprint(__("No items found for Gate Entry {0}", [gate_entry]));
                return;
            }

            // Add each item to the Purchase Receipt items table
            items.forEach(item => {
                let row = frm.add_child("items");

                row.item_code = item.item_code;
                row.item_name = item.item_name;
                row.stock_uom = item.stock_uom;
                row.uom = item.uom;
                row.conversion_factor = item.conversion_factor;
                row.rate = item.rate;
                row.warehouse = item.warehouse;

                // Link to Purchase Order
                row.purchase_order = item.purchase_order;
                row.purchase_order_item = item.name;

                // Link to Gate Entry
                row.custom_bulk_gate_entry = gate_entry;
            });

            // Update totals if they exist in the response
            if (po_totals) {
                frm.set_value("total_qty", po_totals.total_qty);
                frm.set_value("total", po_totals.total);
                frm.set_value("total_taxes_and_charges", po_totals.total_taxes_and_charges);
                frm.set_value("grand_total", po_totals.grand_total);
                frm.set_value("rounding_adjustment", po_totals.rounding_adjustment);
                frm.set_value("rounded_total", po_totals.rounded_total);
                frm.set_value("disable_rounded_total", po_totals.disable_rounded_total);
                frm.set_value("in_words", po_totals.in_words);
                frm.set_value("advance_paid", po_totals.advance_paid);
                frm.set_value("additional_discount_percentage", po_totals.additional_discount_percentage);
                frm.set_value("discount_amount", po_totals.discount_amount);
            }

            // Refresh the items table to show newly added rows
            frm.refresh_field("items");
        }
    });
}

function open_gate_entry_mapper(frm) {
    if (!frm.doc.supplier) {
        frappe.throw(__("Please select Supplier first"));
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_pending_gate_entries",
        args: {
            supplier: frm.doc.supplier
        },
        callback(r) {
            let data = r.message || [];

            if (!data.length) {
                frappe.msgprint(__("No pending Gate Entries found"));
                return;
            }

            let dialog = new frappe.ui.form.MultiSelectDialog({
                doctype: "Gate Entry",
                target: frm,

                setters: {},

                get_query() {
                    return {
                        filters: {
                            name: ["in", data.map(d => d.gate_entry)],
                            supplier: frm.doc.consignor
                        }
                    };
                },

                columns: [
                    { fieldname: "name", label: __("Gate Entry") },
                    { fieldname: "consignor", label: __("Supplier") }
                ],

                action(selections) {
                    if (!selections.length) {
                        frappe.msgprint(__("Please select at least one Gate Entry"));
                        return;
                    }

                    selections.forEach(ge => {
                        map_gate_entry_to_purchase_receipt(frm, ge);
                    });

                    dialog.dialog.hide();
                }
            });
        }
    });
}




function open_gate_entry_mapper(frm) {
    if (!frm.doc.supplier) {
        frappe.throw(__("Please select Supplier first"));
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_pending_gate_entries",
        args: {
            supplier: frm.doc.supplier
        },
        callback(r) {
            let data = r.message || [];

            if (!data.length) {
                frappe.msgprint(__("No pending Gate Entries found"));
                return;
            }

            let dialog = new frappe.ui.form.MultiSelectDialog({
                doctype: "Gate Entry",
                target: frm,

                // 👇 VERY IMPORTANT
                setters: {
                    consignor: frm.doc.supplier
                },

                get_query() {
                    return {
                        filters: {
                            name: ["in", data.map(d => d.gate_entry)],
                            consignor: frm.doc.supplier
                        }
                    };
                },

                columns: [
                    {
                        fieldname: "name",
                        label: __("Gate Entry"),
                        fieldtype: "Link",
                        options: "Gate Entry"
                    },
                    {
                        fieldname: "consignor",
                        label: __("Supplier"),
                        fieldtype: "Link",
                        options: "Supplier"
                    }
                ],

                action(selections) {
                    if (!selections.length) {
                        frappe.msgprint(__("Please select at least one Gate Entry"));
                        return;
                    }

                    selections.forEach(ge => {
                        map_gate_entry_to_purchase_receipt(frm, ge);
                    });

                    dialog.dialog.hide();
                }
            });
        }
    });
}
