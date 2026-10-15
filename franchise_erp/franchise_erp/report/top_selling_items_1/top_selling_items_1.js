frappe.query_reports["Top Selling Items 1"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
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
            "options": ["qty", "amt"],
            "default": "qty"
        },
        {
            "fieldname": "period",
            "label": "Period",
            "fieldtype": "Select",
            "options": ["Monthly", "Quarterly", "Yearly"],
            "default": "Monthly"
        },
        
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        }
    ]
};

