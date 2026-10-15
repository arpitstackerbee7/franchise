// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Purchase Receipt Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "supplier_group",
            label: __("Supplier Group"),
            fieldtype: "Link",
            options: "Supplier Group"
        },
        {
            fieldname: "supplier_agent",
            label: __("Supplier Agent"),
            fieldtype: "Link",
            options: "Supplier",
            get_query: function () {
                return {
                    filters: {
                        custom_is_agent: 1
                    }
                };
            }
        }
    ]
};