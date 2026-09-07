frappe.ui.form.on('Stock Entry', {

    refresh(frm) {
        toggle_fetch_button(frm);
        calculate_total_qty(frm);
        setup_ewaybill(frm);
    },

    stock_entry_type(frm) {
        toggle_fetch_button(frm);
    },

    custom_to_company(frm) {
        toggle_intercompany_flag(frm);
    },

    company(frm) {
        toggle_intercompany_flag(frm);
    },

    items_remove(frm) {

        calculate_total_qty(frm);
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


// frappe.ui.form.on('Stock Entry', {
//     onload: function(frm) {

//         if (frm.doc.stock_entry_type !== "Material Transfer") return;

//         frm.set_query("custom_gate_entry", function() {
//             return {
//                 query: "franchise_erp.custom.stock_entry.get_available_gate_entries_for_wip_return_stock"
//             };
//         });
//     }
// });

// frappe.ui.form.on('Stock Entry', {
//     onload: function(frm) {
        
//         if (frm.doc.stock_entry_type !== "Material Receipt") return;

//         frm.set_query("custom_gate_entrys", function() {
//             return {
//                 query: "franchise_erp.custom.stock_entry.get_available_gate_entries_for_transfer_in_stock"
//             };
//         });

//         if (
//             frm.doc.stock_entry_type === "Send to Subcontractor"
//             && !frm.doc.bill_from_address
//             && frm.doc.company
//         ) {

//             frappe.call({
//                 method: "frappe.contacts.doctype.address.address.get_default_address",
//                 args: {
//                     doctype: "Company",
//                     name: frm.doc.company
//                 },
//                 callback: function(res) {

//                     if (res.message) {
//                         frm.set_value(
//                             "bill_from_address",
//                             res.message
//                         );
//                     }
//                 }
//             });
//         }
        
//         calculate_total_qty(frm);
//     }
// });
frappe.ui.form.on('Stock Entry', {
    onload: function(frm) {

        // Material Receipt specific logic
        if (frm.doc.stock_entry_type === "Material Receipt") {

            frm.set_query("custom_gate_entrys", function() {
                return {
                    query: "franchise_erp.custom.stock_entry.get_available_gate_entries_for_transfer_in_stock"
                };
            });
        }

        // Send to Subcontractor logic
        // if (
        //     frm.doc.docstatus === 0 &&
        //     frm.doc.stock_entry_type === "Send to Subcontractor"
        //     && !frm.doc.bill_from_address
        //     && frm.doc.company
        // ) {

        //     frappe.call({
        //         method: "frappe.contacts.doctype.address.address.get_default_address",
        //         args: {
        //             doctype: "Company",
        //             name: frm.doc.company
        //         },
        //         callback: function(res) {
        //             if (res.message) {
        //                 frm.set_value(
        //                     "bill_from_address",
        //                     res.message
        //                 );
        //             }
        //         }
        //     });
        // }

        calculate_total_qty(frm);
    }
});

frappe.ui.form.on("Stock Entry Detail", {

    qty(frm, cdt, cdn) {
        calculate_total_qty(frm);
    },
});
// =====================================
// ✅ TOTAL QTY
// =====================================
function calculate_total_qty(frm) {

    let total = 0;

    (frm.doc.items || []).forEach(row => {

        total += flt(row.qty || 0);
    });

    // ✅ ONLY UPDATE IF DIFFERENT
    if (flt(frm.doc.custom_total_quantity) !== flt(total)) {

        frm.doc.custom_total_quantity = total;

        frm.refresh_field("custom_total_quantity");

        // ✅ RESET DIRTY STATE
        frm.doc.__unsaved = 0;
    }
}




// =========================================================
// E-WAY BILL SETUP
// =========================================================

function setup_ewaybill(frm) {

    if (!frm.doc.custom_outgoing_logistics_no) {
        return;
    }

    frappe.db.get_value(
        "Outgoing Logistics",
        frm.doc.custom_outgoing_logistics_no,
        "s_transporter"
    ).then(r => {

        const transporter =
            r.message?.s_transporter || "";

        if (!transporter) {
            console.log(
                "No s_transporter found in Outgoing Logistics"
            );
            return;
        }

        console.log(
            "Outgoing Logistics Transporter:",
            transporter
        );

        // =================================================
        // PATCH FRAPPE DIALOG VALIDATION
        // =================================================

        patch_ewaybill_dialog_validation();

        // =================================================
        // OBSERVE E-WAY BILL POPUP
        // =================================================

        const observer = new MutationObserver(() => {

            document.querySelectorAll(".modal").forEach(dialog => {

                if (
                    dialog.dataset.ewaybillReady === "1"
                ) {
                    return;
                }

                const title =
                    dialog.querySelector(".modal-title");

                if (!title) {
                    return;
                }

                const title_text =
                    title.innerText
                        .trim()
                        .toLowerCase();

                if (
                    title_text.includes("e-way") ||
                    title_text.includes("eway") ||
                    title_text.includes("e way")
                ) {

                    dialog.dataset.ewaybillReady = "1";

                    setTimeout(() => {

                        initialize_ewaybill(
                            frm,
                            dialog,
                            transporter
                        );

                    }, 300);
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        setTimeout(() => {
            observer.disconnect();
        }, 60000);
    });
}


// =========================================================
// PATCH FRAPPE DIALOG GET VALUES
// =========================================================

function patch_ewaybill_dialog_validation() {

    if (
        frappe.ui.Dialog.prototype
            .__ewaybill_validation_patched
    ) {
        return;
    }

    frappe.ui.Dialog.prototype
        .__ewaybill_validation_patched = true;

    const original_get_values =
        frappe.ui.Dialog.prototype.get_values;

    frappe.ui.Dialog.prototype.get_values =
        function (...args) {

            try {

                const dialog_wrapper =
                    this.$wrapper?.[0];

                const title =
                    dialog_wrapper?.querySelector(
                        ".modal-title"
                    );

                const title_text =
                    title?.innerText
                        ?.trim()
                        ?.toLowerCase() || "";

                const is_ewaybill =
                    title_text.includes("e-way") ||
                    title_text.includes("eway") ||
                    title_text.includes("e way");

                if (is_ewaybill) {

                    const transporter_field =
                        this.fields_dict?.transporter ||
                        this.fields_dict?.custom_transporter;

                    const transporter =
                        transporter_field?.get_value?.() ||
                        transporter_field?.value ||
                        "";

                    const is_by_hand =
                        transporter
                            .toString()
                            .trim()
                            .toLowerCase() ===
                        "by hand";

                    console.log(
                        "E-Waybill get_values:",
                        {
                            transporter,
                            is_by_hand
                        }
                    );

                    if (is_by_hand) {

                        disable_gst_transporter_validation(
                            this
                        );

                    } else {

                        enable_gst_transporter_validation(
                            this
                        );
                    }
                }

            } catch (error) {

                console.log(
                    "E-Waybill validation patch error:",
                    error
                );
            }

            return original_get_values.apply(
                this,
                args
            );
        };
}


// =========================================================
// FIND GST TRANSPORTER FIELD
// =========================================================

function find_gst_transporter_control(dialog) {

    if (!dialog) {
        return null;
    }

    const possible_fieldnames = [

        "transporter_id",
        "gst_transporter_id",
        "gst_transporter",
        "transporter_gstin",
        "transporter_gst",
        "gstin_transporter",
        "transporter_gst_no",
        "gst_transporter_no",
        "gst_transporter_id_part_a"

    ];

    for (
        const fieldname
        of possible_fieldnames
    ) {

        if (
            dialog.fields_dict &&
            dialog.fields_dict[fieldname]
        ) {

            return dialog.fields_dict[fieldname];
        }
    }

    if (dialog.fields) {

        for (
            const field
            of dialog.fields
        ) {

            const label =
                (
                    field.label ||
                    ""
                )
                .toString()
                .trim()
                .toLowerCase();

            if (
                label === "gst transporter id" ||
                label.includes("gst transporter id")
            ) {

                if (
                    dialog.fields_dict &&
                    dialog.fields_dict[field.fieldname]
                ) {

                    return dialog.fields_dict[
                        field.fieldname
                    ];
                }
            }
        }
    }

    return null;
}


// =========================================================
// DISABLE GST TRANSPORTER VALIDATION
// =========================================================

function disable_gst_transporter_validation(
    dialog
) {

    const gst_field =
        find_gst_transporter_control(
            dialog
        );

    if (!gst_field) {

        console.log(
            "GST Transporter ID Frappe control not found"
        );

        disable_gst_dom_field(
            dialog.$wrapper?.[0]
        );

        return;
    }

    console.log(
        "GST Transporter ID found:",
        gst_field.df?.fieldname
    );

    if (gst_field.df) {

        gst_field.df.reqd = 0;
        gst_field.df.mandatory = 0;
    }

    gst_field.reqd = false;

    try {

        if (
            typeof gst_field.set_value ===
            "function"
        ) {

            gst_field.set_value("");
        }

    } catch (e) {

        console.log(
            "Unable to clear GST Transporter ID:",
            e
        );
    }

    try {

        if (
            typeof gst_field.refresh ===
            "function"
        ) {

            gst_field.refresh();
        }

    } catch (e) {

        console.log(
            "GST field refresh error:",
            e
        );
    }

    if (gst_field.wrapper) {

        gst_field.wrapper
            .querySelectorAll(
                "input, textarea, select"
            )
            .forEach(input => {

                input.required = false;

                input.removeAttribute(
                    "required"
                );

                input.removeAttribute(
                    "aria-required"
                );
            });

        gst_field.wrapper
            .querySelectorAll(
                ".reqd"
            )
            .forEach(element => {

                element.style.display =
                    "none";
            });

        gst_field.wrapper
            .classList.remove(
                "has-error"
            );
    }

    disable_gst_dom_field(
        dialog.$wrapper?.[0]
    );
}


// =========================================================
// DOM GST FIELD DISABLE
// =========================================================

function disable_gst_dom_field(
    dialog_element
) {

    if (!dialog_element) {
        return;
    }

    const fields =
        dialog_element.querySelectorAll(
            ".frappe-control"
        );

    fields.forEach(wrapper => {

        const label =
            wrapper.querySelector(
                ".control-label"
            );

        if (!label) {
            return;
        }

        const text =
            label.innerText
                .trim()
                .toLowerCase()
                .replace(/\*/g, "")
                .trim();

        if (
            text.includes(
                "gst transporter id"
            )
        ) {

            console.log(
                "GST Transporter DOM field found"
            );

            wrapper
                .querySelectorAll(
                    "input, textarea, select"
                )
                .forEach(input => {

                    input.required = false;

                    input.removeAttribute(
                        "required"
                    );

                    input.removeAttribute(
                        "aria-required"
                    );
                });

            wrapper
                .querySelectorAll(
                    ".reqd"
                )
                .forEach(element => {

                    element.style.display =
                        "none";
                });

            const input =
                wrapper.querySelector(
                    "input"
                );

            if (input) {

                input.value = "";

                input.dispatchEvent(
                    new Event("input", {
                        bubbles: true
                    })
                );

                input.dispatchEvent(
                    new Event("change", {
                        bubbles: true
                    })
                );
            }

            wrapper.style.display =
                "none";
        }
    });
}


// =========================================================
// ENABLE GST TRANSPORTER VALIDATION
// =========================================================

function enable_gst_transporter_validation(
    dialog
) {

    const gst_field =
        find_gst_transporter_control(
            dialog
        );

    if (!gst_field) {

        console.log(
            "GST Transporter ID field not found"
        );

        return;
    }

    if (gst_field.df) {

        gst_field.df.reqd = 1;
        gst_field.df.mandatory = 1;
    }

    gst_field.reqd = true;

    try {

        if (
            typeof gst_field.refresh ===
            "function"
        ) {

            gst_field.refresh();
        }

    } catch (e) {

        console.log(e);
    }

    if (gst_field.wrapper) {

        gst_field.wrapper.style.display =
            "block";

        gst_field.wrapper
            .querySelectorAll(
                "input, textarea, select"
            )
            .forEach(input => {

                input.required = true;

                input.setAttribute(
                    "required",
                    "required"
                );

                input.setAttribute(
                    "aria-required",
                    "true"
                );
            });
    }
}


// =========================================================
// INITIALIZE E-WAY BILL
// =========================================================

function initialize_ewaybill(
    frm,
    dialog,
    transporter_value
) {

    // =================================================
    // CORE VEHICLE NUMBER FIRST
    // =================================================

    set_core_vehicle_number(
        frm,
        dialog
    );

    const transporter_wrapper =
        dialog.querySelector(
            '[data-fieldname="transporter"]'
        ) ||
        dialog.querySelector(
            '[data-fieldname="custom_transporter"]'
        );

    if (!transporter_wrapper) {

        console.log(
            "Transporter field not found"
        );

        return;
    }

    const transporter_input =
        transporter_wrapper.querySelector(
            "input"
        ) ||
        transporter_wrapper.querySelector(
            "select"
        );

    if (!transporter_input) {

        console.log(
            "Transporter input not found"
        );

        return;
    }

    // =================================================
    // SET TRANSPORTER
    // =================================================

    transporter_input.value =
        transporter_value;

    transporter_input.dispatchEvent(
        new Event("input", {
            bubbles: true
        })
    );

    transporter_input.dispatchEvent(
        new Event("change", {
            bubbles: true
        })
    );

    // =================================================
    // CUSTOM VEHICLE NUMBER FIELD
    // =================================================

    let vehicle_wrapper =
        dialog.querySelector(
            "#custom-vehicle-number-wrapper"
        );

    if (!vehicle_wrapper) {

        vehicle_wrapper =
            document.createElement("div");

        vehicle_wrapper.id =
            "custom-vehicle-number-wrapper";

        vehicle_wrapper.className =
            "form-group";

        vehicle_wrapper.innerHTML = `
            <label class="control-label">
                Vehicle Number
                <span
                    id="vehicle-number-required"
                    class="text-danger"
                >
                    *
                </span>
            </label>

            <input
                type="text"
                id="custom-vehicle-number"
                class="form-control"
                placeholder="Enter Vehicle Number"
            />
        `;

        transporter_wrapper.insertAdjacentElement(
            "afterend",
            vehicle_wrapper
        );
    }

    const vehicle_input =
        dialog.querySelector(
            "#custom-vehicle-number"
        );

    // =================================================
    // SET CUSTOM VEHICLE NUMBER
    // =================================================

    if (vehicle_input) {

        vehicle_input.value =
            frm.doc.custom_vehicle_number || "";

        if (
            vehicle_input.dataset
                .vehicleListener !== "1"
        ) {

            vehicle_input.dataset
                .vehicleListener = "1";

            vehicle_input.addEventListener(
                "input",
                function () {

                    frm.set_value(
                        "custom_vehicle_number",
                        this.value
                    );

                    /*
                     * IMPORTANT:
                     * Custom Vehicle -> Core Vehicle
                     */

                    sync_ewaybill_vehicle_number_from_dom(
                        frm,
                        dialog
                    );
                }
            );

            vehicle_input.addEventListener(
                "change",
                function () {

                    frm.set_value(
                        "custom_vehicle_number",
                        this.value
                    );

                    sync_ewaybill_vehicle_number_from_dom(
                        frm,
                        dialog
                    );
                }
            );
        }
    }

    // =================================================
    // INITIAL CORE VEHICLE SYNC
    // =================================================

    sync_ewaybill_vehicle_number_from_dom(
        frm,
        dialog
    );

    // =================================================
    // INITIAL STATE
    // =================================================

    update_ewaybill_fields(
        frm,
        dialog,
        transporter_input.value
    );

    // =================================================
    // TRANSPORTER CHANGE MONITOR
    // =================================================

    let last_transporter =
        transporter_input.value || "";

    const transporter_checker =
        setInterval(() => {

            if (!document.body.contains(dialog)) {

                clearInterval(
                    transporter_checker
                );

                return;
            }

            const current_transporter =
                transporter_input.value || "";

            if (
                current_transporter !==
                last_transporter
            ) {

                last_transporter =
                    current_transporter;

                console.log(
                    "Transporter changed:",
                    current_transporter
                );

                update_ewaybill_fields(
                    frm,
                    dialog,
                    current_transporter
                );
            }

        }, 200);

    // =================================================
    // GENERATE VALIDATION
    // =================================================

    setup_generate_validation(
        frm,
        dialog,
        transporter_input
    );
}


// =========================================================
// UPDATE VEHICLE + GST
// =========================================================

function update_ewaybill_fields(
    frm,
    dialog,
    transporter
) {

    const vehicle_wrapper =
        dialog.querySelector(
            "#custom-vehicle-number-wrapper"
        );

    const vehicle_input =
        dialog.querySelector(
            "#custom-vehicle-number"
        );

    const required_star =
        dialog.querySelector(
            "#vehicle-number-required"
        );

    if (
        !vehicle_wrapper ||
        !vehicle_input
    ) {
        return;
    }

    const is_by_hand =
        (transporter || "")
            .trim()
            .toLowerCase() ===
        "by hand";

    console.log(
        "Transporter:",
        transporter,
        "| By Hand:",
        is_by_hand
    );

    // =================================================
    // BY HAND
    // =================================================

    if (is_by_hand) {

        vehicle_wrapper.style.display =
            "block";

        vehicle_input.required =
            true;

        vehicle_input.setAttribute(
            "required",
            "required"
        );

        if (required_star) {

            required_star.style.display =
                "inline";
        }

        make_gst_transporter_optional(
            dialog
        );

        /*
         * IMPORTANT:
         * Existing vehicle number ko
         * core vehicle_no me bhi sync karo.
         */

        sync_ewaybill_vehicle_number_from_dom(
            frm,
            dialog
        );

    } else {

        // =================================================
        // NORMAL TRANSPORTER
        // =================================================

        vehicle_wrapper.style.display =
            "none";

        vehicle_input.required =
            false;

        vehicle_input.removeAttribute(
            "required"
        );

        if (required_star) {

            required_star.style.display =
                "none";
        }

        vehicle_input.value = "";

        frm.set_value(
            "custom_vehicle_number",
            ""
        );

        /*
         * Normal transporter me custom
         * vehicle clear karne ke saath
         * core vehicle_no bhi clear.
         */

        clear_core_vehicle_number(
            dialog
        );

        make_gst_transporter_mandatory(
            dialog
        );
    }
}


// =========================================================
// ALIAS - GST OPTIONAL
// =========================================================

function make_gst_transporter_optional(
    dialog
) {

    disable_gst_transporter_validation(
        get_dialog_instance(dialog)
    );
}


// =========================================================
// ALIAS - GST MANDATORY
// =========================================================

function make_gst_transporter_mandatory(
    dialog
) {

    enable_gst_transporter_validation(
        get_dialog_instance(dialog)
    );
}


// =========================================================
// GET ACTUAL FRAPPE DIALOG INSTANCE
// =========================================================

function get_dialog_instance(
    dialog_element
) {

    if (
        dialog_element &&
        dialog_element.fields_dict
    ) {

        return dialog_element;
    }

    if (
        frappe.ui.Dialog &&
        frappe.ui.Dialog.instances
    ) {

        const instances =
            frappe.ui.Dialog.instances;

        for (
            const instance
            of instances
        ) {

            if (
                instance.$wrapper &&
                instance.$wrapper[0] ===
                dialog_element
            ) {

                return instance;
            }
        }
    }

    return {
        $wrapper: $(dialog_element),
        fields_dict: {}
    };
}


// =========================================================
// GENERATE PART A VALIDATION
// =========================================================

function setup_generate_validation(
    frm,
    dialog,
    transporter_input
) {

    const check_button =
        setInterval(() => {

            if (!document.body.contains(dialog)) {

                clearInterval(
                    check_button
                );

                return;
            }

            const buttons =
                dialog.querySelectorAll(
                    ".modal-footer button"
                );

            buttons.forEach(button => {

                const button_text =
                    button.innerText
                        .trim()
                        .toLowerCase();

                if (
                    button_text.includes(
                        "generate"
                    ) &&
                    button.dataset.vehicleValidation !==
                    "1"
                ) {

                    button.dataset.vehicleValidation =
                        "1";

                    button.addEventListener(
                        "click",
                        function (e) {

                            const transporter =
                                transporter_input.value ||
                                "";

                            const is_by_hand =
                                transporter
                                    .trim()
                                    .toLowerCase() ===
                                "by hand";

                            // =================================================
                            // ALWAYS SYNC VEHICLE BEFORE CORE BUTTON
                            // =================================================

                            sync_ewaybill_vehicle_number_from_dom(
                                frm,
                                dialog
                            );

                            // =================================================
                            // BY HAND
                            // =================================================

                            if (is_by_hand) {

                                console.log(
                                    "Generate Part A: BY HAND"
                                );

                                const frappe_dialog =
                                    find_active_ewaybill_dialog(
                                        dialog
                                    );

                                if (
                                    frappe_dialog
                                ) {

                                    disable_gst_transporter_validation(
                                        frappe_dialog
                                    );
                                }

                                disable_gst_dom_field(
                                    dialog
                                );

                                // =================================================
                                // GET VEHICLE
                                // =================================================

                                const vehicle_input =
                                    dialog.querySelector(
                                        "#custom-vehicle-number"
                                    );

                                const vehicle_number =
                                    vehicle_input?.value
                                        ?.trim() || "";

                                // =================================================
                                // VEHICLE REQUIRED
                                // =================================================

                                if (!vehicle_number) {

                                    e.preventDefault();

                                    e.stopPropagation();

                                    e.stopImmediatePropagation();

                                    frappe.msgprint({

                                        title:
                                            __("Vehicle Number Required"),

                                        message:
                                            __(
                                                "Vehicle Number is mandatory when Transporter is By Hand."
                                            ),

                                        indicator:
                                            "red"
                                    });

                                    if (vehicle_input) {

                                        setTimeout(() => {

                                            vehicle_input.focus();

                                        }, 100);
                                    }

                                    return false;
                                }

                                // =================================================
                                // SAVE CUSTOM VEHICLE
                                // =================================================

                                frm.set_value(
                                    "custom_vehicle_number",
                                    vehicle_number
                                );

                                // =================================================
                                // CRITICAL:
                                // CUSTOM VEHICLE -> CORE VEHICLE_NO
                                // =================================================

                                set_core_vehicle_number(
                                    frm,
                                    dialog
                                );

                                sync_ewaybill_vehicle_number_from_dom(
                                    frm,
                                    dialog
                                );

                                /*
                                 * Save Stock Entry
                                 */

                                frm.save()
                                    .then(() => {

                                        console.log(
                                            "Vehicle Number saved:",
                                            vehicle_number
                                        );

                                    });

                                /*
                                 * Re-apply after core
                                 * handler starts
                                 */

                                setTimeout(() => {

                                    sync_ewaybill_vehicle_number_from_dom(
                                        frm,
                                        dialog
                                    );

                                    const active_dialog =
                                        find_active_ewaybill_dialog(
                                            dialog
                                        );

                                    if (
                                        active_dialog
                                    ) {

                                        disable_gst_transporter_validation(
                                            active_dialog
                                        );
                                    }

                                    disable_gst_dom_field(
                                        dialog
                                    );

                                }, 0);

                                setTimeout(() => {

                                    sync_ewaybill_vehicle_number_from_dom(
                                        frm,
                                        dialog
                                    );

                                }, 100);

                            }

                            // =================================================
                            // NORMAL TRANSPORTER
                            // =================================================

                            else {

                                console.log(
                                    "Generate Part A: NORMAL"
                                );

                                const frappe_dialog =
                                    find_active_ewaybill_dialog(
                                        dialog
                                    );

                                if (
                                    frappe_dialog
                                ) {

                                    enable_gst_transporter_validation(
                                        frappe_dialog
                                    );
                                }
                            }

                        },
                        true
                    );
                }
            });

        }, 200);

    setTimeout(() => {

        clearInterval(
            check_button
        );

    }, 60000);
}


// =========================================================
// FIND ACTIVE E-WAYBILL FRAPPE DIALOG
// =========================================================

function find_active_ewaybill_dialog(
    dialog_element
) {

    if (
        frappe.ui.Dialog.instances
    ) {

        for (
            const instance
            of frappe.ui.Dialog.instances
        ) {

            if (
                instance.$wrapper &&
                instance.$wrapper[0] ===
                dialog_element
            ) {

                return instance;
            }
        }
    }

    return null;
}


// =========================================================
// SET CORE VEHICLE NUMBER
// =========================================================

function set_core_vehicle_number(
    frm,
    dialog
) {

    if (!dialog) {
        return;
    }

    const vehicle_number =
        (
            frm.doc.custom_vehicle_number ||
            dialog.querySelector(
                "#custom-vehicle-number"
            )?.value ||
            ""
        )
        .toString()
        .trim();

    if (!vehicle_number) {

        console.log(
            "Custom Vehicle Number is empty"
        );

        return;
    }

    // =================================================
    // CORE FRAPPE FIELD
    // =================================================

    const vehicle_wrapper =
        dialog.querySelector(
            '[data-fieldname="vehicle_no"]'
        );

    if (!vehicle_wrapper) {

        console.log(
            "Core Vehicle Number field not found"
        );

        return;
    }

    const vehicle_input =
        vehicle_wrapper.querySelector(
            "input"
        );

    if (!vehicle_input) {

        console.log(
            "Core Vehicle Number input not found"
        );

        return;
    }

    // =================================================
    // SET DOM VALUE
    // =================================================

    vehicle_input.value =
        vehicle_number;

    vehicle_input.dispatchEvent(
        new Event("input", {
            bubbles: true
        })
    );

    vehicle_input.dispatchEvent(
        new Event("change", {
            bubbles: true
        })
    );

    // =================================================
    // TRY FRAPPE CONTROL
    // =================================================

    try {

        const active_dialog =
            find_active_ewaybill_dialog(
                dialog
            );

        if (
            active_dialog &&
            active_dialog.fields_dict?.vehicle_no
        ) {

            active_dialog.fields_dict
                .vehicle_no
                .set_value(
                    vehicle_number
                );
        }

    } catch (e) {

        console.log(
            "Core vehicle Frappe set error:",
            e
        );
    }

    console.log(
        "Core Vehicle Number set:",
        vehicle_number
    );
}


// =========================================================
// SYNC CUSTOM VEHICLE -> CORE VEHICLE
// =========================================================

function sync_ewaybill_vehicle_number_from_dom(
    frm,
    dialog
) {

    if (!dialog) {
        return;
    }

    // =================================================
    // GET CUSTOM VEHICLE
    // =================================================

    let vehicle_number = "";

    const custom_input =
        dialog.querySelector(
            "#custom-vehicle-number"
        );

    if (custom_input) {

        vehicle_number =
            custom_input.value || "";
    }

    // Fallback Stock Entry value

    if (!vehicle_number) {

        vehicle_number =
            frm.doc.custom_vehicle_number ||
            "";
    }

    vehicle_number =
        String(vehicle_number)
            .trim();

    console.log(
        "Custom Vehicle Number:",
        vehicle_number
    );

    if (!vehicle_number) {
        return;
    }

    // =================================================
    // SET CORE VEHICLE
    // =================================================

    const core_wrapper =
        dialog.querySelector(
            '[data-fieldname="vehicle_no"]'
        );

    if (!core_wrapper) {

        console.log(
            "Core vehicle_no wrapper not found"
        );

        return;
    }

    const core_input =
        core_wrapper.querySelector(
            "input"
        );

    if (core_input) {

        core_input.value =
            vehicle_number;

        core_input.dispatchEvent(
            new Event("input", {
                bubbles: true
            })
        );

        core_input.dispatchEvent(
            new Event("change", {
                bubbles: true
            })
        );
    }

    // =================================================
    // FRAPPE CONTROL SET VALUE
    // =================================================

    const frappe_dialog =
        find_active_ewaybill_dialog(
            dialog
        );

    if (
        frappe_dialog &&
        frappe_dialog.fields_dict?.vehicle_no
    ) {

        try {

            frappe_dialog.fields_dict
                .vehicle_no
                .set_value(
                    vehicle_number
                );

        } catch (e) {

            console.log(
                "Unable to set core vehicle_no:",
                e
            );
        }
    }

    console.log(
        "Core vehicle_no synced:",
        vehicle_number
    );
}


// =========================================================
// CLEAR CORE VEHICLE NUMBER
// =========================================================

function clear_core_vehicle_number(
    dialog
) {

    if (!dialog) {
        return;
    }

    const core_wrapper =
        dialog.querySelector(
            '[data-fieldname="vehicle_no"]'
        );

    if (!core_wrapper) {
        return;
    }

    const core_input =
        core_wrapper.querySelector(
            "input"
        );

    if (core_input) {

        core_input.value = "";

        core_input.dispatchEvent(
            new Event("input", {
                bubbles: true
            })
        );

        core_input.dispatchEvent(
            new Event("change", {
                bubbles: true
            })
        );
    }

    const frappe_dialog =
        find_active_ewaybill_dialog(
            dialog
        );

    if (
        frappe_dialog &&
        frappe_dialog.fields_dict?.vehicle_no
    ) {

        try {

            frappe_dialog.fields_dict
                .vehicle_no
                .set_value("");

        } catch (e) {

            console.log(
                "Unable to clear core vehicle_no:",
                e
            );
        }
    }
}


// =========================================================
// OLD FUNCTION - COMPATIBILITY
// =========================================================

function sync_ewaybill_vehicle_number(
    dialog
) {

    if (!dialog) {
        return;
    }

    const custom_vehicle =
        dialog.fields_dict?.custom_vehicle_number;

    const core_vehicle =
        dialog.fields_dict?.vehicle_no;

    let vehicle_number = "";

    if (custom_vehicle) {

        vehicle_number =
            custom_vehicle.get_value() ||
            "";
    }

    if (!vehicle_number) {

        const custom_input =
            dialog.$wrapper.find(
                '[data-fieldname="custom_vehicle_number"] input'
            );

        if (custom_input.length) {

            vehicle_number =
                custom_input.val() ||
                "";
        }
    }

    vehicle_number =
        String(vehicle_number)
            .trim();

    console.log(
        "Custom Vehicle Number:",
        vehicle_number
    );

    if (!vehicle_number) {
        return;
    }

    if (core_vehicle) {

        core_vehicle.set_value(
            vehicle_number
        );

        console.log(
            "Core vehicle_no set:",
            vehicle_number
        );
    }

    const core_input =
        dialog.$wrapper.find(
            '[data-fieldname="vehicle_no"] input'
        );

    if (core_input.length) {

        core_input.val(
            vehicle_number
        );

        core_input.trigger(
            "input"
        );

        core_input.trigger(
            "change"
        );

        console.log(
            "Core Vehicle DOM value set:",
            core_input.val()
        );
    }
}


// =========================================================
// UPDATE GST REQUIREMENT
// =========================================================

function update_gst_requirement(
    dialog
) {

    if (!dialog) {
        return;
    }

    const transporter_control =
        dialog.fields_dict?.transporter;

    const gst_control =
        dialog.fields_dict?.gst_transporter_id;

    if (!gst_control) {
        return;
    }

    let transporter = "";

    if (transporter_control) {

        transporter =
            transporter_control.get_value() ||
            "";
    }

    transporter =
        String(transporter)
            .trim()
            .toLowerCase();

    const is_by_hand =
        transporter === "by hand";

    console.log(
        "Transporter:",
        transporter,
        "Is By Hand:",
        is_by_hand
    );

    gst_control.df.reqd =
        is_by_hand ? 0 : 1;

    gst_control.refresh();

    if (is_by_hand) {

        gst_control.set_value("");
    }
}
