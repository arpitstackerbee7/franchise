frappe.ui.form.on("Sales Order", {
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

frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        if (!frm.doc.customer || frm.doc.docstatus !== 1) return;

        frappe.db.get_value(
            "Customer",
            frm.doc.customer,
            "custom_outgoing_logistics_applicable"
        ).then(r => {
            if (r.message?.custom_outgoing_logistics_applicable) {
                frm.add_custom_button(
                    __("Outgoing Logistics"),
                    () => {
                        frappe.new_doc("Outgoing Logistics", {
                            sales_order_no: frm.doc.name,
                            consignee: frm.doc.customer,
                            owner_site: frm.doc.company
                        });
                    },
                    __("Create")
                );
            }
        });
    }
});