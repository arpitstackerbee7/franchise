frappe.ui.form.on("Purchase Order", {
    refresh(frm) {

        if (frm.doc.docstatus !== 1) return;

        frm.add_custom_button(
            __("Incoming Logistics"),
            () => {
                frappe.new_doc("Incoming Logistics", {
                    purchase_no: frm.doc.name,   // ✅ Incoming Logistics fieldname
                    vendor: frm.doc.supplier    // ✅ Incoming Logistics fieldname
                });
            },
            __("Create")
        );
    }
});
