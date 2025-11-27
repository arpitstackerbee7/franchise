frappe.ui.form.on('Sales Invoice Item', {
    item_code: function(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    },

    form_render: function(frm, cdt, cdn) {
        apply_discount_hide(frm, cdt, cdn);
    }
});

function apply_discount_hide(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (!row || !row.item_code) return;

    frappe.db.get_value(
        'Item',
        row.item_code,
        'custom_discount_not_allowed',
        function(r) {
            if (r && r.custom_discount_not_allowed == 1) {

                // ✅ Hide Fields
                frm.fields_dict['items'].grid.update_docfield_property('margin_type', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('margin_rate_or_amount', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('discount_percentage', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('discount_amount', 'hidden', 1);
                frm.fields_dict['items'].grid.update_docfield_property('distributed_discount_amount', 'hidden', 1);

            } else {

                // ✅ Show Fields Again
                frm.fields_dict['items'].grid.update_docfield_property('margin_type', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('margin_rate_or_amount', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('discount_percentage', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('discount_amount', 'hidden', 0);
                frm.fields_dict['items'].grid.update_docfield_property('distributed_discount_amount', 'hidden', 0);

            }

            frm.refresh_field('items');
        }
    );
}
