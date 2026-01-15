frappe.provide("frappe.ui.form");

frappe.ui.form.CustomerQuickEntryForm = class CustomerQuickEntryForm extends frappe.ui.form.QuickEntryForm {

    setup() {
        this.mandatory = (this.mandatory || []).filter(
            f => f !== "custom_mobile_no_customer"
        );

        return super.setup();
    }

    render_dialog() {
        super.render_dialog();

        const fields_to_hide = [
            "customer_type",
            "custom_transporter",
            "gst_category"
        ];

        fields_to_hide.forEach(fieldname => {
            const field = this.dialog.fields_dict[fieldname];
            if (field) {
                field.$wrapper.hide();   // sirf Quick Entry
            }

        
        });

        const company_field = this.dialog.fields_dict.custom_company;
        const mobile_field = this.dialog.fields_dict.custom_mobile_no_customer;

        if (!company_field || !mobile_field) return;

        const set_required_fields = (company) => {
            if (!company) {
                mobile_field.df.reqd = 0;
                mobile_field.refresh();
                return;
            }

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Company",
                    filters: { name: company },
                    fieldname: ["is_group"]
                },
                callback: (r) => {
                    const is_group = r?.message?.is_group || 0;

                    // Parent company (is_group = 1) → mobile NOT mandatory
                    // Normal company → mobile mandatory
                    mobile_field.df.reqd = is_group ? 0 : 1;
                    mobile_field.refresh();
                }
            });
        };

        // On dialog load
        set_required_fields(company_field.get_value());

        // On company change
        company_field.df.onchange = () => {
            set_required_fields(company_field.get_value());
        };

        const parent_only_fields = [
        "customer_group",
        "custom_agent",
        "default_price_list"
    ];

    const handle_parent_company_fields = (company) => {
        if (!company) {
            parent_only_fields.forEach(fname => {
                const field = this.dialog.fields_dict[fname];
                if (field) {
                    field.df.reqd = 0;
                    field.$wrapper.hide();
                    field.refresh();
                }
            });
            return;
        }

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Company",
                filters: { name: company },
                fieldname: ["is_group"]
            },
            callback: (r) => {
                const is_group = r?.message?.is_group || 0;

                parent_only_fields.forEach(fname => {
                    const field = this.dialog.fields_dict[fname];
                    if (!field) return;

                    if (is_group) {
                        field.$wrapper.show();
                        field.df.reqd = 1;
                    } else {
                        field.$wrapper.hide();
                        field.df.reqd = 0;
                    }
                    field.refresh();
                });
            }
        });
    };

    handle_parent_company_fields(company_field.get_value());

    // ⚠️ IMPORTANT:
    // onchange overwrite NA ho, isliye wrap karo
    const old_onchange = company_field.df.onchange;
    company_field.df.onchange = () => {
        if (old_onchange) old_onchange();
        handle_parent_company_fields(company_field.get_value());
    };

}
    
};
