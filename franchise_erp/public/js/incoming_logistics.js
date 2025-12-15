frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {
        frm.set_query("transporter", function() {
            return {
                filters: {
                    is_transporter: 1
                }
            };
        });
    }
});

frappe.ui.form.on("Incoming Logistics", {
    refresh(frm) {

        if (!frm.is_new()) {

            frm.add_custom_button("Create Gate Entry", function() {

                // Pass values to new Gate Entry using route_options
                frappe.route_options = {
                    incoming_logistics: frm.doc.name,
                    owner_site: frm.doc.owner_site,
                    consignor: frm.doc.consignor,
                    transporter: frm.doc.transporter,
                    invoice_no: frm.doc.invoice_no,
                    type: frm.doc.type,
                    date: frm.doc.date,
                };

                frappe.set_route("Form", "Gate Entry", "new-gate-entry");

            }, "Actions");
        }
    }
});
