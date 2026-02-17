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

    // Logic: Enter Mobile Number -> Search & Select Customer
    /* custom_customer_mobile_number: function(frm) {
        let mobile_val = frm.doc.custom_customer_mobile_number;
        if (mobile_val && mobile_val.length >= 10 && !frm.doc.customer) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Customer",
                    filters: { "custom_mobile_no_customer": mobile_val }, 
                    fieldname: ["name", "customer_name"]
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('customer', r.message.name);
                        frappe.show_alert({message: __("Customer Found"), indicator: 'green'});
                    } else {
                        frappe.confirm(__("Customer with mobile {0} not found. Create new?", [mobile_val]), 
                            function() {
                                frappe.new_doc('Customer', { "custom_mobile_no_customer": mobile_val });
                            }
                        );
                    }
                }
            });
        }
    }, */

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