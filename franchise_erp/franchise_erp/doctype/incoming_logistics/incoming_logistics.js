frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {
        frm.set_query("transporter", function() {
            return { filters: { is_transporter: 1 } };
        });

        frm.set_query("consignor", function() {
            return { 
                filters: [
                        ["is_transporter", "=", 0],
                        ["custom_is_agent", "=", 0],
                        ["custom_gate_entry", "=", 1]
                    ]
             };
        });

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Fetch ID "),
                () => open_purchase_order_mapper(frm),
                __("Get Items From")
            );
        }

        // Only show button for Submitted docs
        if (frm.doc.docstatus !== 1) return;
        if (frm.doc.status === "Received") return;

        frm.add_custom_button(
            __("Create Gate Entry"),
            function () {
                // Map all selected purchase orders
                const po_list = (frm.doc.purchase_ids || []).map(row => row.purchase_order);

                frappe.route_options = {
                    incoming_logistics: frm.doc.name,
                    owner_site: frm.doc.owner_site,
                    consignor: frm.doc.consignor,
                    transporter: frm.doc.transporter,
                    invoice_no: frm.doc.invoice_no,
                    type: frm.doc.type,
                    date: frm.doc.date,
                    gate_entry_box_barcode: frm.doc.gate_entry_box_barcode,
                    lr_quantity: frm.doc.lr_quantity,
                    purchase_orders: po_list, // send array of POs instead of single field
                    document_no: frm.doc.lr_document_no,
                    declaration_amount: frm.doc.declaration_amount,
                    purchase_ids :frm.doc.purchase_ids,
                    quantity_as_per_invoice: frm.doc.received_qty
                };

                frappe.set_route("Form", "Gate Entry", "new-gate-entry");
            },
            __("Actions")
        );
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
    },
     refresh: function(frm) {
        toggle_consignor_fields(frm);
    }
});

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

function open_purchase_order_mapper(frm) {
    if (!frm.doc.consignor) frappe.throw({ title: __("Mandatory"), message: __("Please select consignor first") });
    if (!frm.doc.owner_site) frappe.throw({ title: __("Mandatory"), message: __("Please select Owner Site first") });

   new frappe.ui.form.MultiSelectDialog({
    doctype: "Purchase Order",
    target: frm,
    setters: {
        supplier: frm.doc.consignor,
        company: frm.doc.owner_site
    },
    add_filters_group: 1,
    date_field: "transaction_date",
    columns: [
        { fieldname: "name", label: __("Purchase Order"), fieldtype: "Link", options: "Purchase Order" },
        "supplier", "company", "schedule_date"
    ],
    get_query() {
        return {
            filters: [
                ["Purchase Order", "docstatus", "=", 1],
                ["Purchase Order", "status", "=", "To Receive and Bill"],
                ["Purchase Order", "supplier", "=", frm.doc.consignor],
                ["Purchase Order", "company", "=", frm.doc.owner_site],

                // ✅ NEW CONDITION
                // ["Purchase Order Item", "custom_incoming_logistic", "is", "not set"]
            ]
        };
    },
  action(selections) {
    if (!selections || !selections.length) {
        frappe.msgprint(__("Please select at least one Purchase Order"));
        return;
    }

    // Get list of already added POs
    const existing_pos = (frm.doc.purchase_ids || []).map(r => r.purchase_order);

    selections.forEach(po => {
        // Add only if not already in table
        if (!existing_pos.includes(po)) {
            let row = frm.add_child("purchase_ids");
            row.purchase_order = po;
        }
    });

    frm.refresh_field("purchase_ids");
    this.dialog.hide();
}
    });
}

frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});



frappe.ui.form.on("Incoming Logistics", {
    validate(frm) {
        if (!frm.doc.purchase_ids || frm.doc.purchase_ids.length === 0) {
            frappe.msgprint({
                title: __("Validation Error"),
                message: __("Please add at least one Purchase Order before saving."),
                indicator: "red"
            });

            frappe.validated = false;
        }
    }
});

function toggle_consignor_fields(frm) {
    if (!frm.doc.type) {
        return;
    }

    frappe.db.get_value(
        "Incoming Logistics Type",
        frm.doc.type,
        "is_checked",
        function(r) {
            if (r && r.is_checked) {
                // ✅ If checkbox is checked
                frm.set_df_property("consignor_customer", "hidden", 0);
                frm.set_df_property("consignor_customer", "reqd", 1);

                frm.set_df_property("consignor", "hidden", 1);
                frm.set_df_property("consignor", "reqd", 0);

                frm.set_value("consignor", null);

            } else {
                // ❌ If checkbox is NOT checked
                frm.set_df_property("consignor_customer", "hidden", 1);
                frm.set_df_property("consignor_customer", "reqd", 0);

                frm.set_df_property("consignor", "hidden", 0);
                frm.set_df_property("consignor", "reqd", 1);

                frm.set_value("consignor_customer", null);
            }
        }
    );
}