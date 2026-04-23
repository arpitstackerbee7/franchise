// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bulk Sales Return", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Bulk Sales Return', {
    refresh(frm) {
      
            if (frm.is_new() || frm.doc.docstatus !== 0) return;
     
            frm.add_custom_button('Get Items from Sales Invoice', () => {
                open_sales_invoice_dialog(frm);
            });
        
    }
});

frappe.ui.form.on("Bulk Sales Return", {
    refresh(frm) {

        if (frm.is_new() || frm.doc.docstatus !== 0) return;

        frm.add_custom_button("Get Items from Delivery Notes", () => {
            open_return_items_dialog(frm);
        });

    }
});
frappe.ui.form.on('Bulk Sales Return', {
    refresh: function(frm) {

        if (frm.doc.docstatus !== 1) return;

        // 🔥 Check if any draft Return DNs exist
        Promise.all([
    frappe.call({
        method: 'franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.has_draft_return_dns',
        args: { docname: frm.doc.name }
       }),
     frappe.call({
         method: 'franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.has_draft_return_sis',
         args: { docname: frm.doc.name }
       })
    ]).then(([dn_res, si_res]) => {

        if (dn_res.message || si_res.message) {

        frm.add_custom_button('Submit Returns', async function() {

                await frappe.call({
                    method: 'franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.submit_created_returns',
                    args: { docname: frm.doc.name },
                     freeze: true,
                     freeze_message: 'Submitting in background...'
                 });

                  frappe.msgprint('Submission started in background.');
                  frm.reload_doc();
              });

            }
         });
        // frappe.call({
        //     method: 'franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.has_draft_return_dns',
        //     args: {
        //         docname: frm.doc.name
        //     },
            
        //     callback: function(r) {

        //         if (r.message) {
        //             // ✅ Only show button if drafts exist
        //             frm.add_custom_button('Submit Return DNs', async function() {

        //                 await frappe.call({
        //                     method: 'franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.submit_created_dns',
        //                     args: {
        //                         docname: frm.doc.name
        //                     },
        //                     freeze: true,
        //                     freeze_message: 'Submitting Return Delivery Notes...'
        //                 });

        //                 frappe.msgprint('Return Delivery Notes Submitted');
        //                 frm.reload_doc(); // 🔥 refresh after submit
        //             });
        //         }
        //     }
        // });
    }
});
function open_sales_invoice_dialog(frm) {

    let dialog = new frappe.ui.Dialog({
        title: "Return Items from Sales Invoice",
        size: "extra-large",

        fields: [

            {
                fieldname: "customer",
                label: "Customer",
                fieldtype: "Link",
                options: "Customer",
                default: frm.doc.customer,
                read_only: 1,
                reqd: 1,
                onchange() {
                    load_sales_invoice_items(frm, dialog);
                }
            },

            {
                fieldname: "item_code",
                label: "Item",
                fieldtype: "Link",
                options: "Item",
                onchange() {
                    load_sales_invoice_items(frm, dialog);
                }
            },
            {
                fieldname: "serial_no",
                label: "Scan Serial",
                fieldtype: "Data",

                onchange() {

                    let serial = dialog.get_value("serial_no");
                    if (!serial) return;

                    frappe.call({
                        method: "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_si_from_serial",
                        args: {
                            serial_no: serial,
                            company: frm.doc.company,
                            customer: dialog.get_value("customer")
                        },

                        callback: function(r) {

                            if (!r.message) {
                                frappe.msgprint(`Serial ${serial} not found`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }

                            if (r.message.status !== "Delivered") {
                                frappe.msgprint(`Serial ${serial} is not delivered, cannot return.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }

                            // Prevent duplicate across frm.doc.items
                            let serial_exists = false;

                            (frm.doc.items || []).forEach(row => {
                                if (row.serial_nos && row.serial_nos.split("\n").includes(serial)) {
                                    serial_exists = true;
                                }
                            });

                            if (serial_exists) {
                                frappe.msgprint(`Serial ${serial} already exists in the Items table.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }

                            let table = dialog.fields_dict.items_table.grid;
                            let rows = table.get_data();

                            let index = rows.findIndex(d =>
                                d.sales_invoice_item === r.message.sales_invoice_item
                            );

                            if (index !== -1) {

                                let existing = rows[index];

                                if (existing.serial_nos && existing.serial_nos.split("\n").includes(serial)) {
                                    frappe.msgprint(`Serial ${serial} already scanned`);
                                } else {

                                    existing.return_qty = (existing.return_qty || 0) + 1;

                                    existing.serial_nos =
                                        existing.serial_nos
                                            ? existing.serial_nos + "\n" + serial
                                            : serial;

                                    rows.splice(index, 1);
                                    rows.unshift(existing);
                                }

                            } else {

                                r.message.return_qty = 1;
                                r.message.serial_nos = serial;

                                rows.unshift(r.message);
                            }

                            table.refresh();

                            frappe.after_ajax(() => {
                                setTimeout(() => {
                                    let grid = dialog.fields_dict.items_table.grid;

                                    if (grid.grid_rows.length) {
                                        let row = grid.grid_rows[0];

                                        let checkbox = row.wrapper.find('.grid-row-check');

                                        if (!checkbox.prop("checked")) {
                                            checkbox.click();
                                        }
                                    }
                                }, 200);
                            });

                            dialog.set_value("serial_no", "");
                            dialog.fields_dict.serial_no.$input.focus();
                        }
                    });
                }
            },

            {
                fieldname: "items_table",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                in_place_edit: true,

                fields: [

                    { fieldname: "sales_invoice", label: "Sales Invoice", fieldtype: "Data", in_list_view: 1, read_only: 1 },

                    { fieldname: "item_code", label: "Item", fieldtype: "Data", in_list_view: 1,read_only:1 },

                    { fieldname: "returnable_qty", label: "Returnable Qty", fieldtype: "Float", in_list_view: 1,read_only:1 },

                    { fieldname: "returned_qty", label: "Already Returned", fieldtype: "Float", in_list_view: 1,read_only:1},

                    {
                        fieldname: "return_qty",
                        label: "Return Qty",
                        fieldtype: "Float",
                        in_list_view: 1,
                        onchange() {

                            let grid = dialog.fields_dict.items_table.grid;
                            let row = grid.get_row(this.doc.name);
                            let d = row.doc;

                            // Serialized item rule
                            if (d.has_serial_no == 1) {

                                let serial_count = 0;

                                if (d.serial_nos) {
                                    serial_count = d.serial_nos
                                        .split("\n")
                                        .filter(s => s.trim()).length;
                                }

                                if (serial_count === 0) {

                                    frappe.msgprint(
                                        __("Scan Serial Numbers first for serialized item {0}.", [d.item_code])
                                    );

                                    d.return_qty = 0;
                                    grid.refresh();
                                    return;
                                }

                                // keep qty in sync with scanned serial count
                                d.return_qty = serial_count;

                                grid.refresh();
                                return;
                            }

                            // ❌ Prevent zero or empty
                            if (!d.return_qty || d.return_qty <= 0) {
                                frappe.msgprint(`Please enter valid Return Qty for Item ${d.item_code}`);
                                d.return_qty = 0;
                                grid.refresh();
                                return;
                            }

                            // ❌ Exceed validation
                            if (flt(d.return_qty) > flt(d.returnable_qty)) {
                                frappe.msgprint(`Return Qty cannot exceed ${d.returnable_qty}`);
                                d.return_qty = d.returnable_qty;
                                grid.refresh();
                            }
                        }
                    },

                    { fieldname: "serial_nos", label: "Serial Nos", fieldtype: "Small Text", in_list_view: 1, read_only: 1 },

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

            // 🔥 FINAL VALIDATION
            for (let d of selected_rows) {

                if (!d.return_qty || d.return_qty <= 0) {
                    frappe.throw(`Return Qty must be greater than 0 for Item ${d.item_code}`);
                }

                if (flt(d.return_qty) > flt(d.returnable_qty)) {
                    frappe.throw(`Return Qty cannot exceed Returnable Qty for Item ${d.item_code}`);
                }

                if (d.has_serial_no == 1) {

                    let serials = (d.serial_nos || "")
                        .split("\n")
                        .filter(s => s.trim());

                    if (!serials.length) {
                        frappe.throw(`Please scan Serial Numbers for Item ${d.item_code}`);
                    }

                    if (serials.length !== flt(d.return_qty)) {
                        frappe.throw(`Serial count must match Return Qty for Item ${d.item_code}`);
                    }
                }
            }

            // Merge rows scanned multiple times for the same SI item
            let merged_rows = {};

            selected_rows.forEach(d => {

                let key = d.sales_invoice_item;

                if (!merged_rows[key]) {
                    merged_rows[key] = { ...d };
                } else {

                    merged_rows[key].return_qty =
                        flt(merged_rows[key].return_qty) + flt(d.return_qty);

                    if (d.serial_nos) {

                        merged_rows[key].serial_nos =
                            (merged_rows[key].serial_nos || "") +
                            "\n" +
                            d.serial_nos;
                    }
                }
            });

            selected_rows = Object.values(merged_rows);

            selected_rows.forEach(d => {

                let existing = frm.doc.items.find(row =>
                    row.sales_invoice_item === d.sales_invoice_item
                );

                if (existing) {

                    let new_qty = flt(existing.qty) + flt(d.return_qty);

                    if (new_qty > flt(existing.returnable_quantity)) {
                        frappe.throw(
                            __("Return Qty exceeded for Item {0}. Allowed Qty: {1}",
                            [existing.item_code, existing.returnable_quantity])
                        );
                        return;
                    }

                    frappe.model.set_value(existing.doctype, existing.name, "qty", new_qty);

                    if (d.serial_nos) {

                        let existing_serials = existing.serial_nos
                            ? existing.serial_nos.split("\n").filter(s => s.trim())
                            : [];

                        let new_serials = d.serial_nos
                            ? d.serial_nos.split("\n").filter(s => s.trim())
                            : [];

                        let merged = [...new Set([...existing_serials, ...new_serials])];

                        frappe.model.set_value(
                            existing.doctype,
                            existing.name,
                            "serial_nos",
                            merged.join("\n")
                        );
                    }

                } else {

                    let row = frm.add_child("items");

                    row.item_code = d.item_code;
                    row.item_name = d.item_name;
                    row.qty = d.return_qty;
                    row.rate = d.rate;
                    row.sales_invoice = d.sales_invoice;
                    row.sales_invoice_item = d.sales_invoice_item;
                    row.warehouse = d.warehouse;
                    row.returnable_quantity = d.returnable_qty;

                    if (d.serial_nos) {
                        frappe.model.set_value(row.doctype, row.name, "serial_nos", d.serial_nos);
                    }
                }
            });

            frm.refresh_field("items");
            dialog.hide();
        }
    });

    dialog.show();

    load_sales_invoice_items(frm, dialog);
}
function open_return_items_dialog(frm) {

    let dialog = new frappe.ui.Dialog({
        title: "Return Items against Delivery Note",
        size: "extra-large",

        fields: [
            {
                fieldname: "customer",
                label: "Customer",
                fieldtype: "Link",
                options: "Customer",
                default: frm.doc.customer,
                read_only:1,
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
                fieldname: "serial_no",
                label: "Scan Serial",
                fieldtype: "Data",
            
                onchange() {
            
                    let serial = dialog.get_value("serial_no");
                    if (!serial) return;
            
                    frappe.call({
                        method: "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_dn_from_serial",
                        args: {
                            serial_no: serial,
                            company: frm.doc.company
                        },
            
                        callback: function(r) {

                            if (!r.message) {
                                frappe.msgprint(`Serial ${serial} not found`);
                                dialog.set_value("serial_no", "");
                                return;
                            }
                        
                            // ❌ Condition 1 — Serial status Active
                            if (r.message.status !== "Delivered") {
                                frappe.msgprint(`Serial ${serial} is not delivered, cannot return.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }
                        
                            // ❌ Condition 2 — Serial already exists in Items child table
                            let serial_exists = false;
                        
                            (frm.doc.items || []).forEach(row => {
                                if (row.serial_nos && row.serial_nos.split("\n").includes(serial)) {
                                    serial_exists = true;
                                }
                            });
                        
                            if (serial_exists) {
                                frappe.msgprint(`Serial ${serial} already exists in the Items table.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }
                        
                            let table = dialog.fields_dict.items_table.grid;
                            let rows = table.get_data();

                            let index = rows.findIndex(d =>
                                d.delivery_note === r.message.delivery_note &&
                                d.item_code === r.message.item_code
                            );

                            if (index !== -1) {

                                let existing = rows[index];

                                // Prevent duplicate serial
                                if (existing.serial_nos && existing.serial_nos.split("\n").includes(serial)) {
                                    frappe.msgprint(`Serial ${serial} already scanned`);
                                } else {

                                    existing.return_qty = (existing.return_qty || 0) + 1;

                                    existing.serial_nos =
                                        existing.serial_nos
                                            ? existing.serial_nos + "\n" + serial
                                            : serial;

                                    // 🔥 MOVE UPDATED ROW TO TOP
                                    rows.splice(index, 1);   // remove from old position
                                    rows.unshift(existing);  // add to top
                                }

                            } else {

                                r.message.return_qty = 1;
                                r.message.serial_nos = serial;

                                // 🔥 ADD NEW ROW TO TOP
                                rows.unshift(r.message);
                            }

                            table.refresh();

                            frappe.after_ajax(() => {
                                setTimeout(() => {
                                    let grid = dialog.fields_dict.items_table.grid;
                            
                                    if (grid.grid_rows.length) {
                                        let row = grid.grid_rows[0];
                            
                                        let checkbox = row.wrapper.find('.grid-row-check');
                            
                                        // ✅ Only click if NOT already checked
                                        if (!checkbox.prop("checked")) {
                                            checkbox.click();
                                        }
                                    }
                                }, 200);
                            });
                        
                            dialog.set_value("serial_no", "");
                            dialog.fields_dict.serial_no.$input.focus();
                        }
                    });
                }
            },

            {
                fieldname: "items_table",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                in_place_edit: true,

                fields: [

                    { fieldname: "delivery_note", label: "Delivery Note", fieldtype: "Data", read_only: 1, in_list_view: 1},

                    { fieldname: "item_code", label: "Item", fieldtype: "Data", read_only: 1, in_list_view: 1},
                    
                    { fieldname: "returnable_qty", label: "Returnable Qty", fieldtype: "Float", read_only: 1, in_list_view: 1 },
                    
                    { fieldname: "returned_qty", label: "Already Returned", fieldtype: "Float", read_only: 1, in_list_view: 1},

                    {
                        fieldname: "return_qty",
                        label: "Return Qty",
                        fieldtype: "Float",
                        in_list_view: 1,
                        onchange() {
                    
                            let grid = dialog.fields_dict.items_table.grid;
                            let row = grid.get_row(this.doc.name);
                            let d = row.doc;
                    
                            // Serialized item rule
                            if (d.has_serial_no == 1) {
                    
                                let serial_count = 0;
                    
                                if (d.serial_nos) {
                                    serial_count = d.serial_nos
                                        .split("\n")
                                        .filter(s => s.trim()).length;
                                }
                    
                                if (serial_count === 0) {
                    
                                    frappe.msgprint(
                                        __("Scan Serial Numbers first for serialized item {0}.", [d.item_code])
                                    );
                    
                                    d.return_qty = 0;
                                    grid.refresh();
                                    return;
                                }
                    
                                // always sync qty with serial count
                                d.return_qty = serial_count;
                    
                                grid.refresh();
                                return;
                            }
                    
                            // Normal validation for non-serialized
                            if (flt(d.return_qty) > flt(d.returnable_qty)) {
                    
                                frappe.msgprint(
                                    __("Return Qty cannot exceed Returnable Qty for Item {0}", [d.item_code])
                                );
                    
                                d.return_qty = d.returnable_qty;
                                grid.refresh();
                            }
                        }
                    },

                    { fieldname: "serial_nos", label: "Serial Nos", fieldtype: "Small Text", read_only: 1, in_list_view: 1},

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
                        `Please enter Return Qty for Item ${r.item_code} in Delivery Note ${r.delivery_note}`
                    );
                }
        
                if (r.return_qty > r.returnable_qty) {
                    frappe.throw(
                        `Return Qty cannot exceed Returnable Qty for Item ${r.item_code} in Delivery Note ${r.delivery_note}`
                    );
                }
            }
            let merged_rows = {};

            selected_rows.forEach(d => {

                let key = d.delivery_note_item;

                if (!merged_rows[key]) {
                    merged_rows[key] = {...d};
                } else {

                    merged_rows[key].return_qty =
                        flt(merged_rows[key].return_qty) + flt(d.return_qty);

                    if (d.serial_nos) {

                        merged_rows[key].serial_nos =
                            (merged_rows[key].serial_nos || "") +
                            "\n" +
                            d.serial_nos;
                    }
                }

            });
        
            selected_rows = Object.values(merged_rows);

            frappe.call({
                method: "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_dn_item_details",
                args: {
                    items: selected_rows
                },
                callback: function(r) {

                    if (r.message) {

                        try {

                            r.message.forEach(d => {

                                let existing = frm.doc.items.find(row =>
                                    row.delivery_note_item === d.name &&
                                    row.warehouse === d.warehouse
                                );
                                if (existing) {

                                    let new_qty = flt(existing.qty) + flt(d.qty);
                                
                                    // validation
                                    if (new_qty > flt(existing.returnable_quantity)) {
                                        frappe.throw(
                                            __("Return Qty exceeded for Item {0}. Allowed Qty: {1}", 
                                            [existing.item_code, existing.returnable_quantity])
                                        );
                                        return;
                                    }
                                
                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "qty",
                                        new_qty
                                    );
                                
                                    if (d.serial_nos) {
                                
                                        let existing_serials = existing.serial_nos
                                            ? existing.serial_nos.split("\n")
                                            : [];
                                
                                        let new_serials = d.serial_nos
                                            ? d.serial_nos.split("\n")
                                            : [];
                                
                                        let merged = [...new Set([...existing_serials, ...new_serials])];
                                
                                        frappe.model.set_value(
                                            existing.doctype,
                                            existing.name,
                                            "serial_nos",
                                            merged.join("\n")
                                        );
                                    }
                                
                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "available_serial_nos",
                                        d.available_serial_nos
                                    );
                                }
                                 else {

                                    let row = frm.add_child("items");

                                    row.delivery_note = d.delivery_note;
                                    row.delivery_note_item = d.name;
                                    row.item_code = d.item_code;
                                    row.item_name = d.item_name;
                                    row.qty = d.qty;
                                    row.uom = d.uom;
                                    row.stock_uom = d.stock_uom;
                                    row.conversion_factor = d.conversion_factor;
                                    row.rate = d.rate;
                                    row.warehouse = d.warehouse;
                                    row.returnable_quantity = d.returnable_quantity;

                                    frappe.model.set_value(row.doctype, row.name, "serial_nos", d.serial_nos);
                                    frappe.model.set_value(row.doctype, row.name, "available_serial_nos", d.available_serial_nos);
                                }

                            });

                        } catch (e) {
                            console.error("Error adding items:", e);
                        }

                        frm.refresh_field("items");

                        dialog.hide();
                    }
                }
            });
            }
        });

    dialog.show();

    load_returnable_items(frm,dialog);
}

function load_sales_invoice_items(frm, dialog) {

    let customer = dialog.get_value("customer");
    let item_code = dialog.get_value("item_code");

    if (!customer) return;

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_sales_invoice_returnable_items",
        args: {
            customer: customer,
            item_code: item_code,
            company: frm.doc.company
        },
        callback(r) {
            if (!r.message) return;

            dialog.fields_dict.items_table.df.data = r.message;
            dialog.fields_dict.items_table.grid.refresh();
        }
    });
}

function load_returnable_items(frm, dialog) {

    let customer = dialog.get_value("customer");
    let item_code = dialog.get_value("item_code");

    if (!customer) return;

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_returnable_items",
        args: {
            customer: customer,
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