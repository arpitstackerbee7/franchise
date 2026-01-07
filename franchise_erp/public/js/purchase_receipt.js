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
function map_gate_entry_to_purchase_receipt(frm, gate_entry, purchase_order) {

    // 🧹 Remove default empty row (only once)
    if (
        frm.doc.items &&
        frm.doc.items.length === 1 &&
        !frm.doc.items[0].item_code
    ) {
        frm.clear_table("items");
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_po_items",
        args: {
            purchase_order: purchase_order
        },
        callback: function (res) {
            (res.message || []).forEach(item => {
                let row = frm.add_child("items");

                row.item_code = item.item_code;
                row.item_name = item.item_name;
                row.stock_uom = item.stock_uom;
                row.uom = item.uom;
                row.conversion_factor = item.conversion_factor;
                row.rate = item.rate;
                row.warehouse = item.warehouse;

                // 🔗 PO links
                row.purchase_order = purchase_order;
                row.purchase_order_item = item.name;

                // ✅ Gate Entry mapping
                row.custom_bulk_gate_entry = gate_entry;
            });

            frm.refresh_field("items");
        }
    });
}

function open_gate_entry_mapper(frm) {
    if (!frm.doc.supplier) {
        frappe.throw({
            title: __("Mandatory"),
            message: __("Please select Supplier first"),
        });
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_gate_entry_with_pos",
        args: { supplier: frm.doc.supplier },
        callback: function (res) {
            const data = res.message || [];

            if (!data.length) {
                frappe.msgprint(__("No Gate Entries found for this supplier"));
                return;
            }

            // 🔹 Group data by Gate Entry
            const grouped = {};
            data.forEach(row => {
                if (!grouped[row.gate_entry]) {
                    grouped[row.gate_entry] = {
                        owner_site: row.owner_site,
                        pos: []
                    };
                }
                grouped[row.gate_entry].pos.push(row.purchase_order);
            });

            // 🔹 Build HTML rows
            let table_rows = '';
            Object.keys(grouped).forEach(ge => {
                grouped[ge].pos.forEach((po, idx) => {
                    table_rows += `
                        <tr data-gate-entry="${ge}">
                            <td>
                                <input type="checkbox" 
                                    class="ge-select" 
                                    data-gate-entry="${ge}" 
                                    data-po="${po}">
                            </td>
                            <td>${idx === 0 ? ge : ''}</td>
                            <td>${po}</td>
                            <td>${grouped[ge].owner_site || ""}</td>
                        </tr>
                    `;
                });
            });

            const d = new frappe.ui.Dialog({
                title: __('Select Purchase Order'),
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'gate_entry_filter',
                        label: 'Gate Entry',
                        options: 'Gate Entry',
                        onchange: function () {
                            const selected_ge = d.get_value('gate_entry_filter');

                            $(d.body).find('tbody tr').each(function () {
                                if (!selected_ge || $(this).data('gate-entry') === selected_ge) {
                                    $(this).show();
                                } else {
                                    $(this).hide();
                                }
                            });
                        }
                    },
                    {
                        fieldtype: 'HTML',
                        fieldname: 'po_table',
                        options: `
                            <div style="max-height: 400px; overflow-y: auto;">
                                <table class="table table-bordered table-condensed">
                                    <thead>
                                        <tr>
                                            <th>Select</th>
                                            <th>Gate Entry ID</th>
                                            <th>Purchase Order ID</th>
                                            <th>Owner Site</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${table_rows}
                                    </tbody>
                                </table>
                            </div>
                        `
                    }
                ],
                primary_action_label: __('Get Items'),
                primary_action: function () {
                    const selected = [];

                    $(d.body).find('.ge-select:checked').each(function () {
                        selected.push({
                            gate_entry: $(this).data('gate-entry'),
                            purchase_order: $(this).data('po')
                        });
                    });

                    if (!selected.length) {
                        frappe.msgprint(__('Please select at least one Purchase Order'));
                        return;
                    }

                    selected.forEach(row => {
                        map_gate_entry_to_purchase_receipt(
                            frm,
                            row.gate_entry,
                            row.purchase_order
                        );
                    });

                    d.hide();
                }
            });

            d.show();
        }
    });
}
