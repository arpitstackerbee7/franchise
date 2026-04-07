frappe.query_reports["Stock Book Report"] = {
	"filters": [
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
	]
};