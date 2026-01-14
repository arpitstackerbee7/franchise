frappe.ui.form.on("Purchase Term Template", {
    refresh(frm) {
        (frm.doc.purchase_term_charges || []).forEach(row => {
            apply_charge_rules(frm, row);
        });
    }
});

frappe.ui.form.on("Purchase Term Charges", {
    charge_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // Reset dependent fields
        frappe.model.set_value(cdt, cdn, "apply_on", "");
        frappe.model.set_value(cdt, cdn, "value_type", "");

        apply_charge_rules(frm, row);
    }
});

function apply_charge_rules(frm, row) {
    const grid = frm.fields_dict.purchase_term_charges.grid;

    /* ---------------- APPLY ON RULES ---------------- */

    if (row.charge_type === "Rate Diff") {
        grid.update_docfield_property("apply_on", "options", ["Item"]);
        grid.update_docfield_property("apply_on", "read_only", 1);
        frappe.model.set_value(row.doctype, row.name, "apply_on", "Item");
    }

    if (row.charge_type === "Discount") {
        grid.update_docfield_property("apply_on", "options", ["Taxable Amount"]);
        grid.update_docfield_property("apply_on", "read_only", 1);
        frappe.model.set_value(row.doctype, row.name, "apply_on", "Taxable Amount");
    }

    /* ---------------- VALUE TYPE RULES ---------------- */

    if (["Rate Diff", "Freight"].includes(row.charge_type)) {
        grid.update_docfield_property("value_type", "options", ["Amount"]);
        grid.update_docfield_property("value_type", "read_only", 1);
        frappe.model.set_value(row.doctype, row.name, "value_type", "Amount");
    } else {
        // Restore default if needed
        grid.update_docfield_property(
            "value_type",
            "options",
            ["Amount", "Percentage"]
        );
        grid.update_docfield_property("value_type", "read_only", 0);
    }
}

frappe.ui.form.on("Purchase Term Template", {
    refresh(frm) {
        hide_add_row_after_render(frm);
    }
});

frappe.ui.form.on("Purchase Term Charges", {
    purchase_term_charges_add(frm) {
        hide_add_row_after_render(frm);
    },
    purchase_term_charges_remove(frm) {
        hide_add_row_after_render(frm);
    },
    charge_type(frm, cdt, cdn) {
        hide_add_row_after_render(frm);
    }
});

function hide_add_row_after_render(frm) {
    const max_rows = 3;

    // wait for grid re-render
    setTimeout(() => {
        const row_count = frm.doc.purchase_term_charges
            ? frm.doc.purchase_term_charges.length
            : 0;

        const grid = frm.fields_dict.purchase_term_charges.grid;

        if (row_count >= max_rows) {
            grid.wrapper.find(".grid-add-row").hide();
        } else {
            grid.wrapper.find(".grid-add-row").show();
        }
    }, 100);
}