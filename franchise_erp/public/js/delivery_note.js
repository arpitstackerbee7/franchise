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


frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        // SIS Counter Role Check
        if (frappe.user.has_role('SIS Counter')) {
            apply_sis_counter_minimal_ui(frm);
        }
    },

   

    // Handle re-rendering when customer is selected
    customer: function(frm) {
        if (frappe.user.has_role('SIS Counter')) {
            setTimeout(() => { apply_sis_counter_minimal_ui(frm); }, 500);
        }
    }
});

function apply_sis_counter_minimal_ui(frm) {
    // 1. Sections to Hide (Internal names from Customize Form JSON)
    const sections_to_hide = [
        'currency_and_price_list',
        'section_break_49',
        'taxes_section',
        'accounting_dimensions_section',
        'gst_section',
        'section_break_41',
        'customer_po_details',
        'sales_team_section_break',
        'printing_details'
    ];

    // 2. Individual Fields to Hide
    const fields_to_hide = [
        'naming_series',
        'posting_time',
        'set_posting_time', 'company', 'amended_from',
        'is_return',
        'tax_id',
        'total_taxes_and_charges',
        'base_total_taxes_and_charges'
    ];

    // Apply Hiding for sections
    sections_to_hide.forEach(sec => {
        frm.set_df_property(sec, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${sec}"]`).attr('style', 'display: none !important');
    });

    // Apply Hiding for fields
    fields_to_hide.forEach(field => {
        frm.set_df_property(field, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${field}"]`).hide();
    });

    // 3. Clean Items Table - FIX: Changed get_all_fields to docfields
    let grid = frm.get_field("items").grid;
    let show_list = ['item_code', 'qty', 'rate', 'discount_amount', 'amount'];

    if (grid && grid.docfields) {
        grid.docfields.forEach(df => {
            grid.set_column_disp(df.fieldname, show_list.includes(df.fieldname));
        });
        grid.refresh();
    }

    // Set simplified page title
    frm.page.set_title("SIS Counter Sale");
}


