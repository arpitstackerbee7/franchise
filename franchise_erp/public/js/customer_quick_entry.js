frappe.provide("frappe.ui.form");

if (!frappe.ui.form.CustomerQuickEntryForm.is_overridden) {

    frappe.ui.form.CustomerQuickEntryForm = class CustomerQuickEntryForm extends frappe.ui.form.QuickEntryForm {

        render_dialog() {

            const allowed_fields = [
                "customer_name",
                "custom_company",
                "custom_date_of_birth",
                "custom_anniversary_date",
                "custom_mobile_no_customer",
                "customer_group",
                "custom_agent",
                "default_price_list",
                "custom_company_abbrevation"
            ];

            this.fields = this.fields.filter(df => allowed_fields.includes(df.fieldname));

            super.render_dialog();

            setTimeout(() => {
                if (this.dialog) {
                    this.dialog.set_primary_action(__('Save'), async () => {
                        await this.save();
                        if (this.dialog) {
                            this.dialog.hide();
                        }
                    });

                    this.dialog.get_primary_btn().text(__('Save'));
                }
            }, 100);
            

            if (this.dialog.fields_dict.custom_company_abbrevation) {
                this.dialog.fields_dict.custom_company_abbrevation.$wrapper.hide();
            }

            this.init_custom_logic();
        }

        init_custom_logic() {

            const f = this.dialog.fields_dict;
            if (!f.custom_company) return;

            const handle_logic = (company) => {

                if (!company) return;

                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Company",
                        filters: { name: company },
                        fieldname: "is_group"
                    },
                    callback: (r) => {

                        const is_group = r.message?.is_group || 0;

                        if (f.custom_mobile_no_customer) {
                            f.custom_mobile_no_customer.df.reqd = is_group ? 0 : 1;
                            f.custom_mobile_no_customer.refresh();
                        }

                        const p_fields = [
                            "customer_group",
                            "custom_agent",
                            "default_price_list"
                        ];

                        p_fields.forEach(fname => {
                            const field = f[fname];
                            if (field) {
                                is_group ? field.$wrapper.show() : field.$wrapper.hide();
                                field.df.reqd = is_group ? 1 : 0;
                                field.refresh();
                            }
                        });

                    }
                });
            };

            handle_logic(f.custom_company.get_value());

            f.custom_company.df.onchange = () => {
                handle_logic(f.custom_company.get_value());
            };
        }
    };

    frappe.ui.form.quick_entry_callbacks["Customer"] = frappe.ui.form.CustomerQuickEntryForm;

    frappe.ui.form.CustomerQuickEntryForm.is_overridden = true;
}