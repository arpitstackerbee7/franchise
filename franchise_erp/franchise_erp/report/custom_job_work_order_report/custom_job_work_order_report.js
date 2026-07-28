// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Job Work Order Report"] = {
	filters: [
		{
			label: __("Order Type"),
			fieldname: "order_type",
			fieldtype: "Select",
			// options: ["Purchase Order", "Subcontracting Order"],
			options: ["Subcontracting Order"],
			default: "Subcontracting Order",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			get_query: function() {
				return {
					order_by: "name asc"
				};
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],

	onload: function(report) {
		frappe.db.get_list("Supplier", {
			fields: ["name"],
			limit: 1,
			order_by: "name asc"
		}).then((r) => {
			if (r.length) {
				report.set_filter_value("supplier", r[0].name);
			}
		});
	}
};