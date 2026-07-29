// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Bonus Report"] = {
    "filters": [
        {
            "fieldname": "bonus_year",
            "label": __("Bonus Year"),
            "fieldtype": "Select",
            "options": ["2025-2026", "2026-2027"],
            "reqd": 1,
            "default": "2026-2027"
        },
		{
            "fieldname": "month",
            "label": "Month",
            "fieldtype": "Select",
            "options": ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].join("\n"),
		},
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee"
        },
        {
            "fieldname": "salary_structure",
            "label": __("Salary Structure"),
            "fieldtype": "Link",
            "options": "Salary Structure"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        }
    ]
};