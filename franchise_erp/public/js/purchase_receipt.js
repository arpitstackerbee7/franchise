// ===================================
// 🚀 GLOBAL CACHE
// ===================================
let barcode_cache = {};
let serial_cache = new Set();
let total_qty_cache = 0;


// ===================================
// 🚀 BUILD CACHE (SAFE)
// ===================================
function build_initial_cache(frm) {
    serial_cache.clear();
    total_qty_cache = 0; // 🔥 VERY IMPORTANT FIX

    (frm.doc.items || []).forEach(row => {
        total_qty_cache += flt(row.qty || 0);

        if (row.serial_no) {
            row.serial_no.split("\n").forEach(s => {
                if (s) serial_cache.add(s.trim());
            });
        }
    });
}


// ===================================
// 🚀 FAST TOTAL UPDATE
// ===================================
function update_total_qty_fast(frm, step) {
    total_qty_cache += step;

    // 🔥 SAFETY
    if (isNaN(total_qty_cache) || total_qty_cache < 0) {
        total_qty_cache = 0;
        (frm.doc.items || []).forEach(row => {
            total_qty_cache += flt(row.qty || 0);
        });
    }

    frm.doc.total_qty = total_qty_cache;
    frm.refresh_field("total_qty");
}


// ===================================
// 🚀 MAP GATE ENTRY
// ===================================
function map_gate_entry_to_purchase_receipt(frm, gate_entry) {

    let gate_entries = Array.isArray(gate_entry) ? gate_entry : [gate_entry];

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.make_pr_from_gate_entries",
        args: { gate_entries },
        freeze: true,
        freeze_message: __("Creating Purchase Receipt..."),

        callback(r) {
            if (!r.message) {
                frappe.msgprint(__("Failed to create Purchase Receipt"));
                return;
            }

            frappe.model.sync(r.message);
            frappe.set_route("Form", "Purchase Receipt", r.message.name);
        }
    });
}


// ===================================
// 🚀 OPEN GATE ENTRY
// ===================================
function open_gate_entry_mapper(frm) {

    if (!frm.doc.supplier) {
        frappe.throw(__("Please select Supplier first"));
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_pending_gate_entries",
        args: { supplier: frm.doc.supplier },
        freeze: true,
        freeze_message: __("Fetching Gate Entries..."),

        callback(r) {

            let data = r.message || [];

            if (!data.length) {
                frappe.msgprint(__("No pending Gate Entries found"));
                return;
            }

            let names = data.map(d => d.gate_entry);

            let dialog = new frappe.ui.form.MultiSelectDialog({
                doctype: "Gate Entry",
                target: frm,

                setters: {
                    consignor: frm.doc.supplier
                },

                get_query() {
                    return {
                        filters: {
                            name: ["in", names],
                            consignor: frm.doc.supplier
                        }
                    };
                },

                columns: [
                    {
                        fieldname: "name",
                        label: __("Gate Entry"),
                        fieldtype: "Link",
                        options: "Gate Entry"
                    },
                    {
                        fieldname: "consignor",
                        label: __("Supplier"),
                        fieldtype: "Link",
                        options: "Supplier"
                    }
                ],

                action(selections) {
                    if (!selections.length) {
                        frappe.msgprint(__("Please select at least one Gate Entry"));
                        return;
                    }

                    map_gate_entry_to_purchase_receipt(frm, selections);
                    dialog.dialog.hide();
                }
            });
        }
    });
}


// ===================================
// 🚀 HANDLE BARCODE
// ===================================
function handle_barcode(frm, item_code, step) {

    let row = frm.doc.items.find(d => d.item_code === item_code);

    if (!row) {
        row = frm.add_child("items");
        row.item_code = item_code;
        row.qty = step;
        row.received_qty = step;
    } else {
        row.qty = flt(row.qty || 0) + step;
        row.received_qty = row.qty;
    }

    update_total_qty_fast(frm, step);

    // 🔥 ONLY ROW REFRESH (IMPORTANT)
    frm.fields_dict.items.grid.refresh_row(row.name);
}


// ===================================
// 🚀 HANDLE SERIAL
// ===================================
function handle_serial(frm, serial, step) {

    let po_items = (frm.doc.items || [])
        .filter(d => d.purchase_order_item)
        .map(d => d.purchase_order_item);

    if (!po_items.length) {
        frappe.throw("No Purchase Order linked");
    }

    frappe.call({
        method: "franchise_erp.custom.purchase_reciept.validate_po_serial",
        args: {
            scanned_serial: serial,
            po_items
        },
        freeze: false,

        callback: function(r) {

            if (!r.message) return;

            let row = frm.doc.items.find(
                d => d.purchase_order_item === r.message.purchase_order_item
            );

            if (!row) {
                frappe.throw("Row not found");
            }

            if (!row.serial_no) row.serial_no = "";

            row.serial_no += (row.serial_no ? "\n" : "") + serial;

            row.qty = flt(row.qty || 0) + step;
            row.received_qty = row.qty;

            serial_cache.add(serial);

            update_total_qty_fast(frm, step);

            frm.fields_dict.items.grid.refresh_row(row.name);
        }
    });
}


// ===================================
// 🚀 MAIN FORM
// ===================================
frappe.ui.form.on("Purchase Receipt", {

    onload(frm) {

        if (!frm.is_new()) {
            build_initial_cache(frm);
            return;
        }

        if (frm.doc.is_subcontracted === 1) return;

        (frm.doc.items || []).forEach(row => {
            if (row.purchase_order_item) {
                row.qty = 0;
                row.serial_no = "";
            }
        });

        build_initial_cache(frm);

        frm.refresh_field("items");
    },

    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Gate Entry"),
                () => open_gate_entry_mapper(frm),
                __("Get Items From")
            );
        }
    },

    // ===================================
    // 🚀 SCAN (OPTIMIZED)
    // ===================================
    custom_scan_serial_no(frm) {

        let scanned_value = frm.doc.custom_scan_serial_no;
            if (!scanned_value) return;

            scanned_value = scanned_value.trim();

            // 🔥 INSTANT CLEAR (VERY IMPORTANT FIX)
            frm.set_value("custom_scan_serial_no", "");

        let step = frm.doc.is_return ? -1 : 1;

        // ✅ barcode cache
        if (barcode_cache[scanned_value]) {
            handle_barcode(frm, barcode_cache[scanned_value], step);
            frm.set_value("custom_scan_serial_no", "");
            return;
        }

        // ✅ serial duplicate check
        if (serial_cache.has(scanned_value)) {
            frm.set_value("custom_scan_serial_no", "");
            frappe.throw(`Serial No ${scanned_value} already scanned`);
        }

        frappe.call({
            method: "franchise_erp.custom.purchase_reciept.get_item_by_barcode",
            args: { barcode: scanned_value },
            freeze: false,

            callback: function(res) {

                if (res.message && res.message.item_code) {

                    barcode_cache[scanned_value] = res.message.item_code;

                    handle_barcode(frm, res.message.item_code, step);
                    frm.set_value("custom_scan_serial_no", "");
                    return;
                }

                handle_serial(frm, scanned_value, step);
            }
        });
    }
});


// ===================================
// 🚀 ITEM AUTO FILL
// ===================================
frappe.ui.form.on("Purchase Receipt Item", {
    item_code(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.item_code) return;

        frappe.db.get_value("Item", row.item_code, [
            "custom_barcode_code",
            "custom_colour_name",
            "custom_size",
            "custom_departments"
        ]).then(r => {

            if (!r.message) return;

            frappe.model.set_value(cdt, cdn, "custom_style", r.message.custom_barcode_code);
            frappe.model.set_value(cdt, cdn, "custom_color", r.message.custom_colour_name);
            frappe.model.set_value(cdt, cdn, "custom_size", r.message.custom_size);
            frappe.model.set_value(cdt, cdn, "custom_department", r.message.custom_departments);

        });
    }
});


// ===================================
// 🚀 BEFORE SUBMIT
// ===================================
frappe.ui.form.on("Purchase Receipt", {
    before_submit(frm) {

        if (!frm.doc.custom_source_sales_invoice) return;

        if (frappe.session.user === "Administrator") return;

        if (
            frm.doc.is_return === 0 &&
            frappe.session.user === frm.doc.owner &&
            frm.doc.represents_company
        ) {
            frappe.msgprint("Supplier cannot submit Normal Purchase Receipt");
            frappe.validated = false;
        }
    }
});


// ===================================
// 🚀 DEFAULT WAREHOUSE
// ===================================
frappe.ui.form.on("Purchase Receipt", {
    company(frm) {

        if (!(frm.is_new() && frm.doc.company)) return;

        frappe.db.get_value(
            "SIS Configuration",
            { company: frm.doc.company },
            "warehouse"
        ).then(r => {

            if (r.message && r.message.warehouse) {
                frm.set_value("set_warehouse", r.message.warehouse);
            }
        });
    }
});


// frappe.ui.form.on("Purchase Receipt Item", {
//     item_code(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];

//         if (frm.doc.is_subcontracted) {
//             frappe.model.set_value(cdt, cdn, "use_serial_batch_fields", 0);
//             frappe.model.set_value(cdt, cdn, "serial_no", "");
//         }
//     }
// });




// frappe.ui.form.on("Purchase Receipt", {

//     refresh(frm) {

//         if (frm.doc.docstatus !== 0) return;

//         frm.add_custom_button("Upload Serial Excel", () => {

//             let dialog = new frappe.ui.Dialog({

//                 title: "Upload Serial Numbers (Excel)",

//                 size: "small",

//                 fields: [

//                     {
//                         label: "Excel File",
//                         fieldname: "file",
//                         fieldtype: "Attach",
//                         reqd: 1
//                     },

//                     {
//                         label: "Replace Existing Items",
//                         fieldname: "replace",
//                         fieldtype: "Check",
//                         default: 1
//                     }

//                 ],

//                 primary_action_label: "Upload",

//                 primary_action(values) {

//                     if (!values.file) {
//                         frappe.msgprint("Please upload excel file");
//                         return;
//                     }

//                     frappe.call({

//                         method: "franchise_erp.api.upload_serial_excel",

//                         args: {
//                             file_url: values.file,
//                             supplier: frm.doc.supplier
//                         },

//                         freeze: true,

//                         freeze_message: "Reading Excel & verifying serial numbers...",

//                         callback(r) {

//                             if (!r.message) return;

//                             let data = r.message.items || [];
//                             let errors = r.message.errors || [];

//                             // ⭐ NEW LINE (Gate Entry auto fill)
//                             if (r.message.gate_entry_list) {

//                                 frm.set_value(
//                                     "custom_bulk_gate_entry",
//                                     r.message.gate_entry_list.join(", ")
//                                 );

//                                 console.log(
//                                     "Gate Entry:",
//                                     r.message.gate_entry_list
//                                 );

//                             }

//                             if (values.replace) {

//                                 frm.clear_table("items");

//                             }

//                             let item_map = {};

//                             data.forEach(d => {

//                                 let key =
//                                     d.item_code +
//                                     "_" +
//                                     d.rate +
//                                     "_" +
//                                     d.purchase_order_item;

//                                 if (!item_map[key]) {

//                                     let row = frm.add_child("items");

//                                     Object.assign(row, d);

//                                     row.qty = 1;

//                                     row.received_qty = 1;

//                                     item_map[key] = row;

//                                 }
//                                 else {

//                                     let row = item_map[key];

//                                     row.qty += 1;

//                                     row.received_qty += 1;

//                                     if (row.serial_no)

//                                         row.serial_no += "\n" + d.serial_no;

//                                     else

//                                         row.serial_no = d.serial_no;

//                                 }

//                             });

//                             frm.refresh_field("items");

//                             frm.refresh_field("custom_bulk_gate_entry");

//                             frm.trigger("calculate_taxes_and_totals");


//                             if (data.length) {

//                                 frappe.show_alert({

//                                     message:
//                                         data.length +
//                                         " serial processed",

//                                     indicator: "green"

//                                 });

//                             }


//                             if (errors.length) {

//                                 frappe.msgprint({

//                                     title: "Skipped Serials",

//                                     indicator: "orange",

//                                     message:
//                                         "<div style='max-height:200px;overflow:auto'>" +
//                                         errors.join("<br>") +
//                                         "</div>"

//                                 });

//                             }


//                             console.log("Items:", data);

//                             console.log("Errors:", errors);


//                             dialog.hide();

//                         }

//                     });

//                 }

//             });

//             dialog.show();

//         });

//     }

// });

// frappe.ui.form.on("Purchase Receipt", {

//     refresh(frm) {

//         if (frm.doc.docstatus !== 0) return;

//         frm.add_custom_button("Upload Serial Excel", () => {

//             let dialog = new frappe.ui.Dialog({

//                 title: "Upload Serial Numbers (Excel)",

//                 size: "small",

//                 fields: [

//                     {
//                         label: "Excel File",
//                         fieldname: "file",
//                         fieldtype: "Attach",
//                         reqd: 1
//                     },

//                     {
//                         label: "Replace Existing Items",
//                         fieldname: "replace",
//                         fieldtype: "Check",
//                         default: 1
//                     }

//                 ],

//                 primary_action_label: "Upload",

//                 async primary_action(values) {

//                     if (!values.file) {

//                         frappe.msgprint("Please upload excel file");
//                         return;
//                     }

//                     console.clear();
//                     console.log("===== SERIAL UPLOAD START =====");

//                     frappe.call({

//                         method: "franchise_erp.api.upload_serial_excel",

//                         args: {
//                             file_url: values.file,
//                             supplier: frm.doc.supplier
//                         },

//                         freeze: true,
//                         freeze_message: "Checking serials & gate entry...",

//                         callback(r) {

//                             if (!r.message) return;

//                             let data = r.message.items || [];
//                             let errors = r.message.errors || [];
//                             let gate_list = r.message.gate_entry_list || [];

//                             console.log("ITEMS FROM PYTHON:", data);
//                             console.log("GATE ENTRY LIST:", gate_list);

//                             if (values.replace) {
//                                 frm.clear_table("items");
//                             }

//                             let item_map = {};

//                             data.forEach(d => {

//                                 let key =
//                                     d.item_code +
//                                     "_" +
//                                     d.rate +
//                                     "_" +
//                                     d.purchase_order_item +
//                                     "_" +
//                                     (d.custom_bulk_gate_entry || "");

//                                 if (!item_map[key]) {

//                                     let row = frm.add_child("items");

//                                     Object.assign(row, d);

//                                     row.qty = 1;
//                                     row.received_qty = 1;

//                                     // IMPORTANT
//                                     row.custom_bulk_gate_entry =
//                                         d.custom_bulk_gate_entry || "";

//                                     console.log(
//                                         "ADD ROW:",
//                                         d.item_code,
//                                         "GATE:",
//                                         row.custom_bulk_gate_entry
//                                     );

//                                     item_map[key] = row;

//                                 }
//                                 else {

//                                     let row = item_map[key];

//                                     row.qty += 1;
//                                     row.received_qty += 1;

//                                     if (row.serial_no)
//                                         row.serial_no += "\n" + d.serial_no;
//                                     else
//                                         row.serial_no = d.serial_no;

//                                 }

//                             });

//                             frm.refresh_field("items");

//                             console.log(
//                                 "FINAL ITEMS TABLE:",
//                                 frm.doc.items
//                             );

//                             frm.trigger("calculate_taxes_and_totals");

//                             if (data.length) {

//                                 frappe.show_alert({

//                                     message:
//                                         data.length +
//                                         " serial processed",

//                                     indicator: "green"

//                                 });

//                             }

//                             if (errors.length) {

//                                 frappe.msgprint({

//                                     title: "Skipped Serials",

//                                     indicator: "orange",

//                                     message:
//                                         "<div style='max-height:200px;overflow:auto'>" +
//                                         errors.join("<br>") +
//                                         "</div>"

//                                 });

//                             }

//                             dialog.hide();

//                             console.log("===== SERIAL UPLOAD END =====");

//                         }

//                     });

//                 }

//             });

//             dialog.show();

//         });

//     }

// });





frappe.ui.form.on("Purchase Receipt", {

    refresh(frm) {

        if (frm.doc.docstatus !== 0) return;

        frm.add_custom_button("Upload Serial Excel", () => {

            let dialog = new frappe.ui.Dialog({

                title: "Upload Serial Numbers (Excel)",

                size: "small",

                fields: [

                    {
                        label: "Excel File",
                        fieldname: "file",
                        fieldtype: "Attach",
                        reqd: 1
                    },

                    {
                        label: "Replace Existing Items",
                        fieldname: "replace",
                        fieldtype: "Check",
                        default: 1
                    }

                ],

                primary_action_label: "Upload",

                primary_action(values) {

                    if (!values.file) {

                        frappe.msgprint("Please upload excel file");
                        return;

                    }

                    frappe.call({

                        method: "franchise_erp.api.upload_serial_excel",

                        args: {

                            file_url: values.file,
                            supplier: frm.doc.supplier

                        },

                        freeze: true,

                        freeze_message: "Reading Excel...",

                        callback(r) {

                            if (!r.message) return;

                            let data = r.message.items || [];
                            let errors = r.message.errors || [];

                            console.log("DATA:", data);


                            // ✅ DELETE DEFAULT ROW
                            if (
                                frm.doc.items &&
                                frm.doc.items.length === 1 &&
                                !frm.doc.items[0].item_code
                            ) {

                                frm.clear_table("items");

                            }


                            // optional replace
                            if (values.replace) {

                                frm.clear_table("items");

                            }


                            let item_map = {};


                            data.forEach(d => {

                                let key =
                                    d.item_code +
                                    "_" +
                                    d.rate +
                                    "_" +
                                    d.purchase_order_item +
                                    "_" +
                                    (d.custom_bulk_gate_entry || "");


                                if (!item_map[key]) {

                                    let row = frm.add_child("items");

                                    Object.assign(row, d);

                                    row.qty = 1;

                                    row.received_qty = 1;

                                    // child table field
                                    row.custom_bulk_gate_entry =
                                        d.custom_bulk_gate_entry || "";


                                    item_map[key] = row;

                                }
                                else {

                                    let row = item_map[key];

                                    row.qty += 1;

                                    row.received_qty += 1;


                                    if (row.serial_no)

                                        row.serial_no += "\n" + d.serial_no;

                                    else

                                        row.serial_no = d.serial_no;

                                }

                            });


                            frm.refresh_field("items");

                            frm.trigger("calculate_taxes_and_totals");


                            if (data.length) {

                                frappe.show_alert({

                                    message:
                                        data.length +
                                        " Serial Added",

                                    indicator: "green"

                                });

                            }


                            if (errors.length) {

                                frappe.msgprint({

                                    title: "Skipped Serials",

                                    indicator: "orange",

                                    message:
                                        "<div style='max-height:200px;overflow:auto'>" +
                                        errors.join("<br>") +
                                        "</div>"

                                });

                            }


                            dialog.hide();

                        }

                    });

                }

            });

            dialog.show();

        });

    }

});