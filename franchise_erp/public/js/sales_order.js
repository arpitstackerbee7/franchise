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
