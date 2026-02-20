frappe.ui.form.on("Incoming Logistics", {
        refresh(frm) {

        frm.set_query("transporter", () => ({
            filters: { is_transporter: 1 }
        }));

        frm.set_query("consignor", () => ({
            filters: [
                ["is_transporter", "=", 0],
                ["custom_is_agent", "=", 0],
                ["custom_gate_entry", "=", 1]
            ]
        }));

        // ==============================
        // FETCH ID BUTTON
        // ==============================
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Fetch ID"),
                () => open_incoming_mapper_by_type(frm),
                __("Get Items From")
            );
        }

        // ==============================
        // CREATE GATE ENTRY BUTTON
        // ==============================
        if (frm.doc.docstatus !== 1 || frm.doc.status === "Received") return;

        frm.add_custom_button(
            __("Create Gate Entry"),
            () => {

                if (!frm.doc.references || !frm.doc.references.length) {
                    frappe.throw("No references found");
                }

                const refs = frm.doc.references.map(r => ({
                    source_doctype: r.source_doctype,
                    source_name: r.source_name
                }));

                frappe.route_options = {
                    incoming_logistics: frm.doc.name,
                    owner_site: frm.doc.owner_site,
                    consignor: frm.doc.consignor,
                    transporter: frm.doc.transporter,
                    type: frm.doc.type,
                    references: refs
                };

                frappe.set_route("Form", "Gate Entry", "new-gate-entry");
            },
            __("Actions")
        );
    },

    // ✅ ONLY ONE TYPE EVENT
    type(frm) {
        toggle_consignor_customer_fields(frm);
        frm.clear_table("references");
        frm.refresh_field("references");
    },
    owner_site(frm) {
        if (frm.doc.owner_site) fetch_company_city(frm);
    },
    consignor(frm) {
        if (frm.doc.consignor) fetch_supplier_city(frm);
    },
    charged_weight(frm) {
        calculate_freight_and_total(frm);
    },
    rate(frm) {
        calculate_freight_and_total(frm);
    },
    others(frm) {
        calculate_total(frm);
    },
    freight(frm) {
        calculate_total(frm);
    },
    type(frm) {
        toggle_site_field(frm);
    },
    type: function(frm) {
        toggle_consignor_fields(frm);
    },
    to_pay(frm) {
        frm.trigger('toggle_pay_fields');
    },
    lr_date(frm) {
        validate_date_not_future(frm, "lr_date");
    },
    invoice_date(frm) {
        validate_date_not_future(frm, "invoice_date");
    },
    date(frm) {
        validate_date_not_future(frm, "date");
    },
    onload(frm) {
        if (frm.is_new()) {
            const today = frappe.datetime.get_today();
            frm.set_value("lr_date", today);
            frm.set_value("invoice_date", today);
            frm.set_value("date", today);
        }
    //     if (!frm.doc.to_pay) frm.set_value('to_pay', 'Yes');
    //     frm.trigger('toggle_pay_fields');
    //     toggle_site_field(frm);
    // },
    // toggle_pay_fields(frm) {
    //     const hide_fields = [
    //         'rate', 'actual_weight', 'charged_weight',
    //         'freight', 'others', 'declaration_amount', 'total_amount'
    //     ];
    //     const hide = frm.doc.to_pay === 'No';
    //     hide_fields.forEach(field => frm.set_df_property(field, 'hidden', hide));
    }
});

// ===================================================
// TYPE → DOCTYPE MAP
// ===================================================
const INCOMING_TYPE_MAP = {
    "Job Receipt": "Job Work Receipt",
    "Purchase": "Purchase Order",
    "Sales Return": "Sales Invoice",
    "Transfer IN": "Stock Entry",
    "WIP Return": "Stock Entry"
};


// ===================================================
// FETCH HANDLER
// ===================================================
function open_incoming_mapper_by_type(frm) {

    if (!frm.doc.type) frappe.throw("Please select Type first");
    if (!frm.doc.owner_site) frappe.throw("Please select Owner Site first");

    const map = {
        "Purchase": open_purchase_order_mapper,
        "Job Receipt": open_job_receipt_mapper
    };
    map[frm.doc.type]?.(frm);
    // map[frm.doc.type]?.(frm) || frappe.throw("Invalid Incoming Type");
}


// ===================================================
// PURCHASE ORDER
// ===================================================
function open_purchase_order_mapper(frm) {

    if (!frm.doc.consignor) {
        frappe.throw("Please select Supplier first");
    }

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Purchase Order",
        target: frm,
        setters: {
            supplier: frm.doc.consignor,
            company: frm.doc.owner_site
        },
        get_query() {
            return {
                filters: [
                    ["docstatus", "=", 1],
                    ["supplier", "=", frm.doc.consignor],
                    ["company", "=", frm.doc.owner_site]
                ]
            };
        },
        action(selections) {
            add_reference_rows(frm, selections);
            this.dialog.hide();
        }
    });
}


// ===================================================
// JOB RECEIPT
// ===================================================
function open_job_receipt_mapper(frm) {

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Job Work Receipt",
        target: frm,
        setters: {
            company: frm.doc.owner_site
        },
        get_query() {
            return {
                filters: [
                    ["docstatus", "=", 1],
                    ["company", "=", frm.doc.owner_site]
                ]
            };
        },
        action(selections) {
            add_reference_rows(frm, selections);
            this.dialog.hide();
        }
    });
}


// ===================================================
// ADD ROWS INTO `references` CHILD TABLE
// ===================================================
function add_reference_rows(frm, selections) {

    const source_doctype = INCOMING_TYPE_MAP[frm.doc.type];
    if (!source_doctype) frappe.throw("Invalid Type mapping");

    const existing = (frm.doc.references || []).map(
        r => `${r.source_doctype}::${r.source_name}`
    );

    selections.forEach(name => {

        const key = `${source_doctype}::${name}`;
        if (existing.includes(key)) return;

        let row = frm.add_child("references");
        row.source_doctype = source_doctype;
        row.source_name = name;
    });

    frm.refresh_field("references");
}


// ===================================================
// CONSIGNOR / CUSTOMER TOGGLE
// ===================================================
function toggle_consignor_customer_fields(frm) {

    const supplier_types = ["Purchase", "Job Receipt", "WIP Return"];
    const customer_types = ["Sales Return"];

    if (supplier_types.includes(frm.doc.type)) {
        frm.set_df_property("consignor", "hidden", 0);
        frm.set_df_property("customer", "hidden", 1);
        frm.set_value("customer", null);
    }
    else if (customer_types.includes(frm.doc.type)) {
        frm.set_df_property("customer", "hidden", 0);
        frm.set_df_property("consignor", "hidden", 1);
        frm.set_value("consignor", null);
    }
    else {
        frm.set_df_property("customer", "hidden", 1);
        frm.set_df_property("consignor", "hidden", 1);
    }
}




/* ---------------- COMPANY → station_to ---------------- */
async function fetch_company_city(frm) {
    const r = await frappe.call({
        method: "frappe.contacts.doctype.address.address.get_default_address",
        args: { doctype: "Company", name: frm.doc.owner_site }
    });

    if (r.message) {
        const addr = await frappe.db.get_value("Address", r.message, "custom_citytown");
        if (addr?.message?.custom_citytown) frm.set_value("station_to", addr.message.custom_citytown);
    }
}

/* ---------------- SUPPLIER → station_from ---------------- */
async function fetch_supplier_city(frm) {
    const r = await frappe.call({
        method: "frappe.contacts.doctype.address.address.get_default_address",
        args: { doctype: "Supplier", name: frm.doc.consignor }
    });

    if (r.message) {
        const addr = await frappe.db.get_value("Address", r.message, "custom_citytown");
        if (addr?.message?.custom_citytown) frm.set_value("station_from", addr.message.custom_citytown);
    }
}

function calculate_freight_and_total(frm) {
    let freight = flt(frm.doc.charged_weight) * flt(frm.doc.rate);
    frm.set_value('freight', freight);
    calculate_total(frm);
}

function calculate_total(frm) {
    let total = flt(frm.doc.freight) + flt(frm.doc.others);
    frm.set_value('total_amount', total);
}

function toggle_site_field(frm) {
    if (frm.doc.type === "Sales Return") {
        frm.set_df_property("site", "hidden", 0);
        frm.set_df_property("site", "reqd", 1);
    } else {
        frm.set_df_property("site", "hidden", 1);
        frm.set_df_property("site", "reqd", 0);
        frm.set_value("site", "");
    }
}

function validate_date_not_future(frm, fieldname) {
    if (frm.doc[fieldname] && frm.doc[fieldname] > frappe.datetime.get_today()) {
        frappe.msgprint({
            title: __("Invalid Date"),
            message: __("Future dates are not allowed. Today's date has been set automatically."),
            indicator: "red"
        });
        frm.set_value(fieldname, frappe.datetime.get_today());
    }
}



frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});



// frappe.ui.form.on("Incoming Logistics", {
//     validate(frm) {
//         if (!frm.doc.purchase_ids || frm.doc.purchase_ids.length === 0) {
//             frappe.msgprint({
//                 title: __("Validation Error"),
//                 message: __("Please add at least one Purchase Order before saving."),
//                 indicator: "red"
//             });

//             frappe.validated = false;
//         }
//     }
// });

frappe.ui.form.on("Incoming Logistics", {
    validate(frm) {
        if (!frm.doc.references || frm.doc.references.length === 0) {
            frappe.msgprint({
                title: __("Validation Error"),
                message: __("Please add at least one Purchase Id before saving."),
                indicator: "red"
            });

            frappe.validated = false;
        }
    }
});
function toggle_consignor_fields(frm) {
    if (!frm.doc.type) return;

    frappe.db.get_value(
        "Incoming Logistics Type",
        frm.doc.type,
        ["is_customer", "is_supplier"],
        function (r) {
            if (!r) return;

            // 👉 Customer case
            if (r.is_customer) {
                frm.set_df_property("consignor_customer", "hidden", 0);
                frm.set_df_property("consignor_customer", "reqd", 1);

                frm.set_df_property("consignor", "hidden", 1);
                frm.set_df_property("consignor", "reqd", 0);
                frm.set_value("consignor", null);
            }

            // 👉 Supplier case
            else if (r.is_supplier) {
                frm.set_df_property("consignor", "hidden", 0);
                frm.set_df_property("consignor", "reqd", 1);

                frm.set_df_property("consignor_customer", "hidden", 1);
                frm.set_df_property("consignor_customer", "reqd", 0);
                frm.set_value("consignor_customer", null);
            }

            // 👉 Safety fallback
            else {
                frm.set_df_property("consignor", "hidden", 1);
                frm.set_df_property("consignor_customer", "hidden", 1);
                frm.set_value("consignor", null);
                frm.set_value("consignor_customer", null);
            }
        }
    );
}
