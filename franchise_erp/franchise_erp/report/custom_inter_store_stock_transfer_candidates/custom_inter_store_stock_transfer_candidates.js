// Copyright (c) 2026, and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Inter-store Stock Transfer Candidates"] = {
	filters: [
		{
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],
};
