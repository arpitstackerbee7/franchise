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
            if (this.dialog.fields_dict[fieldname]) {
                this.dialog.set_df_property(fieldname, "hidden", 1);
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
    }
};
