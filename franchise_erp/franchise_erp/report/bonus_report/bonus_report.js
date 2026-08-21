// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Bonus Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date"
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