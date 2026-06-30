frappe.query_reports["Stock Book Report"] = {
	filters: [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname": "supplier",
			"label": __("Party Name"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "barcode",
			"label": __("Barcode"),
			"fieldtype": "Data"
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "image" && value) {
			return `<div style="display:flex; align-items:center; justify-content:center; height:100%;">
				<img src="${value}" style="height:60px;width:60px;object-fit:cover;border-radius:4px;">
			</div>`;
		}
		return default_formatter(value, row, column, data);
	},

	after_datatable_render: function (datatable_obj) {
		datatable_obj.options.cellHeight = 70;
		datatable_obj.refresh();
	}
};