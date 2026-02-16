// frappe.ui.form.on("Stock Entry", {
//     scan_barcode: function(frm) {
//         setTimeout(() => {
//             let row = frm.doc.items[frm.doc.items.length - 1];
//             if (!row) return;

//             // Agar serial numbers hain
//             if (row.serial_no) {
//                 let serials = row.serial_no
//                     .split("\n")
//                     .map(s => s.trim())
//                     .filter(s => s);

//                 let qty = serials.length;

//                 // Qty ko serial count ke equal rakho
//                 if (row.qty !== qty) {
//                     frappe.model.set_value(
//                         row.doctype,
//                         row.name,
//                         "qty",
//                         qty
//                     );
//                 }
//             }
//         }, 300);
//     }
// });


frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        toggle_fetch_button(frm);
    },
    stock_entry_type(frm) {
        toggle_fetch_button(frm);
    }
});

function toggle_fetch_button(frm) {
    // SAFELY clear button only if it exists
    try {
        frm.remove_custom_button('Get Transits');
    } catch (e) {
        // ignore silently (frappe UI bug)
    }

    if (
        frm.doc.docstatus === 0 &&
        frm.doc.stock_entry_type === "Material Receipt"
    ) {
        frm.add_custom_button(
            'Get Transits',
            () => fetch_and_import_material_issues(frm)
        );
    }
}



function fetch_and_import_material_issues(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Stock Entry',
            filters: {
                stock_entry_type: 'Material Issue',
                docstatus: 1,
                custom_to_company: frm.doc.company,
                custom_status: ["in", ["In Transit", "Partially Delivered"]],
                custom_intercompany_stock_transfer: 1,
            },
            fields: ['name', 'company', 'posting_date', 'stock_entry_type', 'custom_status'],
            limit_page_length: 0
        },
        callback: function(r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(`No Material Issue entries found for current company: ${frm.doc.company}`);
                return;
            }

            const entries = r.message.map(entry => ({
                selected: 0,
                name: entry.name,
                company: entry.company,
                posting_date: entry.posting_date,
                stock_entry_type: entry.stock_entry_type,
                status: entry.custom_status
            }));

            const dialog = new frappe.ui.Dialog({
                title: 'Select Material Issues',
                fields: [
                    {
                        fieldtype: 'Table',
                        fieldname: 'entries',
                        label: 'Material Issues',
                        cannot_add_rows: true,
                        in_place_edit: false,
                        read_only: 1,
                        fields: [
                            { fieldtype: 'Link', label: 'Stock Entry ID', fieldname: 'name', in_list_view: 1, options: 'Stock Entry', width: '200px', read_only:1 },
                            { fieldtype: 'Data', label: 'Stock Entry Type', fieldname: 'stock_entry_type', in_list_view: 1, width: '200px', read_only:1},
                            { fieldtype: 'Data', label: 'From company', fieldname: 'company', in_list_view: 1, width: '200px', read_only: 1 },
                            { fieldtype: 'Data', label: 'Issue Date', fieldname: 'posting_date', in_list_view: 1, width: '200px', read_only: 1 },
                            { fieldtype: 'Data', label: 'Status', fieldname: 'status', in_list_view: 1, width: '200px', read_only:1 },
                        ],
                        data: entries,
                        get_data: () => entries
                    }
                ],
                primary_action_label: 'Import Items',
                primary_action() {
                    const selected_entries = dialog.fields_dict.entries.grid.get_selected_children();
                    if (selected_entries.length === 0) {
                        frappe.msgprint('Please select at least one entry.');
                        return;
                    }

                    const selected_ids = selected_entries.map(entry => entry.name);

                    frappe.call({
                        method: 'franchise_erp.custom.stock_entry.get_items_from_material_issues',
                        args: { stock_entry_names: selected_ids },
                        callback: function(res) {
                            if (res.message && res.message.length > 0) {
                                frm.clear_table('items');

                                res.message.forEach(item => {
                                    const row = frm.add_child('items');
                                    row.item_code = item.item_code;
                                    row.qty = item.qty;
                                    row.uom = item.uom;
                                    row.conversion_factor = item.conversion_factor || 1;
                                    row.transfer_qty = item.qty * row.conversion_factor;
                                    row.stock_uom = item.stock_uom || item.uom;
                                    row.stock_qty = item.qty * row.conversion_factor;
                                    row.batch_no = item.batch_no;
                                    row.serial_no = item.serial_no;           // ✅ map serial_no from Material Issue
                                    row.s_warehouse = item.s_warehouse;       // ✅ source warehouse
                                    row.t_warehouse = frm.doc.to_warehouse;   // ✅ target warehouse
                                    row.basic_rate = item.basic_rate;
                                    row.use_serial_batch_fields = 1;          // ✅ tick automatically
                                    row.custom_material_issue_id = item.custom_material_issue_id;
                                    row.custom_material_issue_item_id = item.custom_material_issue_item_id;
                                });
                                frm.refresh_field('items');
                                frappe.msgprint(`${res.message.length} items imported.`);
                            } else {
                                frappe.msgprint('No items found in selected Material Issues.');
                            }
                        }
                    });

                    dialog.hide();
                }
            });

            dialog.$wrapper.find('.modal-dialog').css({ width: '1000px', maxWidth: '90%' });
            dialog.$wrapper.find('.modal-content').css({ height: '600px', overflow: 'auto' });

            dialog.show();
        }
    });
}


