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
        // Apply minimal UI for SIS Counter Role
        if (frappe.user.has_role('SIS Counter')) {
            apply_sis_counter_minimal_ui(frm);
        }
    },

    // Logic: Enter Mobile Number -> Search & Select Customer
    // custom_customer_mobile_number: function(frm) {
    //     let mobile_val = frm.doc.custom_customer_mobile_number;
    //     if (mobile_val && mobile_val.length >= 10 && !frm.doc.customer) {
    //         frappe.call({
    //             method: "frappe.client.get_value",
    //             args: {
    //                 doctype: "Customer",
    //                 filters: { "custom_mobile_no_customer": mobile_val }, 
    //                 fieldname: ["name", "customer_name"]
    //             },
    //             callback: function(r) {
    //                 if (r.message) {
    //                     frm.set_value('customer', r.message.name);
    //                     frappe.show_alert({message: __("Customer Found"), indicator: 'green'});
    //                 } else {
    //                     frappe.confirm(__("Customer with mobile {0} not found. Create new?", [mobile_val]), 
    //                         function() {
    //                             frappe.new_doc('Customer', { "custom_mobile_no_customer": mobile_val });
    //                         }
    //                     );
    //                 }
    //             }
    //         });
    //     }
    // },

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
        'currency_and_price_list',       // Currency and Price List
        'section_break_49',              // Additional Discount
        'taxes_section',                 // Sales Taxes and Charges Section
        'accounting_dimensions_section', // Accounting Dimensions
        'gst_section',                   // GST Details
        'section_break_41',              // Tax Breakup
        'customer_po_details',           // PO Details
        'sales_team_section_break',      // Commission
        'printing_details'               // Print Settings
    ];

    // 2. Individual Fields to Hide (Including Total Taxes)
    const fields_to_hide = [
        'naming_series', 
        // 'posting_date', 
        'posting_time', 
        'set_posting_time', 'company', 'amended_from', 
        'is_return', 
        // 'set_warehouse', 
        'tax_id',
        'total_taxes_and_charges',       // <--- Hides Total Taxes and Charges (INR)
        'base_total_taxes_and_charges'   // Hides base currency tax total
    ];

    // Apply Hiding via JavaScript and Forceful CSS
    sections_to_hide.forEach(sec => {
        frm.set_df_property(sec, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${sec}"]`).attr('style', 'display: none !important');
    });

    fields_to_hide.forEach(field => {
        frm.set_df_property(field, 'hidden', 1);
        $(frm.wrapper).find(`div[data-fieldname="${field}"]`).hide();
    });

    // 3. Keep Items Table Clean
    let grid = frm.get_field("items").grid;
    grid.get_all_fields().forEach(df => {
        let show_list = ['item_code', 'qty', 'rate', 'discount_amount', 'amount'];
        grid.set_column_disp(df.fieldname, show_list.includes(df.fieldname));
    });

   
    // Set Page Title
    frm.page.set_title("SIS Counter Sale");
}