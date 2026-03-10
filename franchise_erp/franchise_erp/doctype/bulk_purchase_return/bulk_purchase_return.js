frappe.ui.form.on("Bulk Purchase Return", {
    refresh(frm) {

        if (frm.is_new()) return;

        frm.add_custom_button("Get Items from GRN", () => {
            open_return_items_dialog(frm);
        });

    }
});


function open_return_items_dialog(frm) {

    let dialog = new frappe.ui.Dialog({
        title: "Return Items from GRN",
        size: "extra-large",

        fields: [
            {
                fieldname: "supplier",
                label: "Supplier",
                fieldtype: "Link",
                options: "Supplier",
                default: frm.doc.supplier,
                reqd: 1,
                onchange() {
                    load_returnable_items(frm, dialog);
                }
            },

            {
                fieldname: "item_code",
                label: "Item",
                fieldtype: "Link",
                options: "Item",
                onchange() {
                    load_returnable_items(frm, dialog);
                }
            },

            {
                fieldname: "items_table",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                in_place_edit: true,

                fields: [

                    { fieldname: "purchase_receipt", label: "GRN", fieldtype: "Data", read_only: 1, in_list_view: 1 },

                    { fieldname: "item_code", label: "Item", fieldtype: "Data", read_only: 1, in_list_view: 1 },

                    { fieldname: "returnable_qty", label: "Returnable Qty", fieldtype: "Float", read_only: 1, in_list_view: 1 },

                    { fieldname: "returned_qty", label: "Already Returned", fieldtype: "Float", read_only: 1, in_list_view: 1 },

                    {
                        fieldname: "return_qty",
                        label: "Return Qty",
                        fieldtype: "Float",
                        in_list_view: 1,
                        onchange() {

                            let rows = dialog.fields_dict.items_table.grid.get_data();

                            rows.forEach(d => {

                                if (d.return_qty > d.returnable_qty) {

                                    frappe.msgprint(
                                        `Return Qty cannot exceed Returnable Qty for Item ${d.item_code}`
                                    );

                                    d.return_qty = d.returnable_qty;

                                    dialog.fields_dict.items_table.grid.refresh();
                                }

                            });

                        }
                    }

                ]
            }
        ],

        primary_action_label: "Add Selected Items",

        primary_action() {

            let selected_rows =
                dialog.fields_dict.items_table.grid.get_selected_children();
        
            if (!selected_rows.length) {
                frappe.msgprint("Please select rows");
                return;
            }
        
            // 🔴 Validate return qty in dialog
            for (let r of selected_rows) {
        
                if (!r.return_qty || r.return_qty <= 0) {
                    frappe.throw(
                        `Please enter Return Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }
        
                if (r.return_qty > r.returnable_qty) {
                    frappe.throw(
                        `Return Qty cannot exceed Returnable Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }
            }
        
            frappe.call({
                method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_pr_item_details",
                args: {
                    items: selected_rows
                },
                callback: function(r) {
        
                    if (r.message) {
        
                        r.message.forEach(d => {
        
                            // Duplicate validation
                            let duplicate = frm.doc.items.find(row =>
                                row.purchase_receipt_item === d.name
                            );
        
                            if (duplicate) {
                                frappe.throw(
                                    `Item ${d.item_code} from GRN ${d.purchase_receipt} is already added.`
                                );
                            }
        
                            let row = frm.add_child("items");
        
                            row.purchase_receipt = d.purchase_receipt;
                            row.purchase_receipt_item = d.name;
        
                            row.item_code = d.item_code;
                            row.item_name = d.item_name;
        
                            row.qty = d.qty;
        
                            row.uom = d.uom;
                            row.stock_uom = d.stock_uom;
                            row.conversion_factor = d.conversion_factor;
        
                            row.rate = d.rate;
                            row.amount = flt(d.rate) * flt(d.qty);
        
                            row.warehouse = d.warehouse;
                            row.returnable_quantity = d.returnable_quantity;
                            
                            frappe.model.set_value(
                                row.doctype,
                                row.name,
                                "available_serial_nos",
                                d.available_serial_nos
                            );
        
                        });
        
                        frm.refresh_field("items");
        
                        dialog.hide();
                    }
        
                }
            });
        }

    });

    dialog.show();

    load_returnable_items(frm, dialog);
}


function load_returnable_items(frm, dialog) {

    let supplier = dialog.get_value("supplier");
    let item_code = dialog.get_value("item_code");

    if (!supplier) return;

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_returnable_items",
        args: {
            supplier: supplier,
            item_code: item_code,
            company: frm.doc.company
        },
        callback: function(r) {

            if (!r.message) return;

            dialog.fields_dict.items_table.df.data = r.message;
            dialog.fields_dict.items_table.grid.refresh();

        }
    });
}


frappe.ui.form.on("Bulk Purchase Return Item Table", {

    qty(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        // Validation
        if (row.qty > row.returnable_quantity) {
            frappe.throw(
                `Row ${row.idx}: Qty cannot exceed Returnable Qty (${row.returnable_qty}) for Item ${row.item_code}`
            );
        }

        // Calculate amount
        row.amount = flt(row.qty) * flt(row.rate);

        frm.refresh_field("items");
    }

});