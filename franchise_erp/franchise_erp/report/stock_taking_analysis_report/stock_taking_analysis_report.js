frappe.query_reports["Stock Taking Analysis Report"] = {

    filters: [

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            width: 180,
            default: frappe.defaults.get_user_default("Company"),

            on_change: function(report) {

                // Clear dependent filters
                report.set_filter_value("warehouse", "");
                report.set_filter_value("stock_taking", "");

                // Refresh report with new company
                frappe.query_report.refresh();
            }
        },

        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse",
            width: 180,

            get_query: function() {

                let company =
                    frappe.query_report.get_filter_value("company");

                return {
                    filters: {
                        company: company
                    }
                };
            }
        },

        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
            width: 180
        },

        {
            fieldname: "stock_taking",
            label: __("Stock Taking"),
            fieldtype: "Link",
            options: "Stock Taking",
            width: 180,

            get_query: function() {

                let company =
                    frappe.query_report.get_filter_value("company");

                return {
                    filters: {
                        company: company
                    }
                };
            }
        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            width: 120,
            default: frappe.datetime.get_today()
        },

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            width: 120,
            default: frappe.datetime.get_today()
        },

        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nSubmitted\nCancelled",
            width: 150,
            // default: "Submitted"
        },

        {
            fieldname: "show_serial_no",
            label: __("Segregate Serial No"),
            fieldtype: "Check",
            default: 0
        }
    ]
};