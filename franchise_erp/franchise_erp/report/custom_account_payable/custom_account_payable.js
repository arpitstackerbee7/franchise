frappe.query_reports["Custom Account Payable"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "report_date",
            label: __("As On Date (Debit Entry)"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
           {
            fieldname: "credit_entry_date",
            label: __("As On Date (Credit Entry)"),
            fieldtype: "Date",
            default: "",
            },
            {
            fieldname: "credit_entry_voucher_types",
            label: __("Credit Entry Voucher Types"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const options = [
                    "Payment Entry",
                    "Purchase Invoice",
                    "Debit Note",
                    "Journal Entry",
                    "Purchase Order",
                    "OTHERS",
                ];
                return options
                    .filter(o => o.toLowerCase().includes((txt || "").toLowerCase()))
                    .map(o => ({ value: o, description: "" }));
            },
           },
        {
            fieldname: "ageing_based_on",
            label: __("Ageing Based On"),
            fieldtype: "Select",
            options: "Due Date\nPosting Date\nSupplier Invoice Date",
            default: "Due Date",
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Select",
            options: "\nSupplier\nCustomer\nEmployee\nShareholder\nStudent",
            default: "Supplier",
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                if (!frappe.query_report.filters) return;
                let party_type = frappe.query_report.get_filter_value("party_type");
                if (!party_type) return;
                return frappe.db.get_link_options(party_type, txt);
            },
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Supplier", txt);
            },
        },
       {
            fieldname: "supplier_group",
            label: __("Supplier Group"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Supplier Group", txt);
            },
        },
        {
            fieldname: "agent",
            label: __("Agent"),
            fieldtype: "Link",
            options: "Supplier",
            get_query: function() {
                // Only show suppliers marked as an Agent
                return {
                    filters: {
                        custom_is_agent: 1,
                    },
                };
            },
        },
        {
            fieldname: "payment_terms_template",
            label: __("Payment Terms Template"),
            fieldtype: "Link",
            options: "Payment Terms Template",
        },
        {
            fieldname: "payable_account",
            label: __("Payable Account"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Account", txt, {
                    account_type: "Payable",
                    company: frappe.query_report.get_filter_value("company"),
                });
            },
        },
        {
            fieldname: "group_by_party",
            label: __("Group By Party"),
            fieldtype: "Check",
            default: 0,
        },
        {
            fieldname: "based_on_payment_terms",
            label: __("Based On Payment Terms"),
            fieldtype: "Check",
            default: 0,
        },
        {
            fieldname: "show_future_payments",
            label: __("Show Future Payments"),
            fieldtype: "Check",
            default: 0,
        },
    ],

    formatter: function(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (!value) value = "&nbsp;";

    if (data && data.is_row_break) {
        return "";
    } else if (data && data.is_subtotal) {
        value = `<b style="display:block; background-color:#ffd6d6;">${value}</b>`;
    } else if (data && data.is_group) {
        value = `<span style="display:block; background-color:#e6e6e6; color:#555;">${value}</span>`;
    }
    return value;
},
};