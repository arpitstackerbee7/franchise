frappe.ui.form.on('Stock Entry', {

    refresh(frm) {
        toggle_fetch_button(frm);
    },

    stock_entry_type(frm) {
        toggle_fetch_button(frm);
    },

    custom_to_company(frm) {
        toggle_intercompany_flag(frm);
    },

    company(frm) {
        toggle_intercompany_flag(frm);
    }

});


// ================================
// SHOW / HIDE GET TRANSITS BUTTON
// ================================
function toggle_fetch_button(frm) {

    frm.remove_custom_button('Get Transits');

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



// =================================
// FETCH MATERIAL ISSUE LIST
// =================================
function fetch_and_import_material_issues(frm) {

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Stock Entry',
            filters: {
                stock_entry_type: 'Material Issue',
                docstatus: 1,
                custom_status: ["in", ["In Transit", "Partially Delivered"]],
                custom_to_company: ["in", [frm.doc.company, null, ""]],
            },
            fields: [
                'name',
                'company',
                'posting_date',
                'stock_entry_type',
                'custom_status'
            ],
            limit_page_length: 0
        },

        callback: function (r) {

            if (!r.message?.length) {
                frappe.msgprint(`No Material Issue entries found for company ${frm.doc.company}`);
                return;
            }

            const entries = r.message.map(row => ({
                name: row.name,
                company: row.company,
                posting_date: row.posting_date,
                stock_entry_type: row.stock_entry_type,
                status: row.custom_status
            }));

            show_material_issue_dialog(frm, entries);
        }
    });
}



// =================================
// DIALOG
// =================================
function show_material_issue_dialog(frm, entries) {

    const dialog = new frappe.ui.Dialog({
        title: 'Select Material Issue',
        size: 'extra-large',

        fields: [{
            fieldtype: 'Table',
            fieldname: 'entries',
            label: 'Material Issues',
            cannot_add_rows: true,
            in_place_edit: true,
            read_only: 1,

            fields: [
                {
                    fieldtype: 'Link',
                    label: 'Stock Entry',
                    fieldname: 'name',
                    options: 'Stock Entry',
                    in_list_view: 1,
                    read_only: 1
                },
                {
                    fieldtype: 'Data',
                    label: 'Type',
                    fieldname: 'stock_entry_type',
                    in_list_view: 1,
                    read_only: 1
                },
                {
                    fieldtype: 'Data',
                    label: 'Company',
                    fieldname: 'company',
                    in_list_view: 1,
                    read_only: 1
                },
                {
                    fieldtype: 'Date',
                    label: 'Issue Date',
                    fieldname: 'posting_date',
                    in_list_view: 1,
                    read_only: 1
                },
                {
                    fieldtype: 'Data',
                    label: 'Status',
                    fieldname: 'status',
                    in_list_view: 1,
                    read_only: 1
                }
            ],

            data: entries,
            get_data: () => entries
        }],

        primary_action_label: 'Import Items',

        primary_action() {

            const grid = dialog.fields_dict.entries.grid;
            const selected = grid.get_selected_children();

            if (selected.length !== 1) {
                frappe.msgprint("Please select exactly ONE Material Issue.");
                return;
            }

            import_items(frm, selected[0].name, dialog);
        }
    });

    dialog.show();

    dialog.$wrapper.find('.modal-dialog').css({
        width: '90%',
        maxWidth: '90%'
    });

    restrict_single_select(dialog);
}



// =================================
// SINGLE SELECT + REMOVE DELETE
// =================================
function restrict_single_select(dialog) {

    const grid = dialog.fields_dict.entries.grid;

    grid.wrapper.find('.grid-remove-rows').hide();
    grid.wrapper.find('.grid-footer').hide();

    grid.wrapper.on('change', 'input[type="checkbox"]', function () {

        if (this.checked) {
            grid.wrapper
                .find('input[type="checkbox"]')
                .not(this)
                .prop('checked', false);
        }

    });
}



// =================================
// IMPORT ITEMS
// =================================
function import_items(frm, stock_entry_id, dialog) {

    frappe.call({
        method: 'franchise_erp.custom.stock_entry.get_items_from_material_issues',
        args: {
            stock_entry_names: [stock_entry_id]
        },

        callback: function (res) {

            if (!res.message?.length) {
                frappe.msgprint('No items found in selected Material Issue.');
                return;
            }

            frm.clear_table('items');

            res.message.forEach(item => {

                const row = frm.add_child('items');

                Object.assign(row, {
                    item_code: item.item_code,
                    qty: item.qty,
                    uom: item.uom,
                    conversion_factor: item.conversion_factor || 1,
                    stock_qty: item.qty * (item.conversion_factor || 1),
                    transfer_qty: item.qty * (item.conversion_factor || 1),
                    serial_no: item.serial_no,
                    batch_no: item.batch_no,
                    s_warehouse: '',
                    t_warehouse: frm.doc.to_warehouse,
                    use_serial_batch_fields: 1,
                    custom_material_issue_id: item.custom_material_issue_id,
                    custom_material_issue_item_id: item.custom_material_issue_item_id
                });

            });

            frm.refresh_field('items');

            frappe.msgprint(`${res.message.length} items imported successfully.`);
            dialog.hide();
        }
    });
}



// =================================
// INTERCOMPANY FLAG
// =================================
function toggle_intercompany_flag(frm) {

    const { company, custom_to_company } = frm.doc;

    frm.set_value(
        'custom_intercompany_stock_transfer',
        company && custom_to_company && company !== custom_to_company ? 1 : 0
    );
}