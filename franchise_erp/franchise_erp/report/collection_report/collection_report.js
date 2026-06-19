// Copyright (c) 2026
// Collection Report - Filters

function get_fiscal_year_start() {
	// Indian fiscal year: Apr to Mar. If current month is Jan-Mar, FY started last calendar year.
	let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	let year = today.getFullYear();
	let month = today.getMonth() + 1; // JS months are 0-indexed
	if (month < 4) {
		year = year - 1;
	}
	return year + "-04-01";
}

frappe.query_reports["Collection Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": get_fiscal_year_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		}
	],

	"after_datatable_render": function(datatable_obj) {
		let filters = frappe.query_report.get_filter_values();
		let from_date = filters.from_date || "";
		let to_date = filters.to_date || "";

		let title = "Collection Report";
		if (from_date && to_date) {
			title = `Collection Report ${from_date} to ${to_date}`;
		} else if (to_date) {
			title = `Collection Report Till ${to_date}`;
		}

		frappe.query_report.page.set_title(title);
	},

	"get_query_params": function() {
		let filters = frappe.query_report.get_filter_values();
		let from_date = filters.from_date || "";
		let to_date = filters.to_date || "";

		let title = "Collection Report";
		if (from_date && to_date) {
			title = `Collection Report ${from_date} to ${to_date}`;
		} else if (to_date) {
			title = `Collection Report Till ${to_date}`;
		}

		return {
			"report_name": title
		};
	}
};