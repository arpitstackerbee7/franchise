frappe.ui.form.on("Subcontracting Order", {
    refresh(frm) {
        if (frm.doc.docstatus !== 0) {
            return;
        }

        set_all_item_tax_templates(frm);

        if (
            frm.doc.purchase_order &&
            frm.doc.company &&
            !frm.doc.taxes_and_charges
        ) {
            set_taxes_and_charges(frm);
        }
         // 🛑 1. Unsaved / New document guard
        if (frm.is_new()) return;

        // 🛑 2. Only Draft documents with Supplier
        if (frm.doc.docstatus !== 0 || !frm.doc.supplier) return;

        // 🧹 3. Prevent duplicate buttons
        frm.remove_custom_button(__('Outgoing Logistics'), __('Create'));

        // 🔍 4. Check if submitted Stock Entry exists
        frappe.db.get_value(
            "Stock Entry",
            {
                subcontracting_order: frm.doc.name,
                docstatus: 1
            },
            "name"
        ).then(se => {

            // ❌ No Stock Entry → no button
            if (!se.message) return;

            // 🔍 5. Check Supplier flag
            frappe.db.get_value(
                "Supplier",
                frm.doc.supplier,
                "custom_gate_out_applicable"
            ).then(r => {

                if (!r.message || !r.message.custom_gate_out_applicable) return;

                // ➕ 6. Add Create → Outgoing Logistics button
                frm.add_custom_button(
                    __('Outgoing Logistics'),
                    () => {
                        frappe.call({
                            method: "franchise_erp.custom.subcontracting_order.get_outgoing_logistics_data",
                            args: {
                                subcontracting_order: frm.doc.name
                            },
                            freeze: true,
                            callback(res) {
                                if (res.message) {
                                    frappe.new_doc("Outgoing Logistics", res.message);
                                }
                            }
                        });
                    },
                    __('Create')
                );
            });
        });
    },

    purchase_order(frm) {
        if (frm.doc.purchase_order && frm.doc.company) {
            set_taxes_and_charges(frm);
        }
    },

    company(frm) {
        if (!frm.doc.company) {
            return;
        }

        set_all_item_tax_templates(frm);

        if (frm.doc.purchase_order) {
            set_taxes_and_charges(frm);
        }
    }
});


frappe.ui.form.on("Subcontracting Order Item", {
    item_code(frm, cdt, cdn) {
        set_item_tax_template(frm, cdt, cdn);
    },

    rate(frm, cdt, cdn) {
        set_item_tax_template(frm, cdt, cdn);
    }
});


function set_all_item_tax_templates(frm) {
    (frm.doc.items || []).forEach(row => {
        if (row.item_code) {
            set_item_tax_template(
                frm,
                row.doctype,
                row.name
            );
        }
    });
}


function set_item_tax_template(frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (!row) {
        return;
    }

    if (!row.item_code || !frm.doc.company) {
        if (row.item_tax_template) {
            frappe.model.set_value(
                cdt,
                cdn,
                "item_tax_template",
                ""
            );
        }

        return;
    }

    frappe.call({
        method:
            "franchise_erp.event.subcontracting_order.get_item_tax_template",

        args: {
            item_code: row.item_code,
            rate: row.rate || 0,
            company: frm.doc.company
        },

        callback(r) {
            const template = r.message || "";

            if (template !== row.item_tax_template) {
                frappe.model.set_value(
                    cdt,
                    cdn,
                    "item_tax_template",
                    template
                );
            }
        }
    });
}


function set_taxes_and_charges(frm) {
    if (!frm.doc.purchase_order || !frm.doc.company) {
        return;
    }

    frappe.call({
        method:
            "franchise_erp.event.subcontracting_order.get_job_work_order_taxes_and_charges",

        args: {
            purchase_order: frm.doc.purchase_order,
            company: frm.doc.company
        },

        callback(r) {
            const template = r.message;

            if (
                template &&
                template !== frm.doc.taxes_and_charges
            ) {
                frm.set_value(
                    "taxes_and_charges",
                    template
                );
            }
        }
    });
}





