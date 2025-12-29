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
        frm.set_query("custom_transporter_supplier", () => {
        frm.set_query("custom_transporter", function() {
            return {
                filters: {
                    is_transporter: 1
                }
            };
        });
    }
});
});
