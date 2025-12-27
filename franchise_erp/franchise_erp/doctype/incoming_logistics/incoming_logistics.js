// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Incoming Logistics", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {
        frm.set_query("transporter", function() {
            return {
                filters: {
                    is_transporter: 1
                }
            };
        });
    },

    refresh(frm) {
        frm.set_query("consignor", function() {
            return {
                filters: {
                    is_transporter: 0
                }
            };
        });
    },
    owner_site(frm) {
        if (frm.doc.owner_site) {
            fetch_company_city(frm);
        }
    },

    consignor(frm) {
        if (frm.doc.consignor) {
            fetch_supplier_city(frm);
        }
    }
});

/* ---------------- COMPANY → station_from ---------------- */
async function fetch_company_city(frm) {
    const r = await frappe.call({
        method: "frappe.contacts.doctype.address.address.get_default_address",
        args: {
            doctype: "Company",
            name: frm.doc.owner_site
        }
    });

    if (r.message) {
        const addr = await frappe.db.get_value(
            "Address",
            r.message,
            "custom_citytown"
        );

        if (addr?.message?.custom_citytown) {
            frm.set_value("station_from", addr.message.custom_citytown);
        }
    }
}

/* ---------------- SUPPLIER → station_to ---------------- */
async function fetch_supplier_city(frm) {
    const r = await frappe.call({
        method: "frappe.contacts.doctype.address.address.get_default_address",
        args: {
            doctype: "Supplier",
            name: frm.doc.consignor
        }
    });

    if (r.message) {
        const addr = await frappe.db.get_value(
            "Address",
            r.message,
            "custom_citytown"
        );

        if (addr?.message?.custom_citytown) {
            frm.set_value("station_to", addr.message.custom_citytown);
        }
    }
}
frappe.ui.form.on('Incoming Logistics', {

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
    }
});


function calculate_freight_and_total(frm) {

    let charged_weight = flt(frm.doc.charged_weight);
    let rate = flt(frm.doc.rate);

    let freight = charged_weight * rate;

    frm.set_value('freight', freight);

    calculate_total(frm);
}


function calculate_total(frm) {

    let freight = flt(frm.doc.freight);
    let others = flt(frm.doc.others);

    let total = freight + others;

    frm.set_value('total_amount', total);
}


frappe.ui.form.on('Incoming Logistics', {
    onload(frm) {
        const today = frappe.datetime.get_today();

        ['date', 'invoice_date', 'lr_date'].forEach(field => {

            // Default today
            if (!frm.doc[field]) {
                frm.set_value(field, today);
            }

            // Disable future dates in calendar
            frm.fields_dict[field].df.options = `max:${today}`;
            frm.fields_dict[field].refresh();
        });
    },
    onload(frm) {
        // default Yes agar blank ho
        if (!frm.doc.to_pay) {
            frm.set_value('to_pay', 'Yes');
        }
        frm.trigger('toggle_pay_fields');
    },

    to_pay(frm) {
        frm.trigger('toggle_pay_fields');
    },

    toggle_pay_fields(frm) {
        const hide_fields = [
            'rate',
            'actual_weight',
            'charged_weight',
            'freight',
            'others',
            'declaration_amount',
            'total_amount'
        ];

        const hide = frm.doc.to_pay === 'No';

        hide_fields.forEach(field => {
            frm.set_df_property(field, 'hidden', hide);
        });
    }
});

frappe.ui.form.on("Incoming Logistics", {

    type: function(frm) {
        toggle_site_field(frm);
    },

    onload: function(frm) {
        toggle_site_field(frm);
    }

});

function toggle_site_field(frm) {

    if (frm.doc.type === "Sales Return") {
        // show + mandatory
        frm.set_df_property("site", "hidden", 0);
        frm.set_df_property("site", "reqd", 1);
    } else {
        // hide + not mandatory
        frm.set_df_property("site", "hidden", 1);
        frm.set_df_property("site", "reqd", 0);
        frm.set_value("site", "");
    }
}



frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {

        // ✅ Sirf Submitted doc
        if (frm.doc.docstatus !== 1) return;

        // ❌ Agar status "Received" hai → button mat dikhao
        if (frm.doc.status === "Received") return;

        frm.add_custom_button(
            __("Create Gate Entry"),
            function () {

                frappe.route_options = {
                    incoming_logistics: frm.doc.name,
                    owner_site: frm.doc.owner_site,
                    consignor: frm.doc.consignor,
                    transporter: frm.doc.transporter,
                    invoice_no: frm.doc.invoice_no,
                    type: frm.doc.type,
                    date: frm.doc.date
                };

                frappe.set_route("Form", "Gate Entry", "new-gate-entry");
            },
            __("Actions")
        );
    },
    //  onload(frm) {
    //     if (frm.doc.incoming_logistics) {
    //         frm.set_df_property("incoming_logistics", "read_only", 1);
    //     }
    // }
});



frappe.ui.form.on("Incoming Logistics", {

    // Form load hote hi today set karo (only for new doc)
    onload(frm) {
        if (frm.is_new()) {
            const today = frappe.datetime.get_today();

            frm.set_value("lr_date", today);
            frm.set_value("invoice_date", today);
            frm.set_value("date", today);
        }
    },

    lr_date(frm) {
        validate_date_not_future(frm, "lr_date");
    },

    invoice_date(frm) {
        validate_date_not_future(frm, "invoice_date");
    },

    date(frm) {
        validate_date_not_future(frm, "date");
    }
});

// Reusable function
function validate_date_not_future(frm, fieldname) {
    if (frm.doc[fieldname]) {
        const today = frappe.datetime.get_today();

        if (frm.doc[fieldname] > today) {
            frappe.msgprint({
                title: __("Invalid Date"),
                message: __("Future dates are not allowed. Today's date has been set automatically."),
                indicator: "red"
            });

            frm.set_value(fieldname, today);
        }
    }
}



