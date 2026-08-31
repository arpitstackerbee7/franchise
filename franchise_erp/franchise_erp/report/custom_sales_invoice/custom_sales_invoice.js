frappe.query_reports["Custom Sales Invoice"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			width: "100px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			width: "100px",
		},
		{
			fieldname: "customer",
			label: __("Customer Name"),
			fieldtype: "MultiSelectList",

			get_data: function (txt) {
				return frappe.db.get_link_options(
					"Customer",
					txt
				);
			},
		},
		{
			fieldname: "class_name",
			label: __("Class Name"),
			fieldtype: "MultiSelectList",

			get_data: function (txt) {
				return frappe.call({
					method: "frappe.client.get_list",

					args: {
						doctype: "Sales Invoice",
						fields: ["custom_class_name"],
						filters: {
							custom_class_name: ["like", `%${txt}%`],
						},
						distinct: true,
						limit_page_length: 20,
					},
				}).then((r) => {
					let unique_classes = [
						...new Set(
							(r.message || [])
								.map((d) => d.custom_class_name)
								.filter(Boolean)
						),
					];

					return unique_classes.map((value) => ({
						value: value,
						description: "",
					}));
				});
			},
		},
		{
			fieldname: "agent",
			label: __("Agent"),
			fieldtype: "MultiSelectList",

			get_data: function (txt) {
				return frappe.db.get_link_options(
					"Supplier",
					txt
				);
			},
		},
		{
			fieldname: "sales_invoice",
			label: __("ID"),
			fieldtype: "MultiSelectList",

			get_data: function (txt) {
				return frappe.db.get_link_options(
					"Sales Invoice",
					txt
				);
			},
		},
	],
};