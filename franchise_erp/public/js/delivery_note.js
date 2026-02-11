frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        frm.set_df_property("title", "read_only", 1);
    }
});

frappe.ui.form.on('Delivery Note', {
    company: function(frm) {
        if (!frm.doc.company) return;

        frappe.db.get_value(
            'SIS Configuration',
            { company: frm.doc.company },
            'delivery_note_warehouse'
        ).then(r => {
            if (r && r.message && r.message.delivery_note_warehouse) {
                frm.set_value(
                    'set_warehouse',
                    r.message.delivery_note_warehouse
                );
            }
        });
    },

    onload: function(frm) {
        if (frm.doc.company && !frm.doc.set_warehouse) {
            frm.trigger('company');
        }
    }
});
