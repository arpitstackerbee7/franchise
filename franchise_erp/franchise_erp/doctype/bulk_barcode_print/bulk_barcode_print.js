frappe.ui.form.on('Bulk Barcode Print', {
    refresh: function(frm) {
        // Scan field par focus set karna refresh hone par
        setTimeout(() => {
            frm.fields_dict["table_xmqw"].grid.wrapper
                .find('[data-fieldname="serial_no"]')
                .css('text-align', 'center');
        }, 300);
        frm.get_field('scan_barcode').$input.focus();
    },

    scan_barcode: function(frm) {
        let scanned_value = frm.doc.scan_barcode;
        if (!scanned_value) return;

        scanned_value = scanned_value.trim();

        frappe.call({
            method: "franchise_erp.custom.barcode_utils.get_barcode_data", 
            args: { 
                barcode: scanned_value, 
                is_serialized_mode: frm.doc.is_serialized ? 1 : 0
            },
            callback: function(res) {
                if (res.message) {
                    let data = res.message;
                    let target_table = "table_xmqw"; // Aapke JSON ke according

                    // 🔹 Scenario A: Serialized Item scan kiya
                    if (data.is_serialized == 1) {
                        // Check if this specific Serial No is already in the table
                        let exists = (frm.doc[target_table] || [])
                            .find(d => d.serial_no === data.serial_no);

                        if (exists) {
                            frappe.show_alert({
                                message: `Serial No ${data.serial_no} is already added.`,
                                indicator: 'orange'
                            });
                        } else {
                            let row = frm.add_child(target_table);
                            row.item_code = data.item_code;
                            row.serial_no = data.serial_no;
                            row.design_no = data.design_no;
                            row.qty = 1; // User manually 4-5 kar sakta hai table mein
                            row.is_serialized = 1;
                        }
                    } 
                    
                    // 🔹 Scenario B: Non-Serialized Item scan kiya
                    else {
                        // Agar wahi item code pehle se hai, toh sirf Qty +1 karein
                        let existing_row = (frm.doc[target_table] || [])
                            .find(d => d.item_code === data.item_code && d.serial_no === "-");

                        if (existing_row) {
                            existing_row.qty = (existing_row.qty || 0) + 1;
                        } else {
                            let row = frm.add_child(target_table);
                            row.item_code = data.item_code;
                            row.serial_no = "-";
                            row.design_no = data.design_no;
                            row.qty = 1;
                            row.is_serialized = 0;
                        }
                    }

                    frm.refresh_field(target_table);
                    
                    // Input clear karein aur focus wapas layein
                    frm.set_value("scan_barcode", "");
                    setTimeout(() => {
                        frm.get_field('scan_barcode').$input.focus();
                    }, 100);
                }
            },
            error: function() {
                frm.set_value("scan_barcode", "");
                frm.get_field('scan_barcode').$input.focus();
            }
        });
    }
});