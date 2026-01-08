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