// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt



frappe.ui.form.on("Outgoing Logistics", {
	refresh(frm) {
        frm.set_query("consignee_supplier", function() {
            return { 
                filters: [
                        ["is_transporter", "=", 0],
                        ["custom_is_agent", "=", 0],
                        ["custom_gate_entry", "=", 1]
                    ]
             };
        });
        // if (frm.doc.docstatus === 0) {
        //     frm.add_custom_button(
        //         __("Fetch Sales Invoice ID"),
        //         () => open_sales_invoice_mapper(frm),
        //         __("Get Items From")
        //     );
        // }
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Fetch ID"),
                () => open_mapper_by_type(frm),
                __("Get Items From")
            );
        }
	},
});

function open_mapper_by_type(frm) {

    if (!frm.doc.type) {
        frappe.throw(__("Please select Type first"));
    }

    if (!frm.doc.owner_site) {
        frappe.throw(__("Please select Owner Site first"));
    }

    const type_map = {
        "Sales Invoice": open_sales_invoice_mapper,
        "Job Order": open_job_order_mapper,
        "Purchase Return": open_purchase_return_mapper,
        "Stock Entry": open_stock_entry_mapper
    };

    if (!type_map[frm.doc.type]) {
        frappe.msgprint(__("Invalid Type selected"));
        return;
    }

    type_map[frm.doc.type](frm);
}
function open_sales_invoice_mapper(frm) {

    if (!frm.doc.consignee) {
        frappe.throw(__("Please select Consignee first"));
    }

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Sales Invoice",
        target: frm,
        setters: {
            customer: frm.doc.consignee,
            company: frm.doc.owner_site
        },
        get_query() {
            return {
                filters: [
                    ["Sales Invoice", "docstatus", "=", 1],
                    ["Sales Invoice", "custom_outgoing_logistics_reference", "is", "not set"],
                    ["Sales Invoice", "customer", "=", frm.doc.consignee],
                    ["Sales Invoice", "company", "=", frm.doc.owner_site]
                ]
            };
        },
        action(selections) {
            add_rows(frm, selections);
            this.dialog.hide();
        }
    });
}
function open_job_order_mapper(frm) { new frappe.ui.form.MultiSelectDialog({ doctype: "Subcontracting Order", target: frm, setters: { company: frm.doc.owner_site }, get_query() { let filters = [ ["Subcontracting Order", "docstatus", "=", 1], ["Subcontracting Order", "custom_outgoing_logistics_reference", "is", "not set"], ["Subcontracting Order", "company", "=", frm.doc.owner_site] ]; if (frm.doc.consignee) { filters.push(["Job Order", "customer", "=", frm.doc.consignee]); } if (frm.doc.supplier) { filters.push(["Job Order", "supplier", "=", frm.doc.supplier]); } return { filters }; }, action(selections) { add_rows(frm, selections); this.dialog.hide(); } }); }


function open_purchase_return_mapper(frm) {

    if (!frm.doc.consignee_supplier) {
        frappe.throw(__("Please select Supplier first"));
    }

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Purchase Receipt",
        target: frm,
        setters: {
            supplier: frm.doc.consignee_supplier,
            is_return: 1
        },
        get_query() {
            return {
                filters: [
                    ["Purchase Receipt", "is_return", "=", 1],
                    ["Purchase Receipt", "docstatus", "=", 1],
                    ["Purchase Receipt", "custom_outgoing_logistics_reference", "is", "not set"],
                    ["Purchase Receipt", "supplier", "=", frm.doc.consignee_supplier],
                    ["Purchase Receipt", "company", "=", frm.doc.owner_site]
                ]
            };
        },
        action(selections) {
            add_rows(frm, selections);
            this.dialog.hide();
        }
    });
}

function open_stock_entry_mapper(frm) {

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Stock Entry",
        target: frm,
        setters: {
            stock_entry_type: "Transfer Out"
        },
        get_query() {
            return {
                filters: [
                    ["Stock Entry", "docstatus", "=", 1],
                    ["Stock Entry", "stock_entry_type", "=", "Transfer Out"],
                    ["Stock Entry", "is_return", "=", 1],
                    ["Stock Entry", "custom_outgoing_logistics_reference", "is", "not set"],
                    ["Stock Entry", "company", "=", frm.doc.owner_site]
                ]
            };
        },
        action(selections) {
            add_rows(frm, selections);
            this.dialog.hide();
        }
    });
}

const TYPE_DOCTYPE_MAP = {
    "Sales Invoice": "Sales Invoice",
    "Job Order": "Subcontracting Order",
    "Purchase Return": "Purchase Receipt",
    "Stock Entry": "Stock Entry"
};
function add_rows(frm, selections) {

    if (!frm.doc.type) {
        frappe.throw(__("Please select Type first"));
    }

    const source_doctype = TYPE_DOCTYPE_MAP[frm.doc.type];

    if (!source_doctype) {
        frappe.throw(__("Invalid Type → Doctype mapping"));
    }

    const existing = (frm.doc.references || []).map(
        r => `${r.source_doctype}::${r.source_name}`
    );

    selections.forEach(name => {

        const key = `${source_doctype}::${name}`;

        if (!existing.includes(key)) {
            let row = frm.add_child("references");
            row.source_doctype = source_doctype;   // ✅ REAL doctype
            row.source_name = name;                // ✅ Document ID
        }
    });

    frm.refresh_field("references");
}



// function open_sales_invoice_mapper(frm) {
//     if (!frm.doc.consignee) frappe.throw({ title: __("Mandatory"), message: __("Please select consignee first") });
//     if (!frm.doc.owner_site) frappe.throw({ title: __("Mandatory"), message: __("Please select Owner Site first") });

//    new frappe.ui.form.MultiSelectDialog({
//     doctype: "Sales Invoice",
//     target: frm,
//     setters: {
//         customer: frm.doc.consignee,
//         company: frm.doc.owner_site
//     },
//     add_filters_group: 1,
//     date_field: "transaction_date",
//     columns: [  
//         { fieldname: "name", label: __("Sales Invoice"), fieldtype: "Link", options: "Sales Invoice" },
//         "supplier", "company"
//     ],
//     get_query() {
//         return {
//             filters: [
//                 ["Sales Invoice", "docstatus", "=", 1],
//                 ["Sales Invoice", "custom_outgoing_logistics_reference", "=", ""],
//                 ["Sales Invoice", "customer", "=", frm.doc.consignee],
//                 ["Sales Invoice", "company", "=", frm.doc.owner_site]
//             ]
//         };
//     },
//   action(selections) {
//     if (!selections || !selections.length) {
//         frappe.msgprint(__("Please select at least one Sales Invoice"));
//         return;
//     }

//     // Get list of already added POs
//     const existing_sis = (frm.doc.sales_invoice_no || []).map(r => r.sales_invoice);

//     selections.forEach(si => {
//         // Add only if not already in table
//         if (!existing_sis.includes(si)) {
//             let row = frm.add_child("sales_invoice_no");
//             row.sales_invoice = si;
//         }
//     });

//     frm.refresh_field("sales_invoice_no");
//     this.dialog.hide();
// }
//     });
// }

frappe.ui.form.on("Outgoing Logistics", {

    onload: function (frm) {
        // When doc is created from another document
        if (frm.doc.owner_site && !frm.doc.station_from) {
            set_station_from_company(frm);
        }

        if (frm.doc.consignee && !frm.doc.station_to) {
            set_station_to_customer(frm);
        }
    },

    // STATION FROM → COMPANY
    owner_site: function (frm) {
        set_station_from_company(frm);
    },

    // STATION TO → CUSTOMER
    consignee: function (frm) {
        set_station_to_customer(frm);
    },
    type: function(frm) {
        toggle_consignee_supplier_fields(frm);
    }
});


/* ------------------------------
   Helper functions
------------------------------ */

function set_station_from_company(frm) {
    if (!frm.doc.owner_site) {
        frm.set_value("station_from", "");
        return;
    }

    frappe.db.get_list("Address", {
        filters: [
            ["Dynamic Link", "link_doctype", "=", "Company"],
            ["Dynamic Link", "link_name", "=", frm.doc.owner_site]
        ],
        fields: ["name", "custom_citytown"],
        limit: 1
    }).then(addresses => {
        if (!addresses || !addresses.length) {
            frm.set_value("station_from", "");
            return;
        }

        frm.set_value(
            "station_from",
            addresses[0].custom_citytown || ""
        );
    });
}


function set_station_to_customer(frm) {
    if (!frm.doc.consignee) {
        frm.set_value("station_to", "");
        return;
    }

    frappe.db.get_value(
        "Customer",
        frm.doc.consignee,
        "customer_primary_address"
    ).then(r => {
        const address = r.message?.customer_primary_address;
        if (!address) return;

        frappe.db.get_value(
            "Address",
            address,
            "custom_citytown"
        ).then(addr => {
            if (addr.message?.custom_citytown) {
                frm.set_value(
                    "station_to",
                    addr.message.custom_citytown
                );
            }
        });
    });
}


frappe.ui.form.on("Outgoing Logistics", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});


frappe.ui.form.on("Outgoing Logistics", {
    document_no(frm) {
        toggle_mandatory_logic(frm);
    },

    before_save(frm) {
        // If Job Work Order is selected, skip validation
        if (frm.doc.document_no) {
            return;
        }

        const rows = frm.doc.sales_invoice_no || [];
        const has_sales_invoice = rows.some(row => row.sales_invoice);

        if (!has_sales_invoice) {
            frappe.throw(__(
                "At least one Sales Invoice is required to create Outgoing Logistics."
            ));
        }
    }
});

function toggle_consignee_supplier_fields(frm) {
    if (!frm.doc.type) return;

    frappe.db.get_value(
        "Outgoing Logistics Type",
        frm.doc.type,
        ["is_customer", "is_supplier"],
        function (r) {
            if (!r) return;

            // 👉 Customer case → show consignee
            if (r.is_customer) {
                frm.set_df_property("consignee", "hidden", 0);
                frm.set_df_property("consignee", "reqd", 1);

                frm.set_df_property("consignee_supplier", "hidden", 1);
                frm.set_df_property("consignee_supplier", "reqd", 0);
                frm.set_value("consignee_supplier", null);
            }

            // 👉 Supplier case → show consignee_supplier
            else if (r.is_supplier) {
                frm.set_df_property("consignee_supplier", "hidden", 0);
                frm.set_df_property("consignee_supplier", "reqd", 1);

                frm.set_df_property("consignee", "hidden", 1);
                frm.set_df_property("consignee", "reqd", 0);
                frm.set_value("consignee", null);
            }

            // 👉 Safety fallback
            else {
                frm.set_df_property("consignee", "hidden", 1);
                frm.set_df_property("consignee_supplier", "hidden", 1);
                frm.set_value("consignee", null);
                frm.set_value("consignee_supplier", null);
            }
        }
    );
}

frappe.ui.form.on('Outgoing Logistics', {

    refresh(frm) {
        set_outgoing_type(frm);
    },

    source_doctype(frm) {
        set_outgoing_type(frm);
    },

    source_document(frm) {
        set_outgoing_type(frm);
    }
});

function set_outgoing_type(frm) {

    if (!frm.doc.source_doctype) return;

    let type_map = {
        "Sales Invoice": "Sales Invoice",
        "Job Order": "Job Order",
        "Job Work Order": "Job Order",
        "Purchase Return": "Purchase Return",
        "Stock Entry": "Transfer Out"
    };

    let logistics_type = type_map[frm.doc.source_doctype];

    if (logistics_type) {
        frm.set_value("outgoing_logistics_type", logistics_type);
    }
}

frappe.ui.form.on("Outgoing Logistics", {
    type(frm) {
        frm.clear_table("sales_invoice_no");
        frm.refresh_field("sales_invoice_no");
    }
});
