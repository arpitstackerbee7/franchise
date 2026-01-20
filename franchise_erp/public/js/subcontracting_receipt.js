frappe.ui.form.on("Subcontracting Receipt", {
    refresh(frm) {
        // sirf submitted document ke liye
        if (frm.doc.docstatus !== 1 || !frm.doc.supplier) return;

        // Supplier master se custom_gate_out_applicable check
        frappe.db.get_value(
            "Supplier",
            frm.doc.supplier,
            "custom_gate_out_applicable",
            (r) => {
                if (r && r.custom_gate_out_applicable) {
                    // ✅ sirf tab button dikhega
                    frm.add_custom_button(
                        __("Incoming Logistics"),
                        () => {
                            frappe.call({
                                method: "franchise_erp.custom.subcontracting_receipt.create_incoming_logistics_from_scr",
                                args: {
                                    subcontracting_receipt: frm.doc.name
                                },
                                callback: function (res) {
                                    if (res.message) {
                                        const doc = frappe.model.sync(res.message)[0];
                                        frappe.set_route("Form", doc.doctype, doc.name);
                                    }
                                }
                            });
                        },
                        __("Create")
                    );
                }
            }
        );
    }
});

frappe.ui.form.on("Subcontracting Receipt", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});