frappe.ui.form.on("Bulk Update HSN SAC and Tax Categories", {

    refresh(frm) {

        frm.add_custom_button("Update GST HSN Code", function () {

            // Validate HSN Code selected
         
            frappe.prompt(
                [
                    {
                        label: "Company",
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        reqd: 1,
                        get_query: function () {
                            return {
                                filters: {
                                    is_group: 0
                                }
                            };
                        }
                    }
                ],

                function(values) {

                   frappe.call({
    method: "franchise_erp.custom.company_tax_sync.update_gst_hsn_code_taxes",
    args: {
        docname: frm.doc.name,
        company: values.company
    },
    freeze: true,
    freeze_message: "Updating GST HSN Code Taxes...",
    callback: function(r) {
        if (r.message) {
            frappe.msgprint({
                title: "Success",
                message: r.message,
                indicator: "green"
            });
        }
    }
});

                },

                "Select Company"
            );

        });

    }

});