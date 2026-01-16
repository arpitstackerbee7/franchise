frappe.ui.form.on("Supplier", {
    refresh(frm) {

        // ✅ Agent Supplier filter
        frm.set_query("custom_agent_supplier", () => {
            return {
                filters: {
                    custom_is_agent: 1
                }
            };
        });

        // ✅ Transporter Supplier filter
       
        frm.set_query("custom_transporter", function() {
            return {
                filters: {
                    is_transporter: 1
                }
            };
        });
    }
});

frappe.ui.form.on("Supplier", {
    setup(frm) {
        frm.set_query("custom_purchase_terms_template", function () {
            return {
                filters: {
                    active: 1
                }
            };
        });
    }
});

frappe.ui.form.on("Supplier", {
    onload(frm) {
        toggle_pan_mandatory(frm);
    },
    refresh(frm) {
        toggle_pan_mandatory(frm);
    },
    tax_withholding_category(frm) {
        toggle_pan_mandatory(frm);
    }
});

function toggle_pan_mandatory(frm) {
    const has_tds = !!frm.doc.tax_withholding_category;

    frm.set_df_property("pan", "reqd", has_tds ? 1 : 0);

    frm.refresh_field("pan");
}
