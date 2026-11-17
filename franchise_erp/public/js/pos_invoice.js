function fe_is_gst(row) {
    const h = (row.account_head || "").toUpperCase();
    return ["CGST", "SGST", "IGST", "CESS"].some(k => h.includes(k));
}

async function fe_apply_pos_tax(frm) {
    if (frm.__fe_busy || frm.doc.docstatus !== 0) return;
    if (!(frm.doc.taxes || []).length) return;
    frm.__fe_busy = true;
    try {
        let changed = false;
        (frm.doc.taxes || []).forEach(t => {
            if (fe_is_gst(t)) {
                if (t.charge_type !== "On Net Total" || !t.included_in_print_rate || t.row_id) {
                    t.charge_type = "On Net Total";
                    t.row_id = null;
                    t.included_in_print_rate = 1;
                    changed = true;
                }
            } else if (t.included_in_print_rate) {
                t.included_in_print_rate = 0;
                changed = true;
            }
        });

        if (changed) {
            frm.refresh_field("taxes");
            await frm.cscript.calculate_taxes_and_totals();
        }

        // Single payment row ko grand total se sync (return me negative bhi)
        const pays = frm.doc.payments || [];
        if (pays.length === 1) {
            const total = flt(frm.doc.rounded_total || frm.doc.grand_total);
            if (flt(pays[0].amount) !== total) {
                pays[0].amount = total;
                pays[0].base_amount = total * flt(frm.doc.conversion_rate || 1);
                frm.doc.paid_amount = total;
                frm.doc.base_paid_amount = pays[0].base_amount;
                frm.refresh_field("payments");
                frm.refresh_field("paid_amount");
            }
        }
    } finally {
        frm.__fe_busy = false;
    }
}

// Items/taxes badalne ke baad ERPNext ki calculation khatam hone do, phir apply karo
function fe_schedule(frm) {
    clearTimeout(frm.__fe_t);
    frm.__fe_t = setTimeout(() => fe_apply_pos_tax(frm), 600);
}

frappe.ui.form.on("POS Invoice", {
    onload_post_render: fe_schedule,
    refresh: fe_schedule,
    taxes_and_charges: fe_schedule,
    pos_profile: fe_schedule,
    items_remove: fe_schedule,
    discount_amount: fe_schedule,
    additional_discount_percentage: fe_schedule,
});

frappe.ui.form.on("POS Invoice Item", {
    item_code: (frm) => fe_schedule(frm),
    qty: (frm) => fe_schedule(frm),
    rate: (frm) => fe_schedule(frm),
    discount_percentage: (frm) => fe_schedule(frm),
    discount_amount: (frm) => fe_schedule(frm),
});