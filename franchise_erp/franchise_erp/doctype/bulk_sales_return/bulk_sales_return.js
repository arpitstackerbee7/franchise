// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt


// =============================================================
// BULK SALES RETURN FORM
// =============================================================

frappe.ui.form.on("Bulk Sales Return", {

    refresh(frm) {

        if (frm.is_new() || frm.doc.docstatus !== 0) {
            return;
        }

        frm.add_custom_button(
            "Get Items from SI / DN",
            () => {
                open_si_dn_dialog(frm);
            }
        );

        frm.add_custom_button(
            "Get Items from Sales Invoice",
            () => {
                open_sales_invoice_dialog(frm);
            }
        );

        frm.add_custom_button(
            "Get Items from Delivery Notes",
            () => {
                open_return_items_dialog(frm);
            }
        );

        update_total_quantity(frm);
    }
});


// =============================================================
// BULK SALES RETURN ITEM TABLE
// =============================================================

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


// =============================================================
// TOTAL QUANTITY
// =============================================================

function update_total_quantity(frm) {

    let total = 0;

    (frm.doc.items || []).forEach(row => {

        total += flt(row.qty || 0);

    });

    frm.set_value(
        "total_quantity",
        total
    );

    frm.refresh_field(
        "total_quantity"
    );
}


// =============================================================
// SUBMITTED BULK RETURN - SUBMIT CREATED RETURNS BUTTON
// =============================================================

frappe.ui.form.on("Bulk Sales Return", {

    refresh: function(frm) {

        if (frm.doc.docstatus !== 1) {
            return;
        }

        Promise.all([

            frappe.call({
                method:
                    "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.has_draft_return_dns",
                args: {
                    docname: frm.doc.name
                }
            }),

            frappe.call({
                method:
                    "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.has_draft_return_sis",
                args: {
                    docname: frm.doc.name
                }
            })

        ]).then(([dn_res, si_res]) => {

            if (
                dn_res.message ||
                si_res.message
            ) {

                frm.add_custom_button(
                    "Submit Returns",
                    async function() {

                        await frappe.call({

                            method:
                                "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.submit_created_returns",

                            args: {
                                docname: frm.doc.name
                            },

                            freeze: true,

                            freeze_message:
                                "Submitting in background..."
                        });

                        frappe.msgprint(
                            "Submission started in background."
                        );

                        frm.reload_doc();
                    }
                );
            }
        });
    }
});


// =============================================================
// SALES INVOICE DIALOG TOTAL
// =============================================================

function update_scan_total_quantity(
    dialog,
    selected_rows
) {

    let total = 0;

    (
        dialog.fields_dict.items_table.df.data ||
        []
    ).forEach(row => {

        if (
            selected_rows[
                row.sales_invoice_item
            ]
        ) {

            total += flt(
                row.return_qty || 0
            );
        }
    });

    dialog.set_value(
        "total_quantity",
        total
    );
}


// =============================================================
// SALES INVOICE DIALOG
// =============================================================

function open_sales_invoice_dialog(frm) {

    let selected_rows = {};

    let dialog = new frappe.ui.Dialog({

        title:
            "Return Items from Sales Invoice",

        size:
            "extra-large",

        fields: [

            // ---------------------------------------------------------
            // CUSTOMER
            // ---------------------------------------------------------

            {
                fieldname: "customer",
                label: "Customer",
                fieldtype: "Link",
                options: "Customer",
                default: frm.doc.customer,
                read_only: 1,
                reqd: 1,

                onchange() {

                    load_sales_invoice_items(
                        frm,
                        dialog,
                        selected_rows
                    );
                }
            },

            // ---------------------------------------------------------
            // ITEM
            // ---------------------------------------------------------

            {
                fieldname: "item_code",
                label: "Item",
                fieldtype: "Link",
                options: "Item",

                onchange() {

                    load_sales_invoice_items(
                        frm,
                        dialog,
                        selected_rows
                    );
                }
            },

            // ---------------------------------------------------------
            // SERIAL SCAN
            // ---------------------------------------------------------

            {
                fieldname: "serial_no",
                label: "Scan Serial",
                fieldtype: "Data",
                options: "Barcode",

                onchange() {

                    let serial =
                        dialog.get_value(
                            "serial_no"
                        );

                    if (!serial) {
                        return;
                    }

                    frappe.call({

                        method:
                            "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_si_from_serial",

                        args: {

                            serial_no:
                                serial,

                            company:
                                frm.doc.company,

                            customer:
                                dialog.get_value(
                                    "customer"
                                )
                        },

                        callback: function(r) {

                            if (!r.message) {

                                frappe.msgprint(
                                    `Serial ${serial} not found`
                                );

                                dialog.set_value(
                                    "serial_no",
                                    ""
                                );

                                dialog.fields_dict
                                    .serial_no
                                    .$input
                                    .focus();

                                return;
                            }

                            if (
                                r.message.status !==
                                "Delivered"
                            ) {

                                frappe.msgprint(
                                    `Serial ${serial} is not delivered, cannot return.`
                                );

                                dialog.set_value(
                                    "serial_no",
                                    ""
                                );

                                dialog.fields_dict
                                    .serial_no
                                    .$input
                                    .focus();

                                return;
                            }

                            // -------------------------------------------------
                            // DUPLICATE SERIAL IN MAIN FORM
                            // -------------------------------------------------

                            let serial_exists = false;

                            (
                                frm.doc.items || []
                            ).forEach(row => {

                                if (
                                    row.serial_nos &&
                                    row.serial_nos
                                        .split("\n")
                                        .includes(serial)
                                ) {

                                    serial_exists = true;
                                }
                            });

                            if (serial_exists) {

                                frappe.msgprint(
                                    `Serial ${serial} already exists in the Items table.`
                                );

                                dialog.set_value(
                                    "serial_no",
                                    ""
                                );

                                dialog.fields_dict
                                    .serial_no
                                    .$input
                                    .focus();

                                return;
                            }

                            // -------------------------------------------------
                            // GRID
                            // -------------------------------------------------

                            let table =
                                dialog.fields_dict
                                    .items_table
                                    .grid;

                            let rows =
                                dialog.fields_dict
                                    .items_table
                                    .df
                                    .data || [];

                            let index =
                                rows.findIndex(d =>
                                    d.sales_invoice_item ===
                                    r.message.sales_invoice_item
                                );

                            if (index !== -1) {

                                let existing =
                                    rows[index];

                                if (
                                    existing.serial_nos &&
                                    existing.serial_nos
                                        .split("\n")
                                        .includes(serial)
                                ) {

                                    frappe.msgprint(
                                        `Serial ${serial} already scanned`
                                    );

                                } else {

                                    existing.return_qty =
                                        flt(
                                            existing.return_qty ||
                                            0
                                        ) + 1;

                                    existing.serial_nos =
                                        existing.serial_nos
                                            ? existing.serial_nos +
                                              "\n" +
                                              serial
                                            : serial;

                                    selected_rows[
                                        existing.sales_invoice_item
                                    ] = true;

                                    rows.splice(
                                        index,
                                        1
                                    );

                                    rows.unshift(
                                        existing
                                    );

                                    dialog.fields_dict
                                        .items_table
                                        .df
                                        .data =
                                        rows;

                                    table.refresh();
                                }

                            } else {

                                r.message.return_qty =
                                    1;

                                r.message.serial_nos =
                                    serial;

                                selected_rows[
                                    r.message.sales_invoice_item
                                ] = true;

                                rows.push(
                                    r.message
                                );

                                dialog.fields_dict
                                    .items_table
                                    .df
                                    .data =
                                    rows;

                                table.refresh();
                            }

                            frappe.after_ajax(() => {

                                let grid =
                                    dialog.fields_dict
                                        .items_table
                                        .grid;

                                setTimeout(() => {

                                    grid.grid_rows.forEach(
                                        gr => {

                                            let checked =
                                                !!selected_rows[
                                                    gr.doc
                                                        .sales_invoice_item
                                                ];

                                            gr.wrapper
                                                .find(
                                                    ".grid-row-check"
                                                )
                                                .prop(
                                                    "checked",
                                                    checked
                                                );
                                        }
                                    );

                                    update_scan_total_quantity(
                                        dialog,
                                        selected_rows
                                    );

                                }, 100);
                            });

                            dialog.set_value(
                                "serial_no",
                                ""
                            );

                            dialog.fields_dict
                                .serial_no
                                .$input
                                .focus();
                        }
                    });
                }
            },

            // ---------------------------------------------------------
            // TOTAL
            // ---------------------------------------------------------

            {
                fieldname: "total_quantity",
                label: "Total Quantity",
                fieldtype: "Float",
                read_only: 1,
                default: 0
            },

            // ---------------------------------------------------------
            // ITEMS TABLE
            // ---------------------------------------------------------

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
                        fieldname: "item_code",
                        label: "Item",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
                    },

                    {
                        fieldname: "serial_nos",
                        label: "Serial Nos",
                        fieldtype: "Data",
                        read_only: 1,
                        in_list_view: 1,
                        columns: 2
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
                        columns: 2,

                        onchange() {

                            let d = this.doc;

                            if (!d) {
                                return;
                            }

                            if (d.has_serial_no) {

                                d.return_qty =
                                    (
                                        d.serial_nos ||
                                        ""
                                    )
                                    .split("\n")
                                    .filter(
                                        x => x.trim()
                                    )
                                    .length;
                            }

                            if (
                                flt(d.return_qty) >
                                flt(d.returnable_qty)
                            ) {

                                d.return_qty =
                                    d.returnable_qty;

                                frappe.msgprint(
                                    "Return Qty cannot exceed Returnable Qty"
                                );
                            }

                            update_scan_total_quantity(
                                dialog,
                                selected_rows
                            );
                        }
                    }
                ]
            }
        ],

        primary_action_label:
            "Add Selected Items",

        primary_action() {

            let selected =
                dialog.fields_dict
                    .items_table
                    .df
                    .data
                    .filter(
                        d =>
                            selected_rows[
                                d.sales_invoice_item
                            ]
                    );

            if (!selected.length) {

                frappe.msgprint(
                    "Please select rows"
                );

                return;
            }

            for (let d of selected) {

                if (
                    !d.return_qty ||
                    d.return_qty <= 0
                ) {

                    frappe.throw(
                        `Return Qty must be greater than 0 for Item ${d.item_code}`
                    );
                }

                if (
                    flt(d.return_qty) >
                    flt(d.returnable_qty)
                ) {

                    frappe.throw(
                        `Return Qty cannot exceed Returnable Qty for Item ${d.item_code}`
                    );
                }

                if (d.has_serial_no == 1) {

                    let serials =
                        (
                            d.serial_nos ||
                            ""
                        )
                        .split("\n")
                        .filter(
                            s => s.trim()
                        );

                    if (!serials.length) {

                        frappe.throw(
                            `Please scan Serial Numbers for Item ${d.item_code}`
                        );
                    }

                    if (
                        serials.length !==
                        flt(d.return_qty)
                    ) {

                        frappe.throw(
                            `Serial count must match Return Qty for Item ${d.item_code}`
                        );
                    }
                }
            }

            // ---------------------------------------------------------
            // MERGE SAME SI ITEM
            // ---------------------------------------------------------

            let merged_rows = {};

            selected.forEach(d => {

                let key =
                    d.sales_invoice_item;

                if (!merged_rows[key]) {

                    merged_rows[key] = {
                        ...d
                    };

                } else {

                    merged_rows[key].return_qty =
                        flt(
                            merged_rows[key].return_qty
                        ) +
                        flt(
                            d.return_qty
                        );

                    if (d.serial_nos) {

                        merged_rows[key].serial_nos =
                            (
                                merged_rows[key]
                                    .serial_nos ||
                                ""
                            ) +
                            "\n" +
                            d.serial_nos;
                    }
                }
            });

            selected =
                Object.values(
                    merged_rows
                );

            // ---------------------------------------------------------
            // ADD TO MAIN FORM
            // ---------------------------------------------------------

            selected.forEach(d => {

                let existing =
                    frm.doc.items.find(
                        row =>
                            row.sales_invoice_item ===
                            d.sales_invoice_item
                    );

                if (existing) {

                    let new_qty =
                        flt(existing.qty) +
                        flt(d.return_qty);

                    if (
                        new_qty >
                        flt(
                            existing.returnable_quantity
                        )
                    ) {

                        frappe.throw(
                            __(
                                "Return Qty exceeded for Item {0}. Allowed Qty: {1}",
                                [
                                    existing.item_code,
                                    existing.returnable_quantity
                                ]
                            )
                        );
                    }

                    frappe.model.set_value(
                        existing.doctype,
                        existing.name,
                        "qty",
                        new_qty
                    );

                    if (d.serial_nos) {

                        let existing_serials =
                            existing.serial_nos
                                ? existing.serial_nos
                                    .split("\n")
                                    .filter(
                                        s => s.trim()
                                    )
                                : [];

                        let new_serials =
                            d.serial_nos
                                ? d.serial_nos
                                    .split("\n")
                                    .filter(
                                        s => s.trim()
                                    )
                                : [];

                        let merged = [
                            ...new Set([
                                ...existing_serials,
                                ...new_serials
                            ])
                        ];

                        frappe.model.set_value(
                            existing.doctype,
                            existing.name,
                            "serial_nos",
                            merged.join("\n")
                        );
                    }

                } else {

                    let row =
                        frm.add_child(
                            "items"
                        );

                    row.item_code =
                        d.item_code;

                    row.item_name =
                        d.item_name;

                    row.qty =
                        d.return_qty;

                    row.rate =
                        d.rate;

                    row.sales_invoice =
                        d.sales_invoice;

                    row.sales_invoice_item =
                        d.sales_invoice_item;

                    row.warehouse =
                        d.warehouse;

                    row.returnable_quantity =
                        d.returnable_qty;

                    if (d.serial_nos) {

                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "serial_nos",
                            d.serial_nos
                        );
                    }
                }
            });

            frm.refresh_field(
                "items"
            );

            setTimeout(() => {

                update_total_quantity(
                    frm
                );

            }, 50);

            dialog.hide();
        }
    });

    dialog.show();

    // ---------------------------------------------------------
    // CHECKBOX CHANGE
    // ---------------------------------------------------------

    dialog.$wrapper.on(
        "change",
        ".grid-row-check",
        function() {

            let grid =
                dialog.fields_dict
                    .items_table
                    .grid;

            grid.grid_rows.forEach(
                row => {

                    let checked =
                        row.wrapper
                            .find(
                                ".grid-row-check"
                            )
                            .prop(
                                "checked"
                            );

                    if (checked) {

                        selected_rows[
                            row.doc.sales_invoice_item
                        ] = true;

                    } else {

                        delete selected_rows[
                            row.doc.sales_invoice_item
                        ];
                    }
                }
            );

            update_scan_total_quantity(
                dialog,
                selected_rows
            );
        }
    );

    // ---------------------------------------------------------
    // ENTER KEY
    // ---------------------------------------------------------

    dialog.$wrapper.on(
        "keydown",
        function(e) {

            if (e.key === "Enter") {

                e.preventDefault();
                e.stopPropagation();

                return false;
            }
        }
    );

    load_sales_invoice_items(
        frm,
        dialog,
        selected_rows
    );
}


// =============================================================
// LOAD SALES INVOICE ITEMS
// =============================================================

function load_sales_invoice_items(
    frm,
    dialog,
    selected_rows
) {

    let customer =
        dialog.get_value(
            "customer"
        );

    let item_code =
        dialog.get_value(
            "item_code"
        );

    if (!customer) {
        return;
    }

    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_sales_invoice_returnable_items",

        args: {

            customer:
                customer,

            item_code:
                item_code,

            company:
                frm.doc.company
        },

        callback(r) {

            if (!r.message) {
                return;
            }

            let old_rows =
                dialog.fields_dict
                    .items_table
                    .df
                    .data || [];

            let new_rows =
                r.message || [];

            let row_map = {};

            old_rows.forEach(
                row => {

                    if (
                        selected_rows[
                            row.sales_invoice_item
                        ]
                    ) {

                        row_map[
                            row.sales_invoice_item
                        ] = row;
                    }
                }
            );

            new_rows.forEach(
                row => {

                    if (
                        row_map[
                            row.sales_invoice_item
                        ]
                    ) {

                        row.return_qty =
                            row_map[
                                row.sales_invoice_item
                            ].return_qty;

                        row.serial_nos =
                            row_map[
                                row.sales_invoice_item
                            ].serial_nos;
                    }

                    row_map[
                        row.sales_invoice_item
                    ] = row;
                }
            );

            dialog.fields_dict
                .items_table
                .df
                .data =
                Object.values(
                    row_map
                );

            let grid =
                dialog.fields_dict
                    .items_table
                    .grid;

            grid.refresh();

            frappe.after_ajax(
                () => {

                    let grid =
                        dialog.fields_dict
                            .items_table
                            .grid;

                    grid.grid_rows.forEach(
                        row => {

                            row.wrapper
                                .find(
                                    ".grid-row-check"
                                )
                                .prop(
                                    "checked",
                                    !!selected_rows[
                                        row.doc
                                            .sales_invoice_item
                                    ]
                                );
                        }
                    );

                    update_scan_total_quantity(
                        dialog,
                        selected_rows
                    );
                }
            );
        }
    });
}


// =============================================================
// DELIVERY NOTE RETURN DIALOG
// =============================================================

function open_return_items_dialog(frm) {

    let dialog =
        new frappe.ui.Dialog({

            title:
                "Return Items against Delivery Note",

            size:
                "extra-large",

            fields: [

                // -------------------------------------------------
                // CUSTOMER
                // -------------------------------------------------

                {
                    fieldname: "customer",
                    label: "Customer",
                    fieldtype: "Link",
                    options: "Customer",
                    default: frm.doc.customer,
                    read_only: 1,
                    reqd: 1,

                    onchange() {

                        load_returnable_items(
                            frm,
                            dialog
                        );
                    }
                },

                // -------------------------------------------------
                // ITEM
                // -------------------------------------------------

                {
                    fieldname: "item_code",
                    label: "Item",
                    fieldtype: "Link",
                    options: "Item",

                    onchange() {

                        load_returnable_items(
                            frm,
                            dialog
                        );
                    }
                },

                // -------------------------------------------------
                // SERIAL
                // -------------------------------------------------

                {
                    fieldname: "serial_no",
                    label: "Scan Serial",
                    fieldtype: "Data",
                    options: "Barcode",

                    onchange() {

                        let serial =
                            dialog.get_value(
                                "serial_no"
                            );

                        if (!serial) {
                            return;
                        }

                        frappe.call({

                            method:
                                "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_dn_from_serial",

                            args: {

                                serial_no:
                                    serial,

                                company:
                                    frm.doc.company
                            },

                            callback: function(r) {

                                if (!r.message) {

                                    frappe.msgprint(
                                        `Serial ${serial} not found`
                                    );

                                    dialog.set_value(
                                        "serial_no",
                                        ""
                                    );

                                    return;
                                }

                                if (
                                    r.message.status !==
                                    "Delivered"
                                ) {

                                    frappe.msgprint(
                                        `Serial ${serial} is not delivered, cannot return.`
                                    );

                                    dialog.set_value(
                                        "serial_no",
                                        ""
                                    );

                                    dialog.fields_dict
                                        .serial_no
                                        .$input
                                        .focus();

                                    return;
                                }

                                // -----------------------------------------
                                // DUPLICATE
                                // -----------------------------------------

                                let serial_exists =
                                    false;

                                (
                                    frm.doc.items ||
                                    []
                                ).forEach(
                                    row => {

                                        if (
                                            row.serial_nos &&
                                            row.serial_nos
                                                .split("\n")
                                                .includes(
                                                    serial
                                                )
                                        ) {

                                            serial_exists =
                                                true;
                                        }
                                    }
                                );

                                if (serial_exists) {

                                    frappe.msgprint(
                                        `Serial ${serial} already exists in the Items table.`
                                    );

                                    dialog.set_value(
                                        "serial_no",
                                        ""
                                    );

                                    dialog.fields_dict
                                        .serial_no
                                        .$input
                                        .focus();

                                    return;
                                }

                                let table =
                                    dialog.fields_dict
                                        .items_table
                                        .grid;

                                let rows =
                                    table.get_data();

                                let index =
                                    rows.findIndex(
                                        d =>
                                            d.delivery_note ===
                                                r.message.delivery_note &&
                                            d.item_code ===
                                                r.message.item_code
                                    );

                                if (index !== -1) {

                                    let existing =
                                        rows[index];

                                    if (
                                        existing.serial_nos &&
                                        existing.serial_nos
                                            .split("\n")
                                            .includes(
                                                serial
                                            )
                                    ) {

                                        frappe.msgprint(
                                            `Serial ${serial} already scanned`
                                        );

                                    } else {

                                        existing.return_qty =
                                            flt(
                                                existing.return_qty ||
                                                0
                                            ) + 1;

                                        existing.serial_nos =
                                            existing.serial_nos
                                                ? existing.serial_nos +
                                                  "\n" +
                                                  serial
                                                : serial;

                                        rows.splice(
                                            index,
                                            1
                                        );

                                        rows.unshift(
                                            existing
                                        );
                                    }

                                } else {

                                    r.message.return_qty =
                                        1;

                                    r.message.serial_nos =
                                        serial;

                                    rows.unshift(
                                        r.message
                                    );
                                }

                                table.refresh();

                                frappe.after_ajax(
                                    () => {

                                        setTimeout(
                                            () => {

                                                let grid =
                                                    dialog.fields_dict
                                                        .items_table
                                                        .grid;

                                                if (
                                                    grid.grid_rows
                                                        .length
                                                ) {

                                                    let row =
                                                        grid.grid_rows[0];

                                                    let checkbox =
                                                        row.wrapper
                                                            .find(
                                                                ".grid-row-check"
                                                            );

                                                    if (
                                                        !checkbox.prop(
                                                            "checked"
                                                        )
                                                    ) {

                                                        checkbox.click();
                                                    }
                                                }

                                            },
                                            200
                                        );
                                    }
                                );

                                dialog.set_value(
                                    "serial_no",
                                    ""
                                );

                                dialog.fields_dict
                                    .serial_no
                                    .$input
                                    .focus();
                            }
                        });
                    }
                },

                // -------------------------------------------------
                // ITEMS
                // -------------------------------------------------

                {
                    fieldname: "items_table",
                    fieldtype: "Table",
                    label: "Items",
                    cannot_add_rows: true,
                    in_place_edit: true,

                    fields: [

                        {
                            fieldname:
                                "delivery_note",

                            label:
                                "Delivery Note",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1
                        },

                        {
                            fieldname:
                                "item_code",

                            label:
                                "Item",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1
                        },

                        {
                            fieldname:
                                "returnable_qty",

                            label:
                                "Returnable Qty",

                            fieldtype:
                                "Float",

                            read_only:
                                1,

                            in_list_view:
                                1
                        },

                        {
                            fieldname:
                                "returned_qty",

                            label:
                                "Already Returned",

                            fieldtype:
                                "Float",

                            read_only:
                                1,

                            in_list_view:
                                1
                        },

                        {
                            fieldname:
                                "return_qty",

                            label:
                                "Return Qty",

                            fieldtype:
                                "Float",

                            in_list_view:
                                1,

                            onchange() {

                                let grid =
                                    dialog.fields_dict
                                        .items_table
                                        .grid;

                                let row =
                                    grid.get_row(
                                        this.doc.name
                                    );

                                let d =
                                    row.doc;

                                if (
                                    d.has_serial_no ==
                                    1
                                ) {

                                    let serial_count =
                                        d.serial_nos
                                            ? d.serial_nos
                                                .split("\n")
                                                .filter(
                                                    s =>
                                                        s.trim()
                                                )
                                                .length
                                            : 0;

                                    if (
                                        serial_count ===
                                        0
                                    ) {

                                        frappe.msgprint(
                                            __(
                                                "Scan Serial Numbers first for serialized item {0}.",
                                                [
                                                    d.item_code
                                                ]
                                            )
                                        );

                                        d.return_qty =
                                            0;

                                        grid.refresh();

                                        return;
                                    }

                                    d.return_qty =
                                        serial_count;

                                    grid.refresh();

                                    return;
                                }

                                if (
                                    flt(
                                        d.return_qty
                                    ) >
                                    flt(
                                        d.returnable_qty
                                    )
                                ) {

                                    frappe.msgprint(
                                        __(
                                            "Return Qty cannot exceed Returnable Qty for Item {0}",
                                            [
                                                d.item_code
                                            ]
                                        )
                                    );

                                    d.return_qty =
                                        d.returnable_qty;

                                    grid.refresh();
                                }
                            }
                        },

                        {
                            fieldname:
                                "serial_nos",

                            label:
                                "Serial Nos",

                            fieldtype:
                                "Small Text",

                            read_only:
                                1,

                            in_list_view:
                                1
                        }
                    ]
                }
            ],

            primary_action_label:
                "Add Selected Items",

            primary_action() {

                let selected_rows =
                    dialog.fields_dict
                        .items_table
                        .grid
                        .get_selected_children();

                if (!selected_rows.length) {

                    frappe.msgprint(
                        "Please select rows"
                    );

                    return;
                }

                for (
                    let r of selected_rows
                ) {

                    if (
                        !r.return_qty ||
                        r.return_qty <= 0
                    ) {

                        frappe.throw(
                            `Please enter Return Qty for Item ${r.item_code} in Delivery Note ${r.delivery_note}`
                        );
                    }

                    if (
                        r.return_qty >
                        r.returnable_qty
                    ) {

                        frappe.throw(
                            `Return Qty cannot exceed Returnable Qty for Item ${r.item_code} in Delivery Note ${r.delivery_note}`
                        );
                    }
                }

                // -------------------------------------------------
                // MERGE
                // -------------------------------------------------

                let merged_rows = {};

                selected_rows.forEach(
                    d => {

                        let key =
                            d.delivery_note_item;

                        if (
                            !merged_rows[key]
                        ) {

                            merged_rows[key] = {
                                ...d
                            };

                        } else {

                            merged_rows[key]
                                .return_qty =
                                flt(
                                    merged_rows[key]
                                        .return_qty
                                ) +
                                flt(
                                    d.return_qty
                                );

                            if (
                                d.serial_nos
                            ) {

                                merged_rows[key]
                                    .serial_nos =
                                    (
                                        merged_rows[key]
                                            .serial_nos ||
                                        ""
                                    ) +
                                    "\n" +
                                    d.serial_nos;
                            }
                        }
                    }
                );

                selected_rows =
                    Object.values(
                        merged_rows
                    );

                frappe.call({

                    method:
                        "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_dn_item_details",

                    args: {
                        items:
                            selected_rows
                    },

                    callback:
                        function(r) {

                            if (!r.message) {
                                return;
                            }

                            try {

                                r.message.forEach(
                                    d => {

                                        let existing =
                                            frm.doc.items.find(
                                                row =>
                                                    row.delivery_note_item ===
                                                        d.name &&
                                                    row.warehouse ===
                                                        d.warehouse
                                            );

                                        if (existing) {

                                            let new_qty =
                                                flt(
                                                    existing.qty
                                                ) +
                                                flt(
                                                    d.qty
                                                );

                                            if (
                                                new_qty >
                                                flt(
                                                    existing
                                                        .returnable_quantity
                                                )
                                            ) {

                                                frappe.throw(
                                                    __(
                                                        "Return Qty exceeded for Item {0}. Allowed Qty: {1}",
                                                        [
                                                            existing.item_code,
                                                            existing.returnable_quantity
                                                        ]
                                                    )
                                                );

                                                return;
                                            }

                                            frappe.model.set_value(
                                                existing.doctype,
                                                existing.name,
                                                "qty",
                                                new_qty
                                            );

                                            if (
                                                d.serial_nos
                                            ) {

                                                let existing_serials =
                                                    existing.serial_nos
                                                        ? existing.serial_nos
                                                            .split("\n")
                                                        : [];

                                                let new_serials =
                                                    d.serial_nos
                                                        ? d.serial_nos
                                                            .split("\n")
                                                        : [];

                                                let merged = [
                                                    ...new Set([
                                                        ...existing_serials,
                                                        ...new_serials
                                                    ])
                                                ];

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

                                        } else {

                                            let row =
                                                frm.add_child(
                                                    "items"
                                                );

                                            row.delivery_note =
                                                d.delivery_note;

                                            row.delivery_note_item =
                                                d.name;

                                            row.item_code =
                                                d.item_code;

                                            row.item_name =
                                                d.item_name;

                                            row.qty =
                                                d.qty;

                                            row.uom =
                                                d.uom;

                                            row.stock_uom =
                                                d.stock_uom;

                                            row.conversion_factor =
                                                d.conversion_factor;

                                            row.rate =
                                                d.rate;

                                            row.warehouse =
                                                d.warehouse;

                                            row.returnable_quantity =
                                                d.returnable_quantity;

                                            frappe.model.set_value(
                                                row.doctype,
                                                row.name,
                                                "serial_nos",
                                                d.serial_nos
                                            );

                                            frappe.model.set_value(
                                                row.doctype,
                                                row.name,
                                                "available_serial_nos",
                                                d.available_serial_nos
                                            );
                                        }
                                    }
                                );

                            } catch (e) {

                                console.error(
                                    "Error adding items:",
                                    e
                                );
                            }

                            frm.refresh_field(
                                "items"
                            );

                            dialog.hide();
                        }
                });
            }
        });

    dialog.show();

    dialog.$wrapper.on(
        "keydown",
        function(e) {

            if (e.key === "Enter") {

                e.preventDefault();
                e.stopPropagation();

                return false;
            }
        }
    );

    load_returnable_items(
        frm,
        dialog
    );
}


// =============================================================
// LOAD DELIVERY NOTE ITEMS
// =============================================================

function load_returnable_items(
    frm,
    dialog
) {

    let customer =
        dialog.get_value(
            "customer"
        );

    let item_code =
        dialog.get_value(
            "item_code"
        );

    if (!customer) {
        return;
    }

    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_returnable_items",

        args: {

            customer:
                customer,

            item_code:
                item_code,

            company:
                frm.doc.company
        },

        callback: function(r) {

            if (!r.message) {
                return;
            }

            dialog.fields_dict
                .items_table
                .df
                .data =
                r.message;

            dialog.fields_dict
                .items_table
                .grid
                .refresh();
        }
    });
}


// =============================================================
// COMMON SI / DN SCAN DIALOG
// =============================================================

function open_si_dn_dialog(frm) {

    let selected_rows = {};

    let dialog =
        new frappe.ui.Dialog({

            title:
                "Return Items from Sales Invoice / Delivery Note",

            size:
                "extra-large",

            fields: [

                // -------------------------------------------------
                // CUSTOMER
                // -------------------------------------------------

                {
                    fieldname: "customer",
                    label: "Customer",
                    fieldtype: "Link",
                    options: "Customer",
                    default: frm.doc.customer,
                    read_only: 1,
                    reqd: 1
                },

                // -------------------------------------------------
                // ITEM
                // -------------------------------------------------

                {
                    fieldname: "item_code",
                    label: "Item",
                    fieldtype: "Link",
                    options: "Item",

                    onchange() {

                        load_common_si_dn_items(
                            frm,
                            dialog,
                            selected_rows
                        );
                    }
                },

                // -------------------------------------------------
                // SERIAL SCAN
                // -------------------------------------------------

                {
                    fieldname: "serial_no",
                    label: "Scan Serial",
                    fieldtype: "Data",
                    options: "Barcode",

                    onchange() {

                        let serial =
                            (
                                dialog.get_value(
                                    "serial_no"
                                ) || ""
                            ).trim();

                        if (!serial) {
                            return;
                        }

                        frappe.call({

                            method:
                                "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_return_source_from_serial",

                            args: {

                                serial_no:
                                    serial,

                                company:
                                    frm.doc.company,

                                customer:
                                    dialog.get_value(
                                        "customer"
                                    )
                            },

                            freeze: true,

                            freeze_message:
                                "Finding return source...",

                            callback:
                                function(r) {

                                    // -----------------------------------------
                                    // NOT FOUND
                                    // -----------------------------------------

                                    if (!r.message) {

                                        frappe.msgprint(
                                            `Serial ${serial} was not found in any submitted Sales Invoice or Delivery Note.`
                                        );

                                        dialog.set_value(
                                            "serial_no",
                                            ""
                                        );

                                        setTimeout(
                                            () => {

                                                dialog.fields_dict
                                                    .serial_no
                                                    .$input
                                                    .focus();

                                            },
                                            100
                                        );

                                        return;
                                    }

                                    let d =
                                        r.message;

                                    // -----------------------------------------
                                    // DUPLICATE SERIAL
                                    // -----------------------------------------

                                    let serial_exists =
                                        false;

                                    (
                                        frm.doc.items ||
                                        []
                                    ).forEach(
                                        row => {

                                            if (
                                                row.serial_nos &&
                                                row.serial_nos
                                                    .split("\n")
                                                    .map(
                                                        s =>
                                                            s.trim()
                                                    )
                                                    .includes(
                                                        serial
                                                    )
                                            ) {

                                                serial_exists =
                                                    true;
                                            }
                                        }
                                    );

                                    if (
                                        serial_exists
                                    ) {

                                        frappe.msgprint(
                                            `Serial ${serial} already exists in the Items table.`
                                        );

                                        dialog.set_value(
                                            "serial_no",
                                            ""
                                        );

                                        setTimeout(
                                            () => {

                                                dialog.fields_dict
                                                    .serial_no
                                                    .$input
                                                    .focus();

                                            },
                                            100
                                        );

                                        return;
                                    }

                                    // -----------------------------------------
                                    // GRID DATA
                                    // -----------------------------------------

                                    let grid =
                                        dialog.fields_dict
                                            .items_table
                                            .grid;

                                    let rows =
                                        dialog.fields_dict
                                            .items_table
                                            .df
                                            .data || [];

                                    // -----------------------------------------
                                    // UNIQUE KEY
                                    // -----------------------------------------

                                    let common_key;

                                    if (
                                        d.source_type ===
                                        "Sales Invoice"
                                    ) {

                                        common_key =
                                            `SI::${d.sales_invoice_item}`;

                                    } else {

                                        common_key =
                                            `DN::${d.delivery_note_item}`;
                                    }

                                    d._common_key =
                                        common_key;

                                    // -----------------------------------------
                                    // FIND EXISTING ROW
                                    // -----------------------------------------

                                    let index =
                                        rows.findIndex(
                                            row =>
                                                row._common_key ===
                                                common_key
                                        );

                                    // -----------------------------------------
                                    // EXISTING ROW
                                    // -----------------------------------------

                                    if (
                                        index !== -1
                                    ) {

                                        let existing =
                                            rows[index];

                                        let existing_serials =
                                            existing.serial_nos
                                                ? existing.serial_nos
                                                    .split("\n")
                                                    .map(
                                                        s =>
                                                            s.trim()
                                                    )
                                                    .filter(
                                                        Boolean
                                                    )
                                                : [];

                                        if (
                                            existing_serials
                                                .includes(
                                                    serial
                                                )
                                        ) {

                                            frappe.msgprint(
                                                `Serial ${serial} already scanned.`
                                            );

                                        } else {

                                            existing_serials.push(
                                                serial
                                            );

                                            existing.serial_nos =
                                                existing_serials
                                                    .join("\n");

                                            existing.return_qty =
                                                existing_serials.length;

                                            selected_rows[
                                                common_key
                                            ] = true;

                                            // ---------------------------------
                                            // IMPORTANT:
                                            // Preserve DN information if
                                            // returned by backend.
                                            // ---------------------------------

                                            if (
                                                d.delivery_note
                                            ) {

                                                existing.delivery_note =
                                                    d.delivery_note;
                                            }

                                            if (
                                                d.delivery_note_item
                                            ) {

                                                existing.delivery_note_item =
                                                    d.delivery_note_item;
                                            }

                                            // Move to top
                                            rows.splice(
                                                index,
                                                1
                                            );

                                            rows.unshift(
                                                existing
                                            );
                                        }

                                    }

                                    // -----------------------------------------
                                    // NEW ROW
                                    // -----------------------------------------

                                    else {

                                        d.return_qty =
                                            1;

                                        d.serial_nos =
                                            serial;

                                        selected_rows[
                                            common_key
                                        ] = true;

                                        rows.unshift(
                                            d
                                        );
                                    }

                                    // -----------------------------------------
                                    // SET DATA
                                    // -----------------------------------------

                                    dialog.fields_dict
                                        .items_table
                                        .df
                                        .data =
                                        rows;

                                    grid.refresh();

                                    // -----------------------------------------
                                    // SELECT CHECKBOX
                                    // -----------------------------------------

                                    frappe.after_ajax(
                                        () => {

                                            setTimeout(
                                                () => {

                                                    let grid_rows =
                                                        dialog.fields_dict
                                                            .items_table
                                                            .grid
                                                            .grid_rows;

                                                    grid_rows.forEach(
                                                        gr => {

                                                            let row =
                                                                gr.doc;

                                                            let key =
                                                                row._common_key;

                                                            let checkbox =
                                                                gr.wrapper
                                                                    .find(
                                                                        ".grid-row-check"
                                                                    );

                                                            let should_check =
                                                                !!selected_rows[
                                                                    key
                                                                ];

                                                            if (
                                                                should_check &&
                                                                !checkbox.prop(
                                                                    "checked"
                                                                )
                                                            ) {

                                                                checkbox.click();
                                                            }

                                                            else if (
                                                                !should_check &&
                                                                checkbox.prop(
                                                                    "checked"
                                                                )
                                                            ) {

                                                                checkbox.click();
                                                            }
                                                        }
                                                    );

                                                    update_common_scan_total(
                                                        dialog,
                                                        selected_rows
                                                    );

                                                },
                                                150
                                            );
                                        }
                                    );

                                    // -----------------------------------------
                                    // CLEAR SCAN
                                    // -----------------------------------------

                                    dialog.set_value(
                                        "serial_no",
                                        ""
                                    );

                                    setTimeout(
                                        () => {

                                            dialog.fields_dict
                                                .serial_no
                                                .$input
                                                .focus();

                                        },
                                        200
                                    );
                                }
                        });
                    }
                },

                // -------------------------------------------------
                // TOTAL
                // -------------------------------------------------

                {
                    fieldname:
                        "total_quantity",

                    label:
                        "Total Quantity",

                    fieldtype:
                        "Float",

                    read_only:
                        1,

                    default:
                        0
                },

                // -------------------------------------------------
                // ITEMS TABLE
                // -------------------------------------------------

                {
                    fieldname:
                        "items_table",

                    fieldtype:
                        "Table",

                    label:
                        "Items",

                    cannot_add_rows:
                        true,

                    in_place_edit:
                        true,

                    fields: [

                        {
                            fieldname:
                                "source_type",

                            label:
                                "Source",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                1
                        },

                        {
                            fieldname:
                                "sales_invoice",

                            label:
                                "Sales Invoice",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                2
                        },

                        {
                            fieldname:
                                "delivery_note",

                            label:
                                "Delivery Note",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                2
                        },

                        {
                            fieldname:
                                "item_code",

                            label:
                                "Item",

                            fieldtype:
                                "Data",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                2
                        },

                        {
                            fieldname:
                                "returnable_qty",

                            label:
                                "Returnable",

                            fieldtype:
                                "Float",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                1
                        },

                        {
                            fieldname:
                                "returned_qty",

                            label:
                                "Returned",

                            fieldtype:
                                "Float",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                1
                        },

                        {
                            fieldname:
                                "return_qty",

                            label:
                                "Return Qty",

                            fieldtype:
                                "Float",

                            in_list_view:
                                1,

                            columns:
                                1,

                            onchange() {

                                let d =
                                    this.doc;

                                if (!d) {
                                    return;
                                }

                                // -----------------------------------------
                                // SERIALIZED
                                // -----------------------------------------

                                if (
                                    d.has_serial_no
                                ) {

                                    let serial_count =
                                        (
                                            d.serial_nos ||
                                            ""
                                        )
                                        .split("\n")
                                        .map(
                                            s =>
                                                s.trim()
                                        )
                                        .filter(
                                            Boolean
                                        )
                                        .length;

                                    d.return_qty =
                                        serial_count;
                                }

                                // -----------------------------------------
                                // QTY VALIDATION
                                // -----------------------------------------

                                if (
                                    flt(
                                        d.return_qty
                                    ) >
                                    flt(
                                        d.returnable_qty
                                    )
                                ) {

                                    d.return_qty =
                                        d.returnable_qty;

                                    frappe.msgprint(
                                        __(
                                            "Return Qty cannot exceed Returnable Qty for Item {0}",
                                            [
                                                d.item_code
                                            ]
                                        )
                                    );
                                }

                                update_common_scan_total(
                                    dialog,
                                    selected_rows
                                );
                            }
                        },

                        {
                            fieldname:
                                "serial_nos",

                            label:
                                "Serial Nos",

                            fieldtype:
                                "Small Text",

                            read_only:
                                1,

                            in_list_view:
                                1,

                            columns:
                                2
                        }
                    ]
                }
            ],

            primary_action_label:
                "Add Selected Items",

            primary_action() {

                let all_rows =
                    dialog.fields_dict
                        .items_table
                        .df
                        .data || [];

                let selected =
                    all_rows.filter(
                        row => {

                            let key =
                                row._common_key ||
                                (
                                    row.source_type ===
                                    "Sales Invoice"

                                        ? `SI::${row.sales_invoice_item}`

                                        : `DN::${row.delivery_note_item}`
                                );

                            return !!selected_rows[
                                key
                            ];
                        }
                    );

                if (!selected.length) {

                    frappe.msgprint(
                        "Please select rows."
                    );

                    return;
                }

                // ---------------------------------------------------------
                // VALIDATE
                // ---------------------------------------------------------

                for (
                    let d of selected
                ) {

                    if (
                        !d.return_qty ||
                        flt(d.return_qty) <= 0
                    ) {

                        frappe.throw(
                            `Return Qty must be greater than 0 for Item ${d.item_code}`
                        );
                    }

                    if (
                        flt(d.return_qty) >
                        flt(d.returnable_qty)
                    ) {

                        frappe.throw(
                            `Return Qty cannot exceed Returnable Qty for Item ${d.item_code}`
                        );
                    }

                    if (
                        d.has_serial_no
                    ) {

                        let serials =
                            (
                                d.serial_nos ||
                                ""
                            )
                            .split("\n")
                            .map(
                                s =>
                                    s.trim()
                            )
                            .filter(
                                Boolean
                            );

                        if (
                            !serials.length
                        ) {

                            frappe.throw(
                                `Please scan Serial Number for Item ${d.item_code}`
                            );
                        }

                        if (
                            serials.length !==
                            flt(d.return_qty)
                        ) {

                            frappe.throw(
                                `Serial count must match Return Qty for Item ${d.item_code}`
                            );
                        }
                    }
                }

                // ---------------------------------------------------------
                // ADD ITEMS TO MAIN FORM
                // ---------------------------------------------------------

                selected.forEach(
                    d => {

                        // =================================================
                        // SALES INVOICE SOURCE
                        // =================================================

                        if (
                            d.source_type ===
                            "Sales Invoice"
                        ) {

                            let existing =
                                frm.doc.items.find(
                                    row =>
                                        row.sales_invoice_item ===
                                        d.sales_invoice_item
                                );

                            if (existing) {

                                let new_qty =
                                    flt(
                                        existing.qty
                                    ) +
                                    flt(
                                        d.return_qty
                                    );

                                if (
                                    new_qty >
                                    flt(
                                        existing.returnable_quantity
                                    )
                                ) {

                                    frappe.throw(
                                        __(
                                            "Return Qty exceeded for Item {0}. Allowed Qty: {1}",
                                            [
                                                existing.item_code,
                                                existing.returnable_quantity
                                            ]
                                        )
                                    );
                                }

                                frappe.model.set_value(
                                    existing.doctype,
                                    existing.name,
                                    "qty",
                                    new_qty
                                );

                                // -----------------------------------------
                                // IMPORTANT:
                                // If SI item has DN reference,
                                // preserve it in existing row.
                                // -----------------------------------------

                                if (
                                    d.delivery_note
                                ) {

                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "delivery_note",
                                        d.delivery_note
                                    );
                                }

                                if (
                                    d.delivery_note_item
                                ) {

                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "delivery_note_item",
                                        d.delivery_note_item
                                    );
                                }

                                // -----------------------------------------
                                // SERIALS
                                // -----------------------------------------

                                if (
                                    d.serial_nos
                                ) {

                                    let old_serials =
                                        existing.serial_nos
                                            ? existing.serial_nos
                                                .split("\n")
                                                .filter(
                                                    Boolean
                                                )
                                            : [];

                                    let new_serials =
                                        d.serial_nos
                                            .split("\n")
                                            .filter(
                                                Boolean
                                            );

                                    let merged = [
                                        ...new Set([
                                            ...old_serials,
                                            ...new_serials
                                        ])
                                    ];

                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "serial_nos",
                                        merged.join("\n")
                                    );
                                }

                            } else {

                                let row =
                                    frm.add_child(
                                        "items"
                                    );

                                row.item_code =
                                    d.item_code;

                                row.item_name =
                                    d.item_name;

                                row.qty =
                                    d.return_qty;

                                row.rate =
                                    d.rate;

                                row.sales_invoice =
                                    d.sales_invoice;

                                row.sales_invoice_item =
                                    d.sales_invoice_item;

                                row.warehouse =
                                    d.warehouse;

                                row.returnable_quantity =
                                    d.returnable_qty;

                                // -----------------------------------------
                                // IMPORTANT:
                                // SI -> DN relation
                                // -----------------------------------------

                                if (
                                    d.delivery_note
                                ) {

                                    row.delivery_note =
                                        d.delivery_note;
                                }

                                if (
                                    d.delivery_note_item
                                ) {

                                    row.delivery_note_item =
                                        d.delivery_note_item;
                                }

                                if (
                                    d.serial_nos
                                ) {

                                    frappe.model.set_value(
                                        row.doctype,
                                        row.name,
                                        "serial_nos",
                                        d.serial_nos
                                    );
                                }
                            }
                        }

                        // =================================================
                        // DELIVERY NOTE SOURCE
                        // =================================================

                        else if (
                            d.source_type ===
                            "Delivery Note"
                        ) {

                            let existing =
                                frm.doc.items.find(
                                    row =>
                                        row.delivery_note_item ===
                                            d.delivery_note_item &&
                                        row.warehouse ===
                                            d.warehouse
                                );

                            if (existing) {

                                let new_qty =
                                    flt(
                                        existing.qty
                                    ) +
                                    flt(
                                        d.return_qty
                                    );

                                if (
                                    new_qty >
                                    flt(
                                        existing.returnable_quantity
                                    )
                                ) {

                                    frappe.throw(
                                        __(
                                            "Return Qty exceeded for Item {0}. Allowed Qty: {1}",
                                            [
                                                existing.item_code,
                                                existing.returnable_quantity
                                            ]
                                        )
                                    );
                                }

                                frappe.model.set_value(
                                    existing.doctype,
                                    existing.name,
                                    "qty",
                                    new_qty
                                );

                                if (
                                    d.serial_nos
                                ) {

                                    let old_serials =
                                        existing.serial_nos
                                            ? existing.serial_nos
                                                .split("\n")
                                                .filter(
                                                    Boolean
                                                )
                                            : [];

                                    let new_serials =
                                        d.serial_nos
                                            .split("\n")
                                            .filter(
                                                Boolean
                                            );

                                    let merged = [
                                        ...new Set([
                                            ...old_serials,
                                            ...new_serials
                                        ])
                                    ];

                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "serial_nos",
                                        merged.join("\n")
                                    );
                                }

                            } else {

                                let row =
                                    frm.add_child(
                                        "items"
                                    );

                                row.delivery_note =
                                    d.delivery_note;

                                row.delivery_note_item =
                                    d.delivery_note_item;

                                row.item_code =
                                    d.item_code;

                                row.item_name =
                                    d.item_name;

                                row.qty =
                                    d.return_qty;

                                row.uom =
                                    d.uom;

                                row.stock_uom =
                                    d.stock_uom;

                                row.conversion_factor =
                                    d.conversion_factor;

                                row.rate =
                                    d.rate;

                                row.warehouse =
                                    d.warehouse;

                                row.returnable_quantity =
                                    d.returnable_qty;

                                if (
                                    d.serial_nos
                                ) {

                                    frappe.model.set_value(
                                        row.doctype,
                                        row.name,
                                        "serial_nos",
                                        d.serial_nos
                                    );
                                }
                            }
                        }
                    }
                );

                frm.refresh_field(
                    "items"
                );

                setTimeout(
                    () => {

                        update_total_quantity(
                            frm
                        );

                    },
                    50
                );

                dialog.hide();
            }
        });

    // =============================================================
    // SHOW
    // =============================================================

    dialog.show();

    // =============================================================
    // CHECKBOX CHANGE
    // =============================================================

    dialog.$wrapper.on(
        "change",
        ".grid-row-check",
        function() {

            let grid =
                dialog.fields_dict
                    .items_table
                    .grid;

            grid.grid_rows.forEach(
                gr => {

                    let row =
                        gr.doc;

                    let key =
                        row._common_key ||
                        (
                            row.source_type ===
                            "Sales Invoice"

                                ? `SI::${row.sales_invoice_item}`

                                : `DN::${row.delivery_note_item}`
                        );

                    let checked =
                        gr.wrapper
                            .find(
                                ".grid-row-check"
                            )
                            .prop(
                                "checked"
                            );

                    if (checked) {

                        selected_rows[
                            key
                        ] = true;

                    } else {

                        delete selected_rows[
                            key
                        ];
                    }
                }
            );

            update_common_scan_total(
                dialog,
                selected_rows
            );
        }
    );

    // =============================================================
    // DISABLE ENTER
    // =============================================================

    dialog.$wrapper.on(
        "keydown",
        function(e) {

            if (e.key === "Enter") {

                e.preventDefault();
                e.stopPropagation();

                return false;
            }
        }
    );

    // =============================================================
    // FOCUS SCAN
    // =============================================================

    setTimeout(
        () => {

            if (
                dialog.fields_dict.serial_no &&
                dialog.fields_dict.serial_no.$input
            ) {

                dialog.fields_dict
                    .serial_no
                    .$input
                    .focus();
            }

        },
        300
    );
}


// =============================================================
// LOAD COMMON SI/DN ITEMS
// =============================================================

function load_common_si_dn_items(
    frm,
    dialog,
    selected_rows
) {

    let customer =
        dialog.get_value(
            "customer"
        );

    let item_code =
        dialog.get_value(
            "item_code"
        );

    if (!customer) {
        return;
    }

    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.get_sales_invoice_returnable_items",

        args: {

            customer:
                customer,

            item_code:
                item_code,

            company:
                frm.doc.company
        },

        callback(r) {

            if (!r.message) {
                return;
            }

            let old_rows =
                dialog.fields_dict
                    .items_table
                    .df
                    .data || [];

            let new_rows =
                r.message || [];

            let row_map = {};

            // ---------------------------------------------------------
            // PRESERVE SCANNED ROWS
            // ---------------------------------------------------------

            old_rows.forEach(
                row => {

                    if (
                        row._common_key
                    ) {

                        row_map[
                            row._common_key
                        ] = row;
                    }
                }
            );

            // ---------------------------------------------------------
            // ADD SI ROWS
            // ---------------------------------------------------------

            new_rows.forEach(
                row => {

                    row.source_type =
                        "Sales Invoice";

                    row._common_key =
                        `SI::${row.sales_invoice_item}`;

                    if (
                        row_map[
                            row._common_key
                        ]
                    ) {

                        row.return_qty =
                            row_map[
                                row._common_key
                            ].return_qty;

                        row.serial_nos =
                            row_map[
                                row._common_key
                            ].serial_nos;

                        // ---------------------------------------------
                        // IMPORTANT:
                        // Preserve DN reference of scanned row.
                        // ---------------------------------------------

                        if (
                            row_map[
                                row._common_key
                            ].delivery_note
                        ) {

                            row.delivery_note =
                                row_map[
                                    row._common_key
                                ].delivery_note;
                        }

                        if (
                            row_map[
                                row._common_key
                            ].delivery_note_item
                        ) {

                            row.delivery_note_item =
                                row_map[
                                    row._common_key
                                ].delivery_note_item;
                        }
                    }

                    row_map[
                        row._common_key
                    ] = row;
                }
            );

            dialog.fields_dict
                .items_table
                .df
                .data =
                Object.values(
                    row_map
                );

            let grid =
                dialog.fields_dict
                    .items_table
                    .grid;

            grid.refresh();

            frappe.after_ajax(
                () => {

                    setTimeout(
                        () => {

                            grid.grid_rows.forEach(
                                gr => {

                                    let key =
                                        gr.doc
                                            ._common_key;

                                    let checkbox =
                                        gr.wrapper
                                            .find(
                                                ".grid-row-check"
                                            );

                                    let should_check =
                                        !!selected_rows[
                                            key
                                        ];

                                    if (
                                        should_check &&
                                        !checkbox.prop(
                                            "checked"
                                        )
                                    ) {

                                        checkbox.click();
                                    }

                                    else if (
                                        !should_check &&
                                        checkbox.prop(
                                            "checked"
                                        )
                                    ) {

                                        checkbox.click();
                                    }
                                }
                            );

                            update_common_scan_total(
                                dialog,
                                selected_rows
                            );

                        },
                        100
                    );
                }
            );
        }
    });
}


// =============================================================
// COMMON SI/DN TOTAL
// =============================================================

function update_common_scan_total(
    dialog,
    selected_rows
) {

    let total = 0;

    (
        dialog.fields_dict
            .items_table
            .df
            .data || []
    ).forEach(
        row => {

            let key =
                row._common_key ||
                (
                    row.source_type ===
                    "Sales Invoice"

                        ? `SI::${row.sales_invoice_item}`

                        : `DN::${row.delivery_note_item}`
                );

            if (
                selected_rows[key]
            ) {

                total +=
                    flt(
                        row.return_qty || 0
                    );
            }
        }
    );

    dialog.set_value(
        "total_quantity",
        total
    );
}