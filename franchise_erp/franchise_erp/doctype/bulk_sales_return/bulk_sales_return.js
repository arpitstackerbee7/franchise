// =============================================================================
// Bulk Sales Return - client script
//
// FIXES (is version me):
//  1) Double scan: ek serial scan par do rows banti thi. Scanner / Barcode field
//     "change" event 2 baar bhejta hai aur purana code field ko server
//     response aane ke BAAD clear karta tha, isliye dono calls duplicate check
//     pass kar leti thi. Ab:
//        - field turant clear hota hai
//        - in-flight guard (pending_serials) hai
//        - server response ke baad dobara duplicate check hota hai
//  2) Regex bug: /[\\n,;]+/ newline ki jagah "\" aur "n" par split karta tha
//     (serial me "n" hota to toot jata). Ab /[\n,;]+/ hai.
//  3) Unused purani functions hata di (open_sales_invoice_dialog,
//     open_return_items_dialog, load_sales_invoice_items,
//     load_common_si_dn_items) aur khali duplicate refresh block.
// =============================================================================

frappe.ui.form.on("Bulk Sales Return", {

    refresh(frm) {

        // IMPORTANT: Failure check submitted-document return se PEHLE.
        if (
            frm.doc.status === "Failed" &&
            frm.doc.error_message &&
            !frm.__bulk_return_error_shown
        ) {
            frm.__bulk_return_error_shown = true;

            frappe.msgprint({
                title: __("Sales Return Could Not Be Completed"),
                message: frappe.utils.escape_html(frm.doc.error_message),
                indicator: "red"
            });
        }

        if (frm.is_new() || frm.doc.docstatus !== 0) {
            return;
        }

        frm.add_custom_button(
            __("Get Items from SI / DN"),
            () => open_si_dn_dialog(frm)
        );

        update_total_quantity(frm);
        hide_items_add_row(frm);
    },

    on_submit(frm) {
        // Submit ke baad background job ka status check karo.
        start_bulk_return_error_polling(frm);
    },

    onload_post_render(frm) {
        hide_items_add_row(frm);
    }
});


function start_bulk_return_error_polling(frm) {

    if (frm.__bulk_return_polling) return;

    frm.__bulk_return_polling = true;

    let attempts = 0;
    const maxAttempts = 600; // 20 minutes, har 2 second

    function poll_status() {

        if (attempts >= maxAttempts) {
            frm.__bulk_return_polling = false;
            return;
        }

        attempts++;

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Bulk Sales Return",
                name: frm.doc.name
            }
        }).then((r) => {

            const doc = r.message || {};
            const status = doc.status;

            if (status === "Failed") {
                frm.__bulk_return_polling = false;
                frm.doc.status = status;
                frm.doc.error_message = doc.error_message || "";

                // Popup server realtime se already aa chuka hai.
                frm.__bulk_return_error_shown = true;

                frm.reload_doc();
                return;
            }

            if (status === "Completed") {
                frm.__bulk_return_polling = false;
                frm.reload_doc();
                return;
            }

            // Abhi bhi Queued / In Progress
            setTimeout(poll_status, 2000);

        }).catch(() => {
            setTimeout(poll_status, 2000);
        });
    }

    poll_status();
}


function hide_items_add_row(frm) {

    const field = frm.get_field("items");

    if (!field || !field.grid) {
        return;
    }

    field.grid.cannot_add_rows = true;
    field.grid.wrapper.find(".grid-add-row").hide();
}


frappe.ui.form.on("Bulk Sales Return Item Table", {

    qty(frm) {
        update_total_quantity(frm);
    },

    items_add(frm) {
        update_total_quantity(frm);
    },

    items_remove(frm) {
        update_total_quantity(frm);
    }
});


function update_total_quantity(frm) {

    let total = 0;

    (frm.doc.items || []).forEach(row => {
        total += flt(row.qty || 0);
    });

    frm.set_value("total_quantity", total);
    frm.refresh_field("total_quantity");
}


// =============================================================================
// LOAD RETURNABLE ITEMS (Item filter select karne par - non serialized)
// =============================================================================

function load_returnable_items(frm, dialog, selected_rows) {

    let customer = dialog.get_value("customer");
    let item_code = dialog.get_value("item_code");

    if (!customer || !item_code) {
        return;
    }

    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_returnable_items",

        args: {
            customer: customer,
            item_code: item_code,
            company: frm.doc.company
        },

        freeze: true,
        freeze_message: "Loading returnable items...",

        callback: function (r) {

            if (!r.message) {
                return;
            }

            let table_field = dialog.fields_dict.items_table;

            if (!table_field) {
                return;
            }

            let old_rows = table_field.df.data || [];
            let new_rows = r.message || [];
            let row_map = {};

            // -------------------------------------------------
            // PRESERVE EXISTING ROWS
            // -------------------------------------------------

            old_rows.forEach(row => {

                let key = row._common_key;

                if (!key) {

                    if (
                        row.source_type === "Sales Invoice" &&
                        row.sales_invoice_item
                    ) {
                        key = `SI::${row.sales_invoice_item}`;

                    } else if (
                        row.source_type === "Delivery Note" &&
                        row.delivery_note_item
                    ) {
                        key = `DN::${row.delivery_note_item}`;
                    }
                }

                if (!key) {
                    key = row._scanned_serial
                        ? `SCANNED::${row._scanned_serial}`
                        : `ROW::${frappe.utils.get_random(8)}`;
                }

                row_map[key] = row;
            });

            // -------------------------------------------------
            // ADD API ROWS
            // -------------------------------------------------

            new_rows.forEach(row => {

                let is_si = !!row.sales_invoice_item;
                let is_dn = !!row.delivery_note_item && !row.sales_invoice_item;

                if (is_si) {
                    row.source_type = "Sales Invoice";
                } else if (is_dn) {
                    row.source_type = "Delivery Note";
                }

                let common_key = null;

                if (row.source_type === "Sales Invoice" && row.sales_invoice_item) {
                    common_key = `SI::${row.sales_invoice_item}`;
                } else if (row.source_type === "Delivery Note" && row.delivery_note_item) {
                    common_key = `DN::${row.delivery_note_item}`;
                }

                if (!common_key) {
                    console.warn("Skipping row because source key missing:", row);
                    return;
                }

                row._common_key = common_key;
                row.rate = flt(row.rate);

                // Serialized item search se auto-add / auto-select nahi hota.
                if (row.has_serial_no) {
                    return;
                }

                if (flt(row.returnable_qty) <= 0) {
                    return;
                }

                row.return_qty = 1;
                selected_rows[common_key] = true;

                if (row_map[common_key]) {

                    let existing = row_map[common_key];

                    existing.return_qty = flt(existing.return_qty) || 1;
                    existing.rate = flt(existing.rate) || flt(row.rate);

                } else {
                    row_map[common_key] = row;
                }
            });

            table_field.df.data = Object.values(row_map);
            table_field.grid.refresh();

            // -------------------------------------------------
            // AUTO CHECK
            // -------------------------------------------------

            setTimeout(() => {

                let grid = table_field.grid;

                if (!grid || !grid.grid_rows) {
                    return;
                }

                grid.grid_rows.forEach(gr => {

                    let row = gr.doc;

                    if (!row) {
                        return;
                    }

                    let key = row._common_key;

                    if (!key) {

                        if (row.source_type === "Sales Invoice" && row.sales_invoice_item) {
                            key = `SI::${row.sales_invoice_item}`;
                        } else if (row.source_type === "Delivery Note" && row.delivery_note_item) {
                            key = `DN::${row.delivery_note_item}`;
                        }
                    }

                    if (!key) {
                        return;
                    }

                    let checkbox = gr.wrapper.find(".grid-row-check");

                    if (checkbox.length) {
                        checkbox.prop("checked", !!selected_rows[key]);
                    }
                });

                update_common_scan_total(dialog, selected_rows);

            }, 150);
        }
    });
}


// =============================================================================
// MAIN DIALOG: Get Items from SI / DN
// =============================================================================

function open_si_dn_dialog(frm) {

    let selected_rows = {};

    // Jin serials ka server call abhi chal raha hai (double scan guard)
    const pending_serials = new Set();

    // =========================================================================
    // HELPERS
    // =========================================================================

    function get_serials(serial_nos) {
        return (serial_nos || "")
            .split("\n")
            .map(s => s.trim())
            .filter(Boolean);
    }

    // Serialized: har serial alag row. Non-serialized: same source item = same row.
    function get_row_key(d) {

        if (!d) {
            return null;
        }

        if (d.has_serial_no) {

            let serials = get_serials(d.serial_nos);
            let serial = serials.length ? serials[0] : d._scanned_serial;

            if (d.source_type === "Sales Invoice") {

                if (d.sales_invoice_item && serial) {
                    return `SI::${d.sales_invoice_item}::SERIAL::${serial}`;
                }

            } else if (d.source_type === "Delivery Note") {

                if (d.delivery_note_item && serial) {
                    return `DN::${d.delivery_note_item}::SERIAL::${serial}`;
                }
            }
        }

        if (d._common_key) {
            return d._common_key;
        }

        if (d.source_type === "Sales Invoice") {
            return d.sales_invoice_item ? `SI::${d.sales_invoice_item}` : null;
        }

        if (d.source_type === "Delivery Note") {
            return d.delivery_note_item ? `DN::${d.delivery_note_item}` : null;
        }

        return null;
    }

    function get_source_key(d) {

        if (!d) {
            return null;
        }

        if (d.source_type === "Sales Invoice") {
            return d.sales_invoice_item ? `SI::${d.sales_invoice_item}` : null;
        }

        if (d.source_type === "Delivery Note") {
            return d.delivery_note_item ? `DN::${d.delivery_note_item}` : null;
        }

        return null;
    }

    function serial_exists_in_main_form(serial) {

        let exists = false;

        (frm.doc.items || []).forEach(row => {

            if (!row.serial_nos) {
                return;
            }

            if (get_serials(row.serial_nos).includes(serial)) {
                exists = true;
            }
        });

        return exists;
    }

    function serial_exists_in_dialog(serial) {

        let rows = dialog.fields_dict.items_table.df.data || [];

        return rows.some(row => get_serials(row.serial_nos).includes(serial));
    }

    function refresh_dialog_grid() {

        let table_field = dialog.fields_dict.items_table;

        if (!table_field || !table_field.grid) {
            return;
        }

        let grid = table_field.grid;

        grid.refresh();

        frappe.after_ajax(() => {

            setTimeout(() => {

                if (!grid.grid_rows) {
                    return;
                }

                grid.grid_rows.forEach(gr => {

                    let key = get_row_key(gr.doc);

                    if (!key) {
                        return;
                    }

                    let checkbox = gr.wrapper.find(".grid-row-check");

                    if (!checkbox.length) {
                        return;
                    }

                    let should_check = !!selected_rows[key];

                    if (should_check !== checkbox.prop("checked")) {
                        checkbox.prop("checked", should_check);
                    }
                });

                update_common_scan_total(dialog, selected_rows);

            }, 100);
        });
    }

    function focus_serial_input(delay = 100) {

        setTimeout(() => {

            if (
                dialog.fields_dict.serial_no &&
                dialog.fields_dict.serial_no.$input
            ) {
                dialog.fields_dict.serial_no.$input.focus();
            }

        }, delay);
    }

    // =========================================================================
    // SERIAL SCAN HANDLER
    // =========================================================================

    function handle_serial_scan() {

        let serial = (dialog.get_value("serial_no") || "").trim();

        if (!serial) {
            return;
        }

        // FIX 1: field turant clear karo (call khatam hone ka intezaar nahi).
        // Isse wahi value dobara "change" fire nahi karti.
        dialog.set_value("serial_no", "");

        // FIX 2: same serial ka call pehle se chal raha hai -> chupchap ignore.
        if (pending_serials.has(serial)) {
            return;
        }

        // Main form me pehle se hai
        if (serial_exists_in_main_form(serial)) {

            frappe.msgprint(
                __("Serial {0} already exists in the Items table.", [serial])
            );

            focus_serial_input(100);
            return;
        }

        // Dialog me pehle se scan ho chuka hai
        if (serial_exists_in_dialog(serial)) {

            frappe.msgprint(
                __("Serial {0} is already scanned.", [serial])
            );

            focus_serial_input(100);
            return;
        }

        pending_serials.add(serial);

        frappe.call({

            method:
                "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_return_source_from_serial",

            args: {
                serial_no: serial,
                company: frm.doc.company,
                customer: dialog.get_value("customer")
            },

            freeze: true,
            freeze_message: "Finding return source...",

            always: function () {
                pending_serials.delete(serial);
            },

            callback: function (r) {

                // NOT FOUND
                if (!r.message) {

                    frappe.msgprint(
                        __(
                            "Serial {0} was not found in any submitted Sales Invoice or Delivery Note.",
                            [serial]
                        )
                    );

                    focus_serial_input(100);
                    return;
                }

                // FIX 3: server response ke baad dobara duplicate check
                // (koi doosra call isi beech row add kar chuka ho to).
                if (serial_exists_in_dialog(serial)) {
                    focus_serial_input(100);
                    return;
                }

                let d = r.message;
                let is_serialized = !!d.has_serial_no;

                // =============================================================
                // SERIALIZED: har serial = alag row
                // =============================================================

                if (is_serialized) {

                    d._scanned_serial = serial;
                    d.serial_nos = serial;

                    d._common_key = get_row_key({
                        ...d,
                        serial_nos: serial
                    });

                    if (!d._common_key) {

                        frappe.msgprint(
                            __(
                                "Unable to identify the return source for Serial {0}.",
                                [serial]
                            )
                        );

                        focus_serial_input(100);
                        return;
                    }

                    // Same key wali row pehle se ho to dobara add nahi karni
                    let existing_rows = dialog.fields_dict.items_table.df.data || [];

                    if (existing_rows.some(row => row._common_key === d._common_key)) {
                        focus_serial_input(100);
                        return;
                    }

                    d.return_qty = 1;
                    selected_rows[d._common_key] = true;

                    existing_rows.unshift(d);
                    dialog.fields_dict.items_table.df.data = existing_rows;

                    refresh_dialog_grid();
                    focus_serial_input(200);
                    return;
                }

                // =============================================================
                // NON-SERIALIZED
                // =============================================================

                let common_key = get_source_key(d);

                if (!common_key) {

                    frappe.msgprint(
                        __(
                            "Unable to identify the return source for Item {0}.",
                            [d.item_code]
                        )
                    );

                    focus_serial_input(100);
                    return;
                }

                d._common_key = common_key;

                let table_field = dialog.fields_dict.items_table;
                let rows = table_field.df.data || [];

                let index = rows.findIndex(
                    row =>
                        get_source_key(row) === common_key &&
                        !row.has_serial_no
                );

                if (index !== -1) {

                    let existing = rows[index];
                    let new_qty = flt(existing.return_qty) + 1;
                    let returnable = flt(existing.returnable_qty);

                    if (new_qty > returnable) {

                        frappe.msgprint(
                            __(
                                "Return Qty cannot exceed Returnable Qty for Item {0}. Allowed Qty: {1}",
                                [existing.item_code, returnable]
                            )
                        );

                        focus_serial_input(100);
                        return;
                    }

                    existing.return_qty = new_qty;
                    selected_rows[common_key] = true;

                    if (d.delivery_note) {
                        existing.delivery_note = d.delivery_note;
                    }

                    if (d.delivery_note_item) {
                        existing.delivery_note_item = d.delivery_note_item;
                    }

                    rows.splice(index, 1);
                    rows.unshift(existing);

                } else {

                    if (flt(d.returnable_qty) <= 0) {

                        frappe.msgprint(
                            __(
                                "No returnable quantity is available for Item {0}.",
                                [d.item_code]
                            )
                        );

                        focus_serial_input(100);
                        return;
                    }

                    d.return_qty = 1;
                    selected_rows[common_key] = true;
                    rows.unshift(d);
                }

                table_field.df.data = rows;

                refresh_dialog_grid();
                focus_serial_input(200);
            }
        });
    }

    // =========================================================================
    // DIALOG
    // =========================================================================

    let dialog = new frappe.ui.Dialog({

        title: "Return Items from Sales Invoice / Delivery Note",
        size: "extra-large",

        fields: [

            {
                fieldname: "customer",
                label: "Customer",
                fieldtype: "Link",
                options: "Customer",
                default: frm.doc.customer,
                read_only: 1,
                reqd: 1
            },

            {
                fieldname: "item_code",
                label: "Item",
                fieldtype: "Link",
                options: "Item",

                onchange() {

                    if (!dialog.get_value("item_code")) {
                        return;
                    }

                    load_returnable_items(frm, dialog, selected_rows);
                }
            },

            {
                fieldname: "serial_no",
                label: "Scan Serial",
                fieldtype: "Data",
                options: "Barcode",

                onchange() {
                    handle_serial_scan();
                }
            },

            {
                fieldname: "total_quantity",
                label: "Total Quantity",
                fieldtype: "Float",
                read_only: 1,
                default: 0
            },

            {
                fieldname: "items_table",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                in_place_edit: true,

                fields: [

                    {
                        fieldname: "sales_invoice",
                        label: "Sales Invoice",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    },

                    {
                        fieldname: "delivery_note",
                        label: "Delivery Note",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    },

                    {
                        fieldname: "item_code",
                        label: "Item",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 1
                    },

                    {
                        fieldname: "returnable_qty",
                        label: "Returnable",
                        fieldtype: "Float",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 1
                    },

                    {
                        fieldname: "returned_qty",
                        label: "Returned",
                        fieldtype: "Float",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 1
                    },

                    {
                        fieldname: "return_qty",
                        label: "Return Qty",
                        fieldtype: "Float",
                        in_list_view: 1,
                        columns: 1,

                        onchange() {

                            let d = this.doc;

                            if (!d) {
                                return;
                            }

                            // SERIALIZED: ek serial = ek qty
                            if (d.has_serial_no) {

                                let serials = get_serials(d.serial_nos);

                                d.return_qty = serials.length;

                                if (serials.length > 1) {
                                    d.serial_nos = serials[0];
                                    d.return_qty = 1;
                                }

                                return;
                            }

                            // NON-SERIALIZED
                            let returnable = flt(d.returnable_qty);
                            let qty = flt(d.return_qty);

                            if (qty > returnable) {

                                d.return_qty = returnable;

                                frappe.msgprint(
                                    __(
                                        "Return Qty cannot exceed Returnable Qty for Item {0}. Allowed Qty: {1}",
                                        [d.item_code, returnable]
                                    )
                                );
                            }

                            update_common_scan_total(dialog, selected_rows);
                        }
                    },

                    {
                        fieldname: "serial_nos",
                        label: "Serial Nos",
                        fieldtype: "Small Text",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    }
                ]
            }
        ],

        // =====================================================================
        // PRIMARY ACTION
        // =====================================================================

        primary_action_label: "Add Selected Items",

        primary_action() {

            let all_rows = dialog.fields_dict.items_table.df.data || [];

            let selected = all_rows.filter(row => {

                let key = get_row_key(row);

                return key && !!selected_rows[key];
            });

            if (!selected.length) {
                frappe.msgprint("Please select rows.");
                return;
            }

            // -----------------------------------------------------------------
            // VALIDATE
            // -----------------------------------------------------------------

            for (let d of selected) {

                if (d.has_serial_no) {

                    let serials = get_serials(d.serial_nos);

                    if (serials.length !== 1) {
                        frappe.throw(
                            __(
                                "Each serialized item row must contain exactly one Serial Number for Item {0}.",
                                [d.item_code]
                            )
                        );
                    }

                    if (flt(d.return_qty) !== 1) {
                        frappe.throw(
                            __(
                                "Return Qty must be 1 for serialized Item {0}.",
                                [d.item_code]
                            )
                        );
                    }

                    continue;
                }

                let qty = flt(d.return_qty);
                let returnable = flt(d.returnable_qty);

                if (qty <= 0) {
                    frappe.throw(
                        __("Return Qty must be greater than 0 for Item {0}.", [d.item_code])
                    );
                }

                if (qty > returnable) {
                    frappe.throw(
                        __(
                            "Return Qty cannot exceed Returnable Qty for Item {0}. Allowed Qty: {1}, Requested Qty: {2}",
                            [d.item_code, returnable, qty]
                        )
                    );
                }
            }

            // -----------------------------------------------------------------
            // DUPLICATE SERIAL SKIP (main table + current selection)
            // FIX: regex pehle /[\\n,;]+/ tha (galat), ab /[\n,;]+/
            // -----------------------------------------------------------------

            const normalize_serials = value =>
                (value || "")
                    .split(/[\n,;]+/)
                    .map(serial => serial.trim())
                    .filter(Boolean);

            const serials_already_added = new Set();

            (frm.doc.items || []).forEach(row => {
                normalize_serials(row.serial_nos).forEach(serial => {
                    serials_already_added.add(serial);
                });
            });

            const unique_selected = [];

            selected.forEach(d => {

                if (!d.has_serial_no) {
                    unique_selected.push(d);
                    return;
                }

                const serials = normalize_serials(d.serial_nos);

                if (!serials.length) {
                    unique_selected.push(d);
                    return;
                }

                const serial = serials[0];

                if (serials_already_added.has(serial)) {

                    frappe.show_alert({
                        message: __(
                            "Serial No. {0} is already added. Duplicate row skipped.",
                            [serial]
                        ),
                        indicator: "orange"
                    });

                    return;
                }

                serials_already_added.add(serial);
                d.serial_nos = serial;
                d.return_qty = 1;
                unique_selected.push(d);
            });

            selected = unique_selected;

            if (!selected.length) {
                frappe.msgprint(
                    __("All selected serial numbers are already present in Items.")
                );
                return;
            }

            // -----------------------------------------------------------------
            // ADD TO MAIN FORM
            // -----------------------------------------------------------------

            selected.forEach(d => {

                // =============================================================
                // SALES INVOICE
                // =============================================================

                if (d.source_type === "Sales Invoice") {

                    // SERIALIZED SI: hamesha nayi row
                    if (d.has_serial_no) {

                        let row = frm.add_child("items");

                        row.item_code = d.item_code;
                        row.item_name = d.item_name;
                        row.qty = 1;
                        row.rate = d.rate;
                        row.sales_invoice = d.sales_invoice;
                        row.sales_invoice_item = d.sales_invoice_item;
                        row.warehouse = d.warehouse;
                        row.returnable_quantity = d.returnable_qty;

                        if (d.delivery_note) {
                            row.delivery_note = d.delivery_note;
                        }

                        if (d.delivery_note_item) {
                            row.delivery_note_item = d.delivery_note_item;
                        }

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "serial_nos",
                            d.serial_nos
                        );

                        return;
                    }

                    // NON-SERIALIZED SI
                    let existing = frm.doc.items.find(
                        row => row.sales_invoice_item === d.sales_invoice_item
                    );

                    if (existing) {

                        let new_qty = flt(existing.qty) + flt(d.return_qty);

                        if (new_qty > flt(d.returnable_qty)) {
                            frappe.throw(
                                __(
                                    "Return Qty exceeded for Item {0}. Allowed Qty: {1}, Requested Total: {2}",
                                    [existing.item_code, d.returnable_qty, new_qty]
                                )
                            );
                        }

                        frappe.model.set_value(
                            existing.doctype,
                            existing.name,
                            "qty",
                            new_qty
                        );

                        if (d.delivery_note) {
                            frappe.model.set_value(
                                existing.doctype,
                                existing.name,
                                "delivery_note",
                                d.delivery_note
                            );
                        }

                        if (d.delivery_note_item) {
                            frappe.model.set_value(
                                existing.doctype,
                                existing.name,
                                "delivery_note_item",
                                d.delivery_note_item
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

                        if (d.delivery_note) {
                            row.delivery_note = d.delivery_note;
                        }

                        if (d.delivery_note_item) {
                            row.delivery_note_item = d.delivery_note_item;
                        }
                    }
                }

                // =============================================================
                // DELIVERY NOTE
                // =============================================================

                else if (d.source_type === "Delivery Note") {

                    // SERIALIZED DN: hamesha nayi row
                    if (d.has_serial_no) {

                        let row = frm.add_child("items");

                        row.delivery_note = d.delivery_note;
                        row.delivery_note_item = d.delivery_note_item;
                        row.item_code = d.item_code;
                        row.item_name = d.item_name;
                        row.qty = 1;
                        row.uom = d.uom;
                        row.stock_uom = d.stock_uom;
                        row.conversion_factor = d.conversion_factor;
                        row.rate = d.rate;
                        row.warehouse = d.warehouse;
                        row.returnable_quantity = d.returnable_qty;

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "serial_nos",
                            d.serial_nos
                        );

                        return;
                    }

                    // NON-SERIALIZED DN
                    let existing = frm.doc.items.find(
                        row =>
                            row.delivery_note_item === d.delivery_note_item &&
                            row.warehouse === d.warehouse
                    );

                    if (existing) {

                        let new_qty = flt(existing.qty) + flt(d.return_qty);

                        if (new_qty > flt(d.returnable_qty)) {
                            frappe.throw(
                                __(
                                    "Return Qty exceeded for Item {0}. Allowed Qty: {1}, Requested Total: {2}",
                                    [existing.item_code, d.returnable_qty, new_qty]
                                )
                            );
                        }

                        frappe.model.set_value(
                            existing.doctype,
                            existing.name,
                            "qty",
                            new_qty
                        );

                    } else {

                        let row = frm.add_child("items");

                        row.delivery_note = d.delivery_note;
                        row.delivery_note_item = d.delivery_note_item;
                        row.item_code = d.item_code;
                        row.item_name = d.item_name;
                        row.qty = d.return_qty;
                        row.uom = d.uom;
                        row.stock_uom = d.stock_uom;
                        row.conversion_factor = d.conversion_factor;
                        row.rate = d.rate;
                        row.warehouse = d.warehouse;
                        row.returnable_quantity = d.returnable_qty;
                    }
                }
            });

            // -----------------------------------------------------------------
            // REFRESH MAIN FORM
            // -----------------------------------------------------------------

            frm.refresh_field("items");

            setTimeout(() => {
                update_total_quantity(frm);
            }, 50);

            dialog.hide();
        }
    });

    dialog.show();

    // Dialog ke checkbox / row-number columns narrow
    if (!document.getElementById("bsr-dialog-check-style")) {

        const style = document.createElement("style");

        style.id = "bsr-dialog-check-style";

        style.innerHTML = `
            .modal .grid-row .row-check,
            .modal .grid-heading-row .row-check {
                flex: 0 0 28px !important;
                max-width: 28px !important;
                width: 28px !important;
            }

            .modal .grid-row .row-index,
            .modal .grid-heading-row .row-index {
                flex: 0 0 32px !important;
                max-width: 32px !important;
                width: 32px !important;
            }
        `;

        document.head.appendChild(style);
    }

    // =========================================================================
    // CHECKBOX CHANGE
    // =========================================================================

    dialog.$wrapper.on("change", ".grid-row-check", function () {

        let checkbox = $(this);
        let grid = dialog.fields_dict.items_table.grid;
        let grid_row = checkbox.closest(".grid-row");
        let row_name = grid_row.attr("data-name");
        let target_row = null;

        if (row_name && grid.grid_rows_by_docname) {
            target_row = grid.grid_rows_by_docname[row_name];
        }

        if (!target_row && grid.grid_rows) {

            grid.grid_rows.forEach(gr => {

                if (gr.wrapper.is(grid_row)) {
                    target_row = gr;
                }
            });
        }

        if (target_row && target_row.doc) {

            let key = get_row_key(target_row.doc);

            if (key) {

                if (checkbox.prop("checked")) {
                    selected_rows[key] = true;
                } else {
                    delete selected_rows[key];
                }
            }
        }

        update_common_scan_total(dialog, selected_rows);
    });

    // =========================================================================
    // ENTER KEY DISABLE
    // =========================================================================

    dialog.$wrapper.on("keydown", function (e) {

        if (e.key === "Enter") {

            e.preventDefault();
            e.stopPropagation();

            return false;
        }
    });

    // INITIAL FOCUS
    setTimeout(() => {

        if (
            dialog.fields_dict.serial_no &&
            dialog.fields_dict.serial_no.$input
        ) {
            dialog.fields_dict.serial_no.$input.focus();
        }

    }, 300);
}


// =============================================================================
// DIALOG TOTAL QUANTITY
// =============================================================================

function update_common_scan_total(dialog, selected_rows) {

    let total = 0;

    (dialog.fields_dict.items_table.df.data || []).forEach(row => {

        let key =
            row._common_key ||
            (
                row.source_type === "Sales Invoice"
                    ? `SI::${row.sales_invoice_item}`
                    : `DN::${row.delivery_note_item}`
            );

        if (selected_rows[key]) {
            total += flt(row.return_qty || 0);
        }
    });

    dialog.set_value("total_quantity", total);
}