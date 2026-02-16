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
            
            // 1. Hide Sections and Tabs (Using wrapper to prevent global leakage)
            const to_hide_sections = [
                'currency_and_price_list', 
                // 'section_break_49', 'taxes_section', 
                // 'section_break_41', 'totals', 
                'accounting_dimensions_section',
                // 'customer_po_details', 'sales_team_section_break', 'printing_details',
                // 'gst_section', 'address_and_contact_tab', 'terms_tab', 
                // 'more_info_tab', 'connections_tab'
            ];

            to_hide_sections.forEach(fieldname => {
                let field = frm.get_field(fieldname);
                if (field && field.wrapper) {
                    $(field.wrapper).hide(); 
                }
            });

            // 2. Hide Individual Fields (Including the Tax field you mentioned)
            const fields_to_hide = [
                'naming_series', 'posting_date', 'posting_time', 
                'set_posting_time', 'company', 'amended_from', 
                'is_return', 'set_warehouse',
                // 'total_taxes_and_charges',      // <--- Hides Total Taxes and Charges (INR)
                // 'base_total_taxes_and_charges'  // Hides base currency tax field
            ];
            
            fields_to_hide.forEach(f => {
                // Method 1: standard hiding
                frm.set_df_property(f, 'hidden', 1);
                // Method 2: Force hide using DOM for persistent fields
                $(`div[data-fieldname="${f}"]`).hide();
            });

            // 3. Hide Sidebar, Dashboard, Tabs and Footer (Scoped ONLY to this form)
            // frm.dashboard.hide();
            // $(frm.wrapper).find('.form-tabs').hide();
            // $(frm.wrapper).find('.form-sidebar').hide();
            // $(frm.wrapper).find('.form-footer').hide();

            // 4. Clean Items Table Columns
            let grid = frm.get_field("items").grid;
            grid.get_all_fields().forEach(df => {
                let show_list = ['item_code', 'qty', 'rate', 'discount_amount', 'amount'];
                if (!show_list.includes(df.fieldname)) {
                    grid.set_column_disp(df.fieldname, false);
                } else {
                    grid.set_column_disp(df.fieldname, true);
                }
            });

            frm.page.set_title("SIS Counter Sale");
        }
    },

    // Customer Mobile Number Search Logic
    custom_customer_mobile_number: function(frm) {
        let mobile_val = frm.doc.custom_customer_mobile_number;
        if (mobile_val && mobile_val.length >= 10) {
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
    }
});