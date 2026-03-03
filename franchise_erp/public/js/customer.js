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
    onload(frm) {
        apply_company_credit_rules(frm);
        set_required_fields(frm);
        // toggle_parent_company_fields(frm);

    },
    onload_post_render(frm) {
        //  EDIT FULL FORM FIX
        set_required_fields(frm);
        apply_company_credit_rules(frm);
        // toggle_parent_company_fields(frm);

    },

    refresh(frm) {
        set_required_fields(frm);
        apply_company_credit_rules(frm);
        // toggle_parent_company_fields(frm);

    },

    custom_company(frm) {
        set_required_fields(frm);
        apply_company_credit_rules(frm);
        // toggle_parent_company_fields(frm);
    }
});



function set_required_fields(frm) {
    // 🔒 form / fields ready hone ke baad hi run ho

    if (!frm.doc.custom_company) {
        setTimeout(() => {

            frm.set_df_property("custom_mobile_no_customer", "reqd", 0);
            frm.toggle_display("custom_mobile_no_customer", 1);

            frm.refresh_field("custom_mobile_no_customer");
        }, 0);
        return;
    }

    frappe.db.get_value("Company", frm.doc.custom_company, "is_group")
        .then(r => {
            const is_group = r.message?.is_group;

            setTimeout(() => {

                frm.set_df_property(
                    "custom_mobile_no_customer",
                    "reqd",
                    is_group ? 0 : 1
                );
                frm.toggle_display("custom_mobile_no_customer", !is_group);

                frm.refresh_field("custom_mobile_no_customer");
            }, 0);
        });
}

function apply_company_credit_rules(frm) {
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

        // Parent field
        frm.set_df_property(
            "custom_credit_days",
            "reqd",
            d.custom_make_credit_days_mandatory ? 1 : 0
        );

        // Child table field
        if (frm.fields_dict.credit_limits) {
            frm.fields_dict.credit_limits.grid.update_docfield_property(
                "credit_limit",
                "reqd",
                d.custom_make_credit_limit_mandatory ? 1 : 0
            );
        }

        // Refresh fields to reflect reqd changes visually
        frm.refresh_field("custom_credit_days");
        frm.refresh_field("credit_limits");
    });
}


//validation for credit limit validation
frappe.ui.form.on("Customer", {
    onload(frm) {
        if (frm.is_new()) {
            auto_add_credit_limit_row(frm);
        }
    },

    refresh(frm) {
        auto_add_credit_limit_row(frm);
    }
});

function auto_add_credit_limit_row(frm) {
    if (!frm.doc.credit_limits || frm.doc.credit_limits.length === 0) {
        let row = frm.add_child("credit_limits");

        // Default company set karo
        row.company = frappe.defaults.get_default("Company");

        // credit_limit intentionally BLANK
        row.credit_limit = null;

        frm.refresh_field("credit_limits");
    }
}



frappe.ui.form.on("Customer", {
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

// function toggle_parent_company_fields(frm) {
//     if (!frm.doc.custom_company) {
//         ["customer_group", "agent", "default_price_list"].forEach(f => {
//             frm.set_df_property(f, "reqd", 0);
//             frm.refresh_field(f);
//         });
//         return;
//     }

//     frappe.db.get_value("Company", frm.doc.custom_company, "is_group")
//         .then(r => {
//             const is_group = r.message?.is_group || 0;

//             ["customer_group", "custom_agent", "default_price_list"].forEach(f => {
//                 frm.set_df_property(f, "reqd", is_group ? 1 : 0);
//                 frm.refresh_field(f);
//             });
//         });
// }

frappe.ui.form.on("Customer", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});


frappe.ui.form.on('Customer', {
    refresh(frm) {
        if (frm.doc.custom_company) {
            frm.trigger('check_company_counter_validation');
        }
    },

    custom_company(frm) {
        frm.trigger('check_company_counter_validation');
    },

    check_company_counter_validation(frm) {
        if (!frm.doc.custom_company) return;

        frappe.db.get_value(
            'Company',
            frm.doc.custom_company,
            'custom_disable_validation_for_counter'
        ).then(r => {
            const flag = r.message.custom_disable_validation_for_counter;

            frm.toggle_reqd('customer_group', flag);
            frm.toggle_reqd('custom_agent', flag);
            frm.toggle_reqd('default_price_list', flag);

            // Set defaults if validation disabled
            if (!flag) {
                frm.set_value('tax_category', 'In-State');

                // Set default price list = MRP
                frappe.db.get_value('Price List', {price_list_name: 'MRP'}, 'enabled').then(res => {
                    if (!res.message || res.message.enabled != 1) {
                        frappe.msgprint({
                            title: __('Invalid Price List'),
                            message: __('Please create and enable <b>MRP</b> Price List'),
                            indicator: 'red'
                        });
                        return;
                    }
                    if (!frm.doc.default_price_list) {
                        frm.set_value('default_price_list', 'MRP');
                    }
                });

                // Set default customer group = Retail
                frappe.db.get_value('Customer Group', {customer_group_name: 'Retail'}, 'name').then(res => {
                    if (!res.message) {
                        frappe.msgprint({
                            title: __('Invalid Customer Group'),
                            message: __('Please create <b>Retail</b> Customer Group'),
                            indicator: 'red'
                        });
                        return;
                    }
                    if (!frm.doc.customer_group) {
                        frm.set_value('customer_group', res.message.name);
                    }
                });
            }
        });
    }
});




