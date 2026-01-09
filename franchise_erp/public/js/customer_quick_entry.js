frappe.provide("frappe.ui.form");

frappe.ui.form.CustomerQuickEntryForm = class CustomerQuickEntryForm extends frappe.ui.form.QuickEntryForm {

    setup() {
        // 🔥 Remove both from default mandatory
        this.mandatory = (this.mandatory || []).filter(
            f => !["custom_transporter", "custom_mobile_no_customer"].includes(f)
        );

        return super.setup();
    }

    render_dialog() {
        super.render_dialog();

        const company_field = this.dialog.fields_dict.custom_company;
        const transporter_field = this.dialog.fields_dict.custom_transporter;
        const mobile_field = this.dialog.fields_dict.custom_mobile_no_customer;

        if (!company_field || !transporter_field || !mobile_field) return;

        const set_required_fields = (company) => {
            if (!company) {
                transporter_field.df.reqd = 0;
                mobile_field.df.reqd = 0;

                transporter_field.refresh();
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

                    // ✅ FINAL RULE
                    transporter_field.df.reqd = is_group ? 1 : 0;
                    mobile_field.df.reqd = is_group ? 0 : 1;

                    transporter_field.refresh();
                    mobile_field.refresh();
                }
            });
        };

        // ✅ On dialog load
        set_required_fields(company_field.get_value());

        // 🔁 On company change
        company_field.df.onchange = () => {
            set_required_fields(company_field.get_value());
        };
    }
};
