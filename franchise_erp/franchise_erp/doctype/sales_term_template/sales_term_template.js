// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt


frappe.ui.form.on("Sales Term Template", {
    refresh(frm) {
        hide_add_row_after_render(frm);
    }
});

frappe.ui.form.on("Sales Term Charges", {
    sales_term_charges_add(frm) {
        hide_add_row_after_render(frm);
    },
    sales_term_charges_remove(frm) {
        hide_add_row_after_render(frm);
    },
    charge_type(frm, cdt, cdn) {
        hide_add_row_after_render(frm);
    }
});

function hide_add_row_after_render(frm) {
    const max_rows = 1;

    // wait for grid re-render
    setTimeout(() => {
        const row_count = frm.doc.sales_term_charges
            ? frm.doc.sales_term_charges.length
            : 0;

        const grid = frm.fields_dict.sales_term_charges.grid;

        if (row_count >= max_rows) {
            grid.wrapper.find(".grid-add-row").hide();
        } else {
            grid.wrapper.find(".grid-add-row").show();
        }
    }, 100);
}