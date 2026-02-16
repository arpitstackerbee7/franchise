frappe.ui.form.on("Stock Entry", {
    scan_barcode: function(frm) {
        setTimeout(() => {
            let row = frm.doc.items[frm.doc.items.length - 1];
            if (!row) return;

            // Agar serial numbers hain
            if (row.serial_no) {
                let serials = row.serial_no
                    .split("\n")
                    .map(s => s.trim())
                    .filter(s => s);

                let qty = serials.length;

                // Qty ko serial count ke equal rakho
                if (row.qty !== qty) {
                    frappe.model.set_value(
                        row.doctype,
                        row.name,
                        "qty",
                        qty
                    );
                }
            }
        }, 300);
    }
});


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


// select multiple entry and delete option use in this code
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
                                    // row.s_warehouse = item.s_warehouse;
                                    row.s_warehouse = '';       // ✅ source warehouse
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

// select one entry and delete option hide in this code
// function fetch_and_import_material_issues(frm) {
//     frappe.call({
//         method: 'frappe.client.get_list',
//         args: {
//             doctype: 'Stock Entry',
//             filters: {
//                 stock_entry_type: 'Material Issue',
//                 docstatus: 1,
//                 custom_to_company: frm.doc.company,
//                 custom_status: ["in", ["In Transit", "Partially Delivered"]],
//                 custom_intercompany_stock_transfer: 1
//             },
//             fields: [
//                 'name',
//                 'company',
//                 'posting_date',
//                 'stock_entry_type',
//                 'custom_status'
//             ],
//             limit_page_length: 0
//         },
//         callback: function (r) {
//             if (!r.message || r.message.length === 0) {
//                 frappe.msgprint(`No Material Issue entries found for company ${frm.doc.company}`);
//                 return;
//             }

//             const entries = r.message.map(row => ({
//                 name: row.name,
//                 company: row.company,
//                 posting_date: row.posting_date,
//                 stock_entry_type: row.stock_entry_type,
//                 status: row.custom_status
//             }));

//             const dialog = new frappe.ui.Dialog({
//                 title: 'Select Material Issues',
//                 fields: [
//                     {
//                         fieldtype: 'Table',
//                         fieldname: 'entries',
//                         label: 'Material Issues',
//                         cannot_add_rows: true,
//                         in_place_edit: false,
//                         read_only: 1,
//                         fields: [
//                             {
//                                 fieldtype: 'Link',
//                                 label: 'Stock Entry ID',
//                                 fieldname: 'name',
//                                 options: 'Stock Entry',
//                                 in_list_view: 1,
//                                 read_only: 1
//                             },
//                             {
//                                 fieldtype: 'Data',
//                                 label: 'Stock Entry Type',
//                                 fieldname: 'stock_entry_type',
//                                 in_list_view: 1,
//                                 read_only: 1
//                             },
//                             {
//                                 fieldtype: 'Data',
//                                 label: 'From Company',
//                                 fieldname: 'company',
//                                 in_list_view: 1,
//                                 read_only: 1
//                             },
//                             {
//                                 fieldtype: 'Data',
//                                 label: 'Issue Date',
//                                 fieldname: 'posting_date',
//                                 in_list_view: 1,
//                                 read_only: 1
//                             },
//                             {
//                                 fieldtype: 'Data',
//                                 label: 'Status',
//                                 fieldname: 'status',
//                                 in_list_view: 1,
//                                 read_only: 1
//                             }
//                         ],
//                         data: entries,
//                         get_data: () => entries
//                     }
//                 ],
//                 primary_action_label: 'Import Items',
//                 primary_action() {
//                     const selected = dialog.fields_dict.entries.grid.get_selected_children();

//                     if (selected.length === 0) {
//                         frappe.msgprint('Please select ONE Material Issue.');
//                         return;
//                     }

//                     if (selected.length > 1) {
//                         frappe.msgprint('Only one Material Issue can be selected.');
//                         return;
//                     }

//                     const selected_id = selected[0].name;

//                     frappe.call({
//                         method: 'franchise_erp.custom.stock_entry.get_items_from_material_issues',
//                         args: {
//                             stock_entry_names: [selected_id]
//                         },
//                         callback: function (res) {
//                             if (!res.message || res.message.length === 0) {
//                                 frappe.msgprint('No items found in selected Material Issue.');
//                                 return;
//                             }

//                             frm.clear_table('items');

//                             res.message.forEach(item => {
//                                 const row = frm.add_child('items');
//                                 row.item_code = item.item_code;
//                                 row.qty = item.qty;
//                                 row.uom = item.uom;
//                                 row.conversion_factor = item.conversion_factor || 1;
//                                 row.stock_qty = item.qty * row.conversion_factor;
//                                 row.transfer_qty = row.stock_qty;
//                                 row.serial_no = item.serial_no;
//                                 row.batch_no = item.batch_no;
//                                 row.s_warehouse = ''; // keep empty
//                                 row.t_warehouse = frm.doc.to_warehouse;
//                                 row.use_serial_batch_fields = 1;
//                                 row.custom_material_issue_id = item.custom_material_issue_id;
//                                 row.custom_material_issue_item_id = item.custom_material_issue_item_id;
//                             });

//                             frm.refresh_field('items');
//                             frappe.msgprint(`${res.message.length} items imported successfully.`);
//                             dialog.hide();
//                         }
//                     });
//                 }
//             });

//             dialog.show();

//             // ===============================
//             // 🔒 SINGLE SELECT + REMOVE DELETE
//             // ===============================
//             const grid = dialog.fields_dict.entries.grid;

//             // remove delete / bulk actions
//             grid.wrapper.find('.grid-remove-rows').hide();
//             grid.wrapper.find('.grid-footer').hide();

//             // allow only one checkbox selection
//             grid.wrapper.on('change', 'input[type="checkbox"]', function () {
//                 const $this = $(this);

//                 if ($this.prop('checked')) {
//                     // uncheck all others
//                     grid.wrapper.find('input[type="checkbox"]').not(this).prop('checked', false);

//                     // reset all row checked flags
//                     grid.grid_rows.forEach(r => {
//                         r.doc.__checked = false;
//                     });

//                     // set current row checked
//                     const row_idx = $this.closest('.grid-row').data('idx');
//                     const row = grid.grid_rows[row_idx - 1];
//                     if (row) {
//                         row.doc.__checked = true;
//                     }
//                 }
//             });
//         }
//     });
// }



frappe.ui.form.on('Stock Entry', {
    custom_to_company(frm) {
        toggle_intercompany_flag(frm);
    },

    company(frm) {
        toggle_intercompany_flag(frm);
    }
});

function toggle_intercompany_flag(frm) {
    const company = frm.doc.company;
    const to_company = frm.doc.custom_to_company;

    // jab dono filled ho
    if (company && to_company) {
        if (company !== to_company) {
            // ✅ different company → intercompany ON
            frm.set_value('custom_intercompany_stock_transfer', 1);
        } else {
            //  same company → intercompany OFF
            frm.set_value('custom_intercompany_stock_transfer', 0);
        }
    } else {
        // safety: agar to_company blank ho
        frm.set_value('custom_intercompany_stock_transfer', 0);
    }
}
