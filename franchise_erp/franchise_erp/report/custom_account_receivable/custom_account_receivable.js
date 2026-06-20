frappe.query_reports["Custom Account Receivable"] = {
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
            label: __("As On Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
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
            options: "\nCustomer\nSupplier\nEmployee\nShareholder\nStudent",
            default: "Customer",
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
            fieldname: "group_by_party",
            label: __("Group By Party"),
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

        if (data && data.is_subtotal) {
            value = `<b>${value || ""}</b>`;
        } else if (data && data.is_group) {
            value = `<span style="color:#6c757d;">${value || ""}</span>`;
        }

        return value;
    },
};