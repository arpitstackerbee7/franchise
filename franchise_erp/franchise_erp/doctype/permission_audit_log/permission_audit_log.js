frappe.ui.form.on("Permission Audit Log", {
    refresh(frm) {
        if (
            frm.doc.action === "DELETE" &&
            frm.doc.status === "Deleted"
        ) {
            frm.add_custom_button(
                __("Restore Permission"),
                function () {
                    frappe.confirm(
                        __(
                            "Restore this permission rule?"
                        ),
                        function () {
                            frappe.call({
                                method:
                                    "franchise_erp.custom.permission_audit.restore_permission",
                                args: {
                                    log_name: frm.doc.name,
                                },
                                freeze: true,
                                freeze_message:
                                    __("Restoring Permission..."),
                                callback(r) {
                                    if (
                                        r.message &&
                                        r.message.success
                                    ) {
                                        frappe.show_alert({
                                            message:
                                                r.message.message,
                                            indicator: "green",
                                        });

                                        frm.reload_doc();
                                    }
                                },
                            });
                        }
                    );
                }
            );
        }
    },
});