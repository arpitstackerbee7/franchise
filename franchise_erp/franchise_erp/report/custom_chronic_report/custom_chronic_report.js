// Copyright (c) 2026, and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Chronic Report"] = {
	filters: [
		{
			fieldname: "store_type",
			label: __("Store Type"),
			fieldtype: "Select",
			options: ["Hot Store", "Dead Store"],
			default: "Hot Store",
			reqd: 1,
		},
		{
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		// hot stores in green, dead stores in red, as in the analysis sheet
		if (column.fieldname === "sell_through" && data) {
			const color = data.sell_through >= 80 ? "green" : data.sell_through < 30 ? "red" : "";
			if (color) value = `<span style="color: var(--${color}-600); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
