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
        if (
            frm.doc.docstatus === 0 &&
            frm.doc.stock_entry_type === "Send to Subcontractor"
            && !frm.doc.bill_from_address
            && frm.doc.company
        ) {

            frappe.call({
                method: "frappe.contacts.doctype.address.address.get_default_address",
                args: {
                    doctype: "Company",
                    name: frm.doc.company
                },
                callback: function(res) {
                    if (res.message) {
                        frm.set_value(
                            "bill_from_address",
                            res.message
                        );
                    }
                }
            });
        }

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




function setup_ewaybill(frm) {

    if (!frm.doc.supplier) {
        return;
    }

    frappe.db.get_value(
        "Supplier",
        frm.doc.supplier,
        "custom_transporter"
    ).then(r => {

        const supplier_transporter =
            r.message?.custom_transporter || "";

        if (!supplier_transporter) {
            return;
        }

        const observer = new MutationObserver(() => {

            document.querySelectorAll(".modal").forEach(dialog => {

                if (dialog.dataset.ewaybillReady === "1") {
                    return;
                }

                const title =
                    dialog.querySelector(".modal-title");

                if (!title) {
                    return;
                }

                const title_text =
                    title.innerText.trim().toLowerCase();

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
                            supplier_transporter
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


function initialize_ewaybill(
    frm,
    dialog,
    supplier_transporter
) {

    /*
     * Transporter field
     */
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
        transporter_wrapper.querySelector("input") ||
        transporter_wrapper.querySelector("select");

    if (!transporter_input) {
        return;
    }


    /*
     * Supplier Master transporter
     */
    transporter_input.value =
        supplier_transporter;

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


    /*
     * Existing Vehicle Number field
     */
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


    /*
     * Existing value load
     */
    if (vehicle_input) {

        vehicle_input.value =
            frm.doc.custom_vehicle_number || "";


        /*
         * Stock Entry me value update
         */
        vehicle_input.addEventListener(
            "input",
            function () {

                frm.set_value(
                    "custom_vehicle_number",
                    this.value
                );
            }
        );
    }


    /*
     * Initial state
     */
    update_vehicle_field(
        frm,
        dialog,
        transporter_input.value
    );


    /*
     * Transporter monitor
     */
    let last_transporter =
        transporter_input.value || "";


    const transporter_checker =
        setInterval(() => {

            if (!document.body.contains(dialog)) {
                clearInterval(transporter_checker);
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


                update_vehicle_field(
                    frm,
                    dialog,
                    current_transporter
                );
            }

        }, 200);


    /*
     * Generate (Part A) validation
     */
    setup_generate_validation(
        frm,
        dialog,
        transporter_input
    );
}


function update_vehicle_field(
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
            .toLowerCase() === "by hand";


    if (is_by_hand) {

        /*
         * SHOW
         */
        vehicle_wrapper.style.display =
            "block";


        /*
         * REQUIRED
         */
        vehicle_input.required = true;

        vehicle_input.setAttribute(
            "required",
            "required"
        );


        if (required_star) {
            required_star.style.display =
                "inline";
        }


    } else {

        /*
         * HIDE
         */
        vehicle_wrapper.style.display =
            "none";


        /*
         * NOT REQUIRED
         */
        vehicle_input.required = false;

        vehicle_input.removeAttribute(
            "required"
        );


        if (required_star) {
            required_star.style.display =
                "none";
        }


        /*
         * Clear
         */
        vehicle_input.value = "";

        frm.set_value(
            "custom_vehicle_number",
            ""
        );
    }
}


/*
 * ==========================================
 * Generate (Part A) Validation
 * ==========================================
 */

function setup_generate_validation(
    frm,
    dialog,
    transporter_input
) {

    /*
     * Dialog ke buttons check karo
     */
    const check_button = setInterval(() => {

        if (!document.body.contains(dialog)) {
            clearInterval(check_button);
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
                button.dataset.vehicleValidation !== "1"
            ) {

                button.dataset.vehicleValidation =
                    "1";


                /*
                 * Generate button click
                 */
                button.addEventListener(
                    "click",
                    function (e) {

                        const transporter =
                            transporter_input.value || "";


                        const is_by_hand =
                            transporter
                                .trim()
                                .toLowerCase() ===
                            "by hand";


                        /*
                         * ONLY By Hand me mandatory
                         */
                        if (is_by_hand) {

                            const vehicle_input =
                                dialog.querySelector(
                                    "#custom-vehicle-number"
                                );


                            const vehicle_number =
                                vehicle_input?.value
                                    ?.trim() || "";


                            if (!vehicle_number) {

                                /*
                                 * Stop Generate
                                 */
                                e.preventDefault();
                                e.stopPropagation();
                                e.stopImmediatePropagation();


                                /*
                                 * Error message
                                 */
                                frappe.msgprint({
                                    title:
                                        __("Vehicle Number Required"),

                                    message:
                                        __(
                                            "Vehicle Number is mandatory. Please enter a valid Vehicle Number before generating the e-way bill."
                                        ),

                                    indicator:
                                        "red"
                                });


                                /*
                                 * Focus
                                 */
                                if (vehicle_input) {

                                    setTimeout(() => {

                                        vehicle_input.focus();

                                    }, 100);
                                }


                                return false;
                            }


                            /*
                             * Stock Entry me value set
                             */
                            frm.set_value(
                                "custom_vehicle_number",
                                vehicle_number
                            );

                            /*
                             * Save before Generate
                             */
                            frm.save()
                                .then(() => {

                                    console.log(
                                        "Vehicle Number saved:",
                                        vehicle_number
                                    );

                                });
                        }
                    },
                    true
                );
            }
        });

    }, 200);


    /*
     * 60 sec baad stop
     */
    setTimeout(() => {
        clearInterval(check_button);
    }, 60000);
}