frappe.ui.form.on("Bulk Purchase Return", {

    refresh(frm) {

        // Draft document
        if (frm.doc.docstatus === 0) {

            frm.add_custom_button("Get Items from GRN", () => {
                open_return_items_dialog(frm);
            });

            update_total_quantity(frm);
        }


        // Submitted document → Submit Return PR button
        if (frm.doc.docstatus === 1) {

            frappe.call({
                method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.has_draft_return_prs",

                args: {
                    docname: frm.doc.name
                },

                callback: function(r) {

                    if (r.message) {

                        frm.add_custom_button(
                            "Submit Return PRs",

                            async function() {

                                await frappe.call({

                                    method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.submit_created_prs",

                                    args: {
                                        docname: frm.doc.name
                                    },

                                    freeze: true,

                                    freeze_message: "Submitting Return Purchase Receipt..."
                                });


                                frappe.msgprint(
                                    "Return Purchase Receipt submission started."
                                );

                                frm.reload_doc();
                            }
                        );
                    }
                }
            });
        }
    },


    // Child table row added
    items_add(frm) {
        update_total_quantity(frm);
    },


    // Child table row removed
    items_remove(frm) {
        update_total_quantity(frm);
    }
});



/* =========================================================
   CHILD TABLE EVENTS
========================================================= */

frappe.ui.form.on("Bulk Purchase Return Item Table", {

    qty(frm) {
        update_total_quantity(frm);
    }
});



/* =========================================================
   MAIN FORM TOTAL QUANTITY
========================================================= */

function update_total_quantity(frm) {

    let total = 0;

    (frm.doc.items || []).forEach(row => {

        total += flt(row.qty || 0);

    });


    frm.set_value("total_quantity", total);

    frm.refresh_field("total_quantity");
}



/* =========================================================
   POPUP TOTAL QUANTITY
   ONLY SELECTED ROWS
========================================================= */

function update_popup_total_quantity(dialog) {

    let total = 0;


    let selected_rows =
        dialog.fields_dict.items_table.grid.get_selected_children();


    selected_rows.forEach(row => {

        total += flt(row.return_qty || 0);

    });


    dialog.set_value("total_quantity", total);
}



/* =========================================================
   OPEN GRN RETURN ITEMS DIALOG
========================================================= */

function open_return_items_dialog(frm) {

    let dialog = new frappe.ui.Dialog({

        title: "Return Items from GRN",

        size: "extra-large",


        fields: [

            /* =========================
               SUPPLIER
            ========================= */

            {
                fieldname: "supplier",

                label: "Supplier",

                fieldtype: "Link",

                options: "Supplier",

                default: frm.doc.supplier,

                read_only: 1,

                reqd: 1,


                onchange() {

                    load_returnable_items(frm, dialog);
                }
            },


            /* =========================
               ITEM FILTER
            ========================= */

            {
                fieldname: "item_code",

                label: "Item",

                fieldtype: "Link",

                options: "Item",


                onchange() {

                    load_returnable_items(frm, dialog);
                }
            },


            /* =========================
               SERIAL SCAN
            ========================= */

            {
                fieldname: "serial_no",

                label: "Scan Serial",

                fieldtype: "Data",

                options: "Barcode",


                onchange() {

                    let serial =
                        dialog.get_value("serial_no");


                    if (!serial) return;


                    if (dialog.last_scanned === serial) {

                        dialog.set_value("serial_no", "");

                        return;
                    }


                    dialog.last_scanned = serial;


                    frappe.call({

                        method:
                            "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_pr_from_serial",


                        args: {

                            serial_no: serial,

                            company: frm.doc.company
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


                            /* SERIAL ALREADY DELIVERED */

                            if (r.message.status === "Delivered") {

                                frappe.msgprint(
                                    `Serial ${serial} is already Delivered and cannot be returned.`
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


                            /* CHECK EXISTING MAIN TABLE */

                            let serial_exists = false;


                            (frm.doc.items || []).forEach(row => {

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


                            /* POPUP TABLE */

                            let table =
                                dialog.fields_dict
                                    .items_table
                                    .grid;


                            let rows =
                                table.get_data();


                            let index =
                                rows.findIndex(d =>

                                    d.purchase_receipt ===
                                        r.message.purchase_receipt &&

                                    d.item_code ===
                                        r.message.item_code
                                );


                            /* EXISTING ROW */

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

                                }

                                else {

                                    existing.return_qty =
                                        flt(
                                            existing.return_qty || 0
                                        ) + 1;


                                    existing.serial_nos =
                                        existing.serial_nos

                                            ? existing.serial_nos +
                                                "\n" +
                                                serial

                                            : serial;


                                    rows.splice(index, 1);

                                    rows.unshift(existing);
                                }

                            }


                            /* NEW ROW */

                            else {

                                r.message.return_qty = 1;

                                r.message.serial_nos = serial;


                                rows.unshift(
                                    r.message
                                );
                            }


                            table.refresh();


                            /* AUTO SELECT FIRST ROW */

                            frappe.after_ajax(() => {

                                setTimeout(() => {

                                    let grid =
                                        dialog.fields_dict
                                            .items_table
                                            .grid;


                                    if (grid.grid_rows.length) {

                                        let row =
                                            grid.grid_rows[0];


                                        let checkbox =
                                            row.wrapper.find(
                                                ".grid-row-check"
                                            );


                                        if (
                                            !checkbox.prop("checked")
                                        ) {

                                            checkbox.click();
                                        }
                                    }


                                    update_popup_total_quantity(
                                        dialog
                                    );

                                }, 200);

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


            /* =========================
               POPUP TOTAL QUANTITY
            ========================= */

            {
                fieldname: "total_quantity",

                label: "Total Quantity",

                fieldtype: "Float",

                read_only: 1,

                default: 0
            },


            /* =========================
               ITEMS TABLE
            ========================= */

            {
                fieldname: "items_table",

                fieldtype: "Table",

                label: "Items",

                cannot_add_rows: true,

                in_place_edit: true,


                fields: [

                    {
                        fieldname: "purchase_receipt",

                        label: "GRN",

                        fieldtype: "Data",

                        read_only: 1,

                        in_list_view: 1
                    },


                    {
                        fieldname: "item_code",

                        label: "Item",

                        fieldtype: "Data",

                        read_only: 1,

                        in_list_view: 1
                    },


                    {
                        fieldname: "returnable_qty",

                        label: "Returnable Qty",

                        fieldtype: "Float",

                        read_only: 1,

                        in_list_view: 1
                    },


                    {
                        fieldname: "returned_qty",

                        label: "Already Returned",

                        fieldtype: "Float",

                        read_only: 1,

                        in_list_view: 1
                    },


                    /* RETURN QTY */

                    {
                        fieldname: "return_qty",

                        label: "Return Qty",

                        fieldtype: "Float",

                        in_list_view: 1,


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


                            /* SERIALIZED ITEM */

                            if (d.has_serial_no == 1) {

                                let serial_count = 0;


                                if (d.serial_nos) {

                                    serial_count =
                                        d.serial_nos
                                            .split("\n")
                                            .filter(
                                                s => s.trim()
                                            )
                                            .length;
                                }


                                if (serial_count === 0) {

                                    frappe.msgprint(
                                        __(
                                            "Scan Serial Numbers first for serialized item {0}.",
                                            [d.item_code]
                                        )
                                    );


                                    d.return_qty = 0;


                                    grid.refresh();


                                    update_popup_total_quantity(
                                        dialog
                                    );

                                    return;
                                }


                                d.return_qty =
                                    serial_count;


                                grid.refresh();


                                update_popup_total_quantity(
                                    dialog
                                );

                                return;
                            }


                            /* NON SERIALIZED ITEM */

                            if (

                                flt(d.return_qty) >

                                flt(d.returnable_qty)

                            ) {

                                frappe.msgprint(
                                    __(
                                        "Return Qty cannot exceed Returnable Qty for Item {0}",
                                        [d.item_code]
                                    )
                                );


                                d.return_qty =
                                    d.returnable_qty;


                                grid.refresh();
                            }


                            update_popup_total_quantity(
                                dialog
                            );
                        }
                    },


                    {
                        fieldname: "serial_nos",

                        label: "Serial Nos",

                        fieldtype: "Small Text",

                        read_only: 1,

                        in_list_view: 1
                    }
                ]
            }

        ],


        /* =================================================
           ADD SELECTED ITEMS
        ================================================= */

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


            /* VALIDATION */

            for (let r of selected_rows) {

                if (

                    !r.return_qty ||

                    r.return_qty <= 0

                ) {

                    frappe.throw(
                        `Please enter Return Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }


                if (

                    flt(r.return_qty) >

                    flt(r.returnable_qty)

                ) {

                    frappe.throw(
                        `Return Qty cannot exceed Returnable Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }
            }


            /* MERGE DUPLICATE ROWS */

            let merged_rows = {};


            selected_rows.forEach(d => {

                let key =
                    d.purchase_receipt_item;


                if (!merged_rows[key]) {

                    merged_rows[key] = {
                        ...d
                    };

                }

                else {

                    merged_rows[key].return_qty =

                        flt(
                            merged_rows[key].return_qty
                        )

                        +

                        flt(
                            d.return_qty
                        );


                    if (d.serial_nos) {

                        merged_rows[key].serial_nos =

                            (
                                merged_rows[key].serial_nos ||
                                ""
                            )

                            +

                            "\n"

                            +

                            d.serial_nos;
                    }
                }

            });


            selected_rows =
                Object.values(merged_rows);


            /* GET ITEM DETAILS */

            frappe.call({

                method:
                    "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_pr_item_details",


                args: {
                    items: selected_rows
                },


                callback: function(r) {


                    if (!r.message) return;


                    try {

                        r.message.forEach(d => {


                            let existing =

                                frm.doc.items.find(row =>

                                    row.purchase_receipt_item ===
                                        d.name &&

                                    row.warehouse ===
                                        d.warehouse
                                );


                            /* EXISTING ITEM */

                            if (existing) {


                                let new_qty =

                                    flt(existing.qty) +

                                    flt(d.qty);


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

                                    return;
                                }


                                frappe.model.set_value(

                                    existing.doctype,

                                    existing.name,

                                    "qty",

                                    new_qty
                                );


                                /* MERGE SERIALS */

                                if (d.serial_nos) {

                                    let existing_serials =

                                        existing.serial_nos

                                            ? existing.serial_nos.split(
                                                "\n"
                                            )

                                            : [];


                                    let new_serials =

                                        d.serial_nos

                                            ? d.serial_nos.split(
                                                "\n"
                                            )

                                            : [];


                                    let merged =

                                        [

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
                            }


                            /* NEW ITEM */

                            else {

                                let row =
                                    frm.add_child("items");


                                row.purchase_receipt =
                                    d.purchase_receipt;


                                row.purchase_receipt_item =
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

                        });


                    } catch (e) {

                        console.error(
                            "Error adding items:",
                            e
                        );
                    }


                    frm.refresh_field("items");


                    /* UPDATE MAIN TOTAL */

                    setTimeout(() => {

                        update_total_quantity(frm);

                    }, 50);


                    dialog.hide();

                }
            });
        }
    });


    dialog.show();


    /* =====================================================
       CHECKBOX CHANGE → UPDATE POPUP TOTAL
    ===================================================== */

    dialog.$wrapper.on(

        "change",

        ".grid-row-check",

        function() {

            setTimeout(() => {

                update_popup_total_quantity(
                    dialog
                );

            }, 50);

        }
    );


    /* =====================================================
       PREVENT ENTER KEY SUBMISSION
    ===================================================== */

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



/* =========================================================
   LOAD RETURNABLE ITEMS
========================================================= */

function load_returnable_items(frm, dialog) {

    let supplier =
        dialog.get_value("supplier");


    let item_code =
        dialog.get_value("item_code");


    if (!supplier) return;


    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_returnable_items",


        args: {

            supplier: supplier,

            item_code: item_code,

            company: frm.doc.company
        },


        callback: function(r) {


            if (!r.message) return;


            dialog.fields_dict
                .items_table
                .df
                .data = r.message;


            dialog.fields_dict
                .items_table
                .grid
                .refresh();


            update_popup_total_quantity(
                dialog
            );

        }
    });
}