// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt
frappe.query_reports["Sales Trend"] = {
    filters: [
        {
            fieldname: "fiscal_year",
            label: "Fiscal Year",
            fieldtype: "Link",
            options: "Fiscal Year",
            default: frappe.defaults.get_user_default("fiscal_year"),
            reqd: 0
        }
    ]
};