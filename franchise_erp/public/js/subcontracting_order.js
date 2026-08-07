frappe.ui.form.on("Subcontracting Order", {
    refresh(frm) {
       
        frm.add_custom_button(
            __("Fabric Wastage Register"),
            function () {
                frappe.new_doc("Fabric Wastage Register", {
                    subcontracting_order: frm.doc.name,
                    company: frm.doc.company,
                    supplier: frm.doc.supplier
                });
            },
            __("Create")
        );
        
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
        } else {
            set_tax_rows_on_net_total(frm);
        }


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
    },

    taxes_and_charges(frm) {
        setTimeout(() => {
            set_tax_rows_on_net_total(frm);
        }, 500);
    },

    validate(frm) {
        set_tax_rows_on_net_total(frm);
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
            "franchise_erp.custom.subcontracting_order.get_item_tax_template",

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
            "franchise_erp.custom.subcontracting_order.get_job_work_order_taxes_and_charges",

        args: {
            purchase_order: frm.doc.purchase_order,
            company: frm.doc.company
        },

        callback(r) {
            const template = r.message;

            if (!template) {
                return;
            }

            if (template !== frm.doc.taxes_and_charges) {
                frm.set_value("taxes_and_charges", template)
                    .then(() => {
                        setTimeout(() => {
                            set_tax_rows_on_net_total(frm);
                        }, 500);
                    });
            } else {
                set_tax_rows_on_net_total(frm);
            }
        }
    });
}


function set_tax_rows_on_net_total(frm) {
    if (!frm.doc.taxes || !frm.doc.taxes.length) {
        return;
    }

    let changed = false;

    frm.doc.taxes.forEach(row => {
        if (
            row.charge_type === "Actual" ||
            row.charge_type === "On Previous Row Total"
        ) {
            row.charge_type = "On Net Total";
            changed = true;
        }
    });

    if (changed) {
        frm.refresh_field("taxes");
    }
}

frappe.ui.form.on('Subcontracting Order', {
    refresh(frm) {

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
    }
});




