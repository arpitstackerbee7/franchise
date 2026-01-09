frappe.ui.form.on("Customer", {
    setup(frm) {
        // ✅ Agent filter
        frm.set_query("custom_agent", function () {
            return {
                filters: {
                    custom_is_agent: 1
                }
            };
        });

        // ✅ Transporter filter
        frm.set_query("custom_transporter", function () {
            return {
                filters: {
                    is_transporter: 1
                }
            };
        });
    }
});

frappe.ui.form.on("Customer", {
    custom_company(frm) {
        if (!frm.doc.custom_company) return;

        frappe.db.get_value(
            "Company",
            frm.doc.custom_company,
            [
                "custom_make_credit_days_mandatory",
                "custom_make_credit_limit_mandatory"
            ]
        ).then(r => {
            const d = r.message || {};

            // Parent fields
            frm.set_df_property(
                "custom_credit_days",
                "reqd",
                d.custom_make_credit_days_mandatory ? 1 : 0
            );

            // Child table
            if (frm.fields_dict.credit_limits) {
                frm.fields_dict.credit_limits.grid.update_docfield_property(
                    "credit_limit",
                    "reqd",
                    d.custom_make_credit_limit_mandatory ? 1 : 0
                );
            }
        });
    }
});



frappe.ui.form.on("Customer", {
    custom_company(frm) {
        set_required_fields(frm);
    },

    onload(frm) {
        set_required_fields(frm);
    }
});

function set_required_fields(frm) {
    if (!frm.doc.custom_company) {
        frm.set_df_property("custom_transporter", "reqd", 0);
        frm.set_df_property("custom_mobile_no_customer", "reqd", 0);
        return;
    }

    frappe.db.get_value("Company", frm.doc.custom_company, "is_group")
        .then(r => {
            const is_group = r.message.is_group;

            frm.set_df_property("custom_transporter", "reqd", is_group ? 1 : 0);
            frm.set_df_property("custom_mobile_no_customer", "reqd", is_group ? 0 : 1);
        });
}
