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