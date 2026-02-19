frappe.ui.form.on('Bulk Barcode Printing', {
    setup: function(frm) {
        // Center the text in the Serial No column in the Grid
        frappe.dom.set_style(`
            [data-fieldname="items"] [data-fieldname="serial_no"] {
                text-align: center !important;
            }
        `);
    },
    
    scan_barcode: function(frm) {
        let scanned_value = frm.doc.scan_barcode;
        if (!scanned_value) return;
        scanned_value = scanned_value.trim();

        if (!frm.doc.item_type) {
            frappe.msgprint(__("Please select Item Type first"));
            frm.set_value('scan_barcode', '');
            return;
        }

        frappe.call({
            method: "franchise_erp.custom.barcode_utils.get_barcode_data",
            args: { barcode: scanned_value, item_type: frm.doc.item_type },
            callback: function(res) {
                if (res.message) {
                    let data = res.message;

                    if (data.is_serialized === 1) {
                        // Serial Number Logic
                        let exists = (frm.doc.items || []).find(d => d.serial_no === scanned_value);
                        if (exists) {
                            frm.set_value("scan_barcode", "");
                            frappe.throw(`Serial No <b>${scanned_value}</b> already exists.`);
                        }

                        let row = frm.add_child("items");
                        row.item_code = data.item_code;
                        row.serial_no = data.serial_no; 
                        row.design_no = data.design_no;
                        row.qty = 1;
                        row.is_serialized = 1;
                    } else {
                        // Non-Serial Logic (Merge rows)
                        let existing_row = (frm.doc.items || []).find(d => d.item_code === data.item_code && d.serial_no === "-");
                        if (existing_row) {
                            frappe.model.set_value(existing_row.doctype, existing_row.name, "qty", (existing_row.qty || 0) + 1);
                        } else {
                            let row = frm.add_child("items");
                            row.item_code = data.item_code;
                            row.serial_no = "-"; 
                            row.design_no = data.design_no;
                            row.qty = 1;
                            row.is_serialized = 0;
                        }
                    }
                    frm.refresh_field("items");
                    frm.set_value("scan_barcode", "");
                    apply_strict_locks(frm);
                    setTimeout(() => { frm.get_field('scan_barcode').$input.focus(); }, 200);
                }
            }
        });
    },

    refresh: function(frm) {
        apply_strict_locks(frm);
    }
});

// Child Table Events
frappe.ui.form.on('Bulk Barcode Item', {
    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Strictly lock the Qty field in the popup if it is serialized
        frm.fields_dict.items.grid.get_field('qty').read_only = (row.is_serialized === 1);
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Anti-bypass: Force Qty to 1 if user tries to change it for Serialized items
        if (row.is_serialized === 1 && row.qty !== 1) {
            frappe.model.set_value(cdt, cdn, "qty", 1);
            frappe.show_alert({message: __("Quantity for Serialized items is fixed at 1"), indicator: 'orange'});
        }
    }
});

function apply_strict_locks(frm) {
    if (frm.doc.items) {
        frm.doc.items.forEach(row => {
            let grid_row = frm.fields_dict.items.grid.get_row(row.name);
            if (row.is_serialized === 1) {
                // Completely disable the Qty field in the grid
                grid_row.get_field('qty').read_only = 1;
            } else {
                grid_row.get_field('qty').read_only = 0;
            }
        });
    }
}