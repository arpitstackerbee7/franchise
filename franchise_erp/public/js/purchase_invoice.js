// frappe.ui.form.on('Purchase Invoice', {
//     before_submit: function(frm) {
//         const current_user = frappe.session.user;
//         const is_return = frm.doc.is_return;
//         const owner = frm.doc.owner;
// console.log('cu:',current_user)
// console.log('ir:',is_return)
// console.log('o:',owner)
//         // Allow Administrator always
//         if (current_user === "Administrator") {
//             return;
//         }

//         // Normal PI: owner (supplier) cannot submit
//         if (is_return === 0 && current_user === owner) {
//             frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
//             frappe.validated = false;
//             return;
//         }


//         // Return PI: supplier (owner) cannot submit
//         if (is_return === 1 && current_user === owner) {
//             frappe.msgprint("Supplier cannot submit Return Purchase Invoice");
//             frappe.validated = false;
//             return;
//         }
//     }
// });
frappe.ui.form.on('Purchase Invoice', {
    before_submit: async function (frm) {
        const current_user = frappe.session.user;
        const is_return = frm.doc.is_return;
        const owner = frm.doc.owner;
        const represents_company = frm.doc.represents_company;

        // --- GET modified_by FROM PURCHASE INVOICE itself ---
        let modify = frm.doc.modified_by;

        console.log("cu:", current_user);
        console.log("ir:", is_return);
        console.log("o:", owner);
        console.log("modify:", modify);
        console.log("re c:", represents_company);
        // Allow Administrator
        if (current_user === "Administrator") {
            return;
        }

        // Normal PI: owner cannot submit
        if (is_return === 0 && current_user === owner && represents_company !== "") {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Return PI: owner cannot submit
        // if (is_return === 1 && current_user === owner) {
        //     frappe.msgprint("Supplier cannot submit Return Purchase Invoice");
        //     frappe.validated = false;
        //     return;
        // }
    }
});



frappe.ui.form.on("Purchase Invoice", {
    supplier(frm) {
        calculate_due_date(frm);
    },
    posting_date(frm) {
        calculate_due_date(frm);
    },
    bill_date(frm) {
        calculate_due_date(frm);
    }
});

function calculate_due_date(frm) {
    if (!frm.doc.supplier) return;

    frappe.db.get_value(
        "Supplier",
        frm.doc.supplier,
        [
            "custom_invoice_due_date_based_on",
            "custom_invoice_due_date_days"
        ]
    ).then(r => {
        if (!r.message) return;

        let based_on = r.message.custom_invoice_due_date_based_on;
        let days = cint(r.message.custom_invoice_due_date_days || 0);

        if (!days) return;

        let base_date = null;

        if (based_on === "Posting Date" && frm.doc.posting_date) {
            base_date = frm.doc.posting_date;
        }

        if (based_on === "Supplier Invoice Date" && frm.doc.bill_date) {
            base_date = frm.doc.bill_date;
        }

        if (!base_date) return;

        // 🔑 Run AFTER ERPNext internal logic
        frappe.after_ajax(() => {
            setTimeout(() => {
                let due_date = frappe.datetime.add_days(base_date, days);
                frm.set_value("due_date", due_date);
            }, 300);
        });
    });
}

frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        frm.set_df_property("title", "read_only", 1);
    }
});




// frappe.ui.form.on("Purchase Invoice", {
//     refresh(frm) {
//         toggle_bill_fields(frm);
//     },
//     is_return(frm) {
//         toggle_bill_fields(frm);
//     }
// });

// function toggle_bill_fields(frm) {
//     if (frm.doc.is_return) {
//         // Purchase Return → NOT mandatory
//         frm.set_df_property("bill_no", "reqd", 0);
//         frm.set_df_property("bill_date", "reqd", 0);
//     } else {
//         // Normal Purchase Invoice → Mandatory
//         frm.set_df_property("bill_no", "reqd", 1);
//         frm.set_df_property("bill_date", "reqd", 1);
//     }
// }



frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        frm.clear_custom_buttons();

        if (frm.doc.is_return && frm.doc.supplier) {
            frm.add_custom_button("Outstanding", () => {
                show_supplier_outstanding(frm);
            });
        }
    },

    is_return(frm) {
        frm.trigger("refresh");
    },

    supplier(frm) {
        frm.trigger("refresh");
    }
});

function show_supplier_outstanding(frm) {
    frappe.call({
        method: "franchise_erp.custom.purchase_invoice.get_supplier_stats",
        args: {
            supplier: frm.doc.supplier,
            company: frm.doc.company
        },
        callback(r) {
            let data = r.message || {};

            let annual_billing = data.annual_billing || 0;
            let total_unpaid = data.total_unpaid || 0;

            let d = new frappe.ui.Dialog({
                title: "Supplier Outstanding",
                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "stats",
                        options: `
                            <div style="padding:10px">
                                <p><b>Annual Billing:</b> ₹ ${annual_billing}</p>
                                <p><b>Total Unpaid:</b> ₹ ${total_unpaid}</p>
                            </div>
                        `
                    }
                ],
                size: "small"
            });

            d.show();
        }
    });
}


// get invoice_no and invoice_date from incoming logistics
frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        // jab Get Items se data aa chuka ho
        fetch_invoice_details(frm);
    }
});

function fetch_invoice_details(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) return;

    // Step 1: Purchase Receipt nikaalo
    let purchase_receipt = frm.doc.items[0].purchase_receipt;
    if (!purchase_receipt) return;

    // Step 2: Purchase Receipt se Gate Entry lao
    frappe.db.get_value(
        "Purchase Receipt",
        purchase_receipt,
        "custom_gate_entry",
        (pr_res) => {
            if (!pr_res || !pr_res.custom_gate_entry) return;

            let gate_entry = pr_res.custom_gate_entry;

            // Step 3: Gate Entry se Incoming Logistics lao
            frappe.db.get_value(
                "Gate Entry",
                gate_entry,
                "incoming_logistics",
                (ge_res) => {
                    if (!ge_res || !ge_res.incoming_logistics) return;

                    let incoming_logistics = ge_res.incoming_logistics;

                    // Step 4: Incoming Logistics se Invoice No & Date lao
                    frappe.db.get_value(
                        "Incoming Logistics",
                        incoming_logistics,
                        ["invoice_no", "invoice_date"],
                        (il_res) => {
                            if (!il_res) return;

                            // Step 5: Purchase Invoice me set karo
                            frm.set_value("bill_no", il_res.invoice_no);
                            frm.set_value("bill_date", il_res.invoice_date);
                        }
                    );
                }
            );
        }
    );
}

// Fetch default warehouse from SIS Configuration for new Purchase Invoices
frappe.ui.form.on("Purchase Invoice", {
    company: function(frm) {
        // Run only for new documents when a company is selected
        if (frm.is_new() && frm.doc.company) {
            frappe.db.get_value("SIS Configuration", { company: frm.doc.company }, "warehouse")
                .then(r => {
                    if (r.message && r.message.warehouse) {
                        // In Purchase Invoice, 'set_warehouse' field is used when 'Update Stock' is checked
                        frm.set_value("set_warehouse", r.message.warehouse);
                    }
                });
        }
    }
});


frappe.ui.form.on('Purchase Invoice', {
    is_return(frm) {
        if (frm.doc.is_return) {
            make_items_negative_pi(frm);
        }
    },

    refresh(frm) {
        if (frm.doc.is_return) {
            make_items_negative_pi(frm);
        }
    }
});

frappe.ui.form.on('Purchase Invoice Item', {

    serial_no(frm, cdt, cdn) {
        if (!frm.doc.is_return) return;

        // ⏳ wait for ERPNext to finish serial append
        setTimeout(() => {
            let row = locals[cdt][cdn];
            if (!row.serial_no) return;

            let serials = row.serial_no
                .split('\n')
                .filter(s => s.trim());

            // ✅ qty = - serial count
            frappe.model.set_value(
                cdt,
                cdn,
                'qty',
                -Math.abs(serials.length)
            );
        }, 300);
    },

    qty(frm, cdt, cdn) {
        if (!frm.doc.is_return) return;

        let row = locals[cdt][cdn];

        if (row.qty > 0) {
            frappe.model.set_value(
                cdt,
                cdn,
                'qty',
                -Math.abs(row.qty)
            );
        }
    }
});

function make_items_negative_pi(frm) {
    (frm.doc.items || []).forEach(row => {
        if (row.serial_no) {
            let serials = row.serial_no
                .split('\n')
                .filter(s => s.trim());

            frappe.model.set_value(
                row.doctype,
                row.name,
                'qty',
                -Math.abs(serials.length)
            );
        } else if (row.qty > 0) {
            frappe.model.set_value(
                row.doctype,
                row.name,
                'qty',
                -Math.abs(row.qty)
            );
        }
    });
}

// multiple tag gate entry to one purchase invoice for service transport invoice
frappe.ui.form.on('Purchase Invoice', {

    refresh: function(frm) {

        // ✅ remove duplicate button
        frm.remove_custom_button("Gate Entry", __("Get Items From"));

        // ✅ add button in correct group
        frm.add_custom_button(__("Gate Entry"), function() {
            frm.events.open_gate_entry_dialog(frm);
        }, __("Get Items From"));
    },

    // 🔥 OPEN DIALOG
    open_gate_entry_dialog: function(frm) {

        if (!frm.doc.supplier) {
            frappe.msgprint("Please select Supplier first");
            return;
        }
        
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.gate_entry.gate_entry.get_gate_entries_match_from_pi",
            args: {
                supplier: frm.doc.supplier
            },
            callback: function(r) {

                if (!r.message || !r.message.length) {
                    frappe.msgprint("No Gate Entry available");
                    return;
                }

                // ✅ Add serial number
                let original_data = r.message.map((d, i) => {
                    d.idx = i + 1;
                    return d;
                });

                let dialog = new frappe.ui.Dialog({
                    title: "Select Gate Entry",
                    size: "large",
                    fields: [

                        // 🔍 SEARCH
                        {
                            fieldname: "search_gate_entry",
                            fieldtype: "Data",
                            label: "Search Gate Entry",
                            placeholder: "Type Gate Entry ID...",
                            change: function() {

                                let value = dialog.get_value("search_gate_entry");

                                let filtered = original_data;

                                if (value) {
                                    filtered = original_data.filter(d => 
                                        d.name.toLowerCase().includes(value.toLowerCase())
                                    );
                                }

                                // ✅ Re-index serial number
                                filtered = filtered.map((d, i) => {
                                    d.idx = i + 1;
                                    return d;
                                });

                                dialog.fields_dict.gate_entry_table.df.data = filtered;
                                dialog.fields_dict.gate_entry_table.grid.refresh();
                            }
                        },

                        // 📋 TABLE
                        {
                            fieldname: "gate_entry_table",
                            fieldtype: "Table",
                            label: "Gate Entries",
                            cannot_add_rows: true,
                            cannot_delete_rows: true,
                            data: original_data,
                            fields: [

                                // 🔢 Serial No (small)
                                {
                                    fieldname: "idx",
                                    fieldtype: "Int",
                                    label: "#",
                                    in_list_view: 1,
                                    read_only: 1,
                                    columns: 1
                                },

                                // 🔥 Gate Entry (wide)
                                {
                                    fieldname: "name",
                                    fieldtype: "Link",
                                    options: "Gate Entry",
                                    label: "Gate Entry",
                                    in_list_view: 1,
                                    read_only: 1,
                                    columns: 3
                                },

                                {
                                    fieldname: "consignor",
                                    fieldtype: "Link",
                                    options: "Supplier",
                                    label: "Supplier",
                                    in_list_view: 1,
                                    read_only: 1
                                },
                                {
                                    fieldname: "transporter",
                                    fieldtype: "Link",
                                    options: "Supplier",
                                    label: "Transporter",
                                    in_list_view: 1,
                                    read_only: 1
                                }
                            ]
                        }
                    ],

                    // ✅ ACTION BUTTON
                    primary_action_label: "Get Items",
                    primary_action: function() {

                        let selected = dialog.fields_dict.gate_entry_table.grid.get_selected_children();

                        if (!selected.length) {
                            frappe.msgprint("Please select at least one row");
                            return;
                        }

                        frm.events.process_gate_entries(frm, selected);

                        dialog.hide();
                    }
                });

                dialog.show();

                // 🔥 REMOVE ADD BUTTONS + STYLE FIX
                setTimeout(() => {

                    let grid = dialog.fields_dict.gate_entry_table.grid;

                    // ❌ remove buttons
                    grid.wrapper.find('.grid-add-row').hide();
                    grid.wrapper.find('.grid-add-multiple-rows').hide();
                    grid.wrapper.find('.grid-upload').hide();

                    // 🎯 column width fix
                    grid.wrapper.find('[data-fieldname="idx"]').css({
                        "width": "50px",
                        "max-width": "50px"
                    });

                    grid.wrapper.find('[data-fieldname="name"]').css({
                        "width": "250px",
                        "min-width": "250px"
                    });

                }, 200);
            }
        });
    },

    // 🔥 PROCESS ITEMS
    process_gate_entries: function(frm, selected_rows) {

        // ✅ Validate single transporter
        let transporters = [...new Set(selected_rows.map(d => d.transporter))];

        if (transporters.length > 1) {
            frappe.throw("Multiple Transporters found!");
        }

        // ✅ Set Supplier
        frm.set_value("supplier", transporters[0]);

        // ✅ Clear old items
        frm.clear_table("items");

        selected_rows.forEach(ge => {

            if (!ge.transport_service_item) {
                frappe.throw(`Missing Service Item in ${ge.name}`);
            }

            let row = frm.add_child("items");

            row.item_code = ge.transport_service_item;
            row.item_name = ge.transport_service_item;
            row.uom = "Nos";
            row.qty = 1;

            // ✅ Direct rate from backend
            row.rate = ge.total_amount || 0;

            row.custom_gate_entry = ge.name;
        });

        frm.refresh_field("items");

        frappe.msgprint("Items added successfully");
    }

});

// added by mayuri
frappe.ui.form.on("Purchase Invoice", {
    async validate(frm) {
        console.clear();
        console.log("====== MULTI GRN DYNAMIC CHECK ======");

        let pr_list = [...new Set(
            (frm.doc.items || [])
                .map(d => d.purchase_receipt)
                .filter(Boolean)
        )];

        if (!pr_list.length) return;

        const company_data = await frappe.db.get_value("Company", frm.doc.company, ["round_off_account", "round_off_cost_center"]);
        const dynamic_account = company_data && company_data.message ? company_data.message.round_off_account : null;
        const dynamic_cost_center = company_data && company_data.message ? company_data.message.round_off_cost_center : null;

        if (!dynamic_account) {
            frappe.msgprint({
                title: __('Setup Required'),
                indicator: 'orange',
                message: __('Please set <b>Round Off Account</b> in Company Master for {0}', [frm.doc.company])
            });
            return;
        }

        let expected_grand = 0;
        for (let pr_name of pr_list) {
            let pr = await frappe.db.get_doc("Purchase Receipt", pr_name);
            expected_grand += flt(pr.grand_total, 2);
        }

        await frm.script_manager.trigger("calculate_taxes_and_totals");
        let pi_grand = flt(frm.doc.grand_total, 2);
        let diff = flt(expected_grand - pi_grand, 2);

        console.log("Expected Total:", expected_grand);
        console.log("Difference Found:", diff);

        let existing_row = (frm.doc.taxes || []).find(t => t.description === "GRN Adjustment");

        if (!existing_row) {
            let row = frm.add_child("taxes");
            row.charge_type = "Actual";
            row.account_head = dynamic_account; 
            row.description = "GRN Adjustment";
            row.tax_amount = 0; 
            row.cost_center = dynamic_cost_center || frm.doc.cost_center;
            
            frm.refresh_field("taxes");
            frappe.show_alert(__("Adjustment row added with 0 amount. Please update manually."), 5);
        }

        console.log("====== MATCH DONE ======");
    }
});