// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// Copyright (c) 2026, TZU Lifestyle Private Limited
// For license information, please see license.txt

frappe.query_reports["Custom Gratuity Report"] = {
	"filters": [
		{
			"fieldname": "as_on_date",
			"label": __("As On Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						"company": company
					}
				};
			}
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		}
	]
};