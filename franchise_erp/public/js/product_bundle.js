frappe.ui.form.on('Product Bundle', {
    custom_scan_serial_no(frm) {
        if (frm.doc.custom_scan_serial_no) {

            // 🔒 DUPLICATE VALIDATION (ADDED)
            let is_duplicate = frm.doc.items.some(row => 
                row.custom_serial_no === frm.doc.custom_scan_serial_no
            );

            if (is_duplicate) {
                frappe.msgprint(__('This serial number is already added.'));
                frm.set_value('custom_scan_serial_no', '');
                return;
            }
            // 🔒 END DUPLICATE VALIDATION

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    'doctype': 'Serial No',
                    'filters': { 'name': frm.doc.custom_scan_serial_no },
                    'fieldname': ['name', 'item_code', 'description', 'status']
                },
                callback: function (r) {
                    if (!r.exc) {
                        console.log(r.message);
                        var item_details = r.message;
    
                        // Check if the serial number status is 'Delivered'
                        if (item_details.status === 'Delivered') {
                            frappe.msgprint(__('This serial number has already been delivered'));
                            frm.set_value('custom_scan_serial_no', '');
                            return; // Prevent adding it to the item table
                        }
    
                        // Continue with adding the serial number to the item table
                        var row;
                        if (frm.doc.items.length > 0 && !frm.doc.items[0].item_code) {
                            // If first row is empty, use it
                            row = frm.doc.items[0];
                        } else {
                            // Otherwise, add a new row
                            row = frm.fields_dict.items.grid.add_new_row();
                        }
    
                        frappe.model.set_value(row.doctype, row.name, "item_code", item_details.item_code);
                        frappe.model.set_value(row.doctype, row.name, "description", item_details.description);
                        frappe.model.set_value(row.doctype, row.name, "custom_serial_no", item_details.name);    
                        frm.refresh_field('items');
                    }
                }
            });

            frm.set_value('custom_scan_serial_no', '');
        }
    }
});
