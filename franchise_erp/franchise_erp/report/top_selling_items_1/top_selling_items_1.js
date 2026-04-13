// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.query_reports["Top Selling Items 1"] = {
//     "filters": [
//         {
//             "fieldname": "limit",
//             "label": "Top N Items",
//             "fieldtype": "Int",
//             "default": 10
//         }
//     ]
// };











// frappe.query_reports["Top Selling Items 1"] = {
//     "filters": [
//         {
//             "fieldname": "limit",
//             "label": "Top N Items",
//             "fieldtype": "Int",
//             "default": 10
//         },
//         {
//             "fieldname": "metric",
//             "label": "View By",
//             "fieldtype": "Select",
//             "options": ["qty", "amount"],
//             "default": "qty"
//         },
//         {
//             "fieldname": "period",
//             "label": "Period",
//             "fieldtype": "Select",
//             "options": ["Monthly", "Quarterly", "Yearly"],
//             "default": "Monthly"
//         }
//     ]
// };


























frappe.query_reports["Top Selling Items 1"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "limit",
            "label": "Top N Items",
            "fieldtype": "Int",
            "default": 10
        },
        {
            "fieldname": "metric",
            "label": "View By",
            "fieldtype": "Select",
            "options": ["qty", "amount"],
            "default": "qty"
        },
        {
            "fieldname": "period",
            "label": "Period",
            "fieldtype": "Select",
            "options": ["Monthly", "Quarterly", "Yearly"],
            "default": "Monthly"
        }
    ]
};