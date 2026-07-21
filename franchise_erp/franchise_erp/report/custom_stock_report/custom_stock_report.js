// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Stock Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			width: "80",
			options: "Company",
			default: frappe.defaults.get_default("company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			width: "80",
			options: "Item Group",
		},
		{
			fieldname: "item_code",
			label: __("Items"),
			fieldtype: "MultiSelectList",
			width: "80",
			options: "Item",
			get_data: async function (txt) {
				let item_group = frappe.query_report.get_filter_value("item_group");

				let filters = {
					...(item_group && { item_group }),
					is_stock_item: 1,
				};

				let { message: data } = await frappe.call({
					method: "erpnext.controllers.queries.item_query",
					args: {
						doctype: "Item",
						txt: txt,
						searchfield: "name",
						start: 0,
						page_len: 10,
						filters: filters,
						as_dict: 1,
					},
				});

				data = data.map(({ name, ...rest }) => {
					return {
						value: name,
						description: Object.values(rest),
					};
				});

				return data || [];
			},
		},
		{
			fieldname: "warehouse",
			label: __("Warehouses"),
			fieldtype: "MultiSelectList",
			width: "80",
			options: "Warehouse",
			get_data: (txt) => {
				let warehouse_type = frappe.query_report.get_filter_value("warehouse_type");
				let company = frappe.query_report.get_filter_value("company");

				let filters = {
					...(warehouse_type && { warehouse_type }),
					...(company && { company }),
				};

				return frappe.db.get_link_options("Warehouse", txt, filters);
			},
		},
		{
			fieldname: "warehouse_type",
			label: __("Warehouse Type"),
			fieldtype: "Link",
			width: "80",
			options: "Warehouse Type",
		},
		{
			fieldname: "valuation_field_type",
			label: __("Valuation Field Type"),
			fieldtype: "Select",
			width: "80",
			options: "Currency\nFloat",
			default: "Currency",
		},
		{
			fieldname: "include_uom",
			label: __("Include UOM"),
			fieldtype: "Link",
			options: "UOM",
		},
		{
			fieldname: "show_variant_attributes",
			label: __("Show Variant Attributes"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_stock_ageing_data",
			label: __("Show Stock Ageing Data"),
			fieldtype: "Check",
		},
		{
			fieldname: "ignore_closing_balance",
			label: __("Ignore Closing Balance"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "include_zero_stock_items",
			label: __("Include Zero Stock Items"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_dimension_wise_stock",
			label: __("Show Dimension Wise Stock"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {

		// Image Column
		if (column.fieldname === "image" && value) {
			return `
				<div style="display:flex;align-items:center;justify-content:center;height:100%;">
					<img src="${value}" style="height:60px;width:60px;object-fit:cover;border-radius:4px;">
				</div>
			`;
		}

		// Serial Number Column
		if (column.fieldname === "serial_no" && data && data.serial_no) {
			return `
				<a href="#" class="show-serials"
					data-serials="${encodeURIComponent(data.serial_no)}">
					View Serial Numbers (${data.serial_count || 0})
				</a>
			`;
		}

		value = default_formatter(value, row, column, data);

		if (column.fieldname == "out_qty" && data && data.out_qty > 0) {
			value = "<span style='color:red'>" + value + "</span>";
		} else if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	},

	after_datatable_render: function (datatable_obj) {
		datatable_obj.options.cellHeight = 70;
		datatable_obj.refresh();
	},

	onload: function (report) {

		report.page.add_inner_button(__("View Stock Ledger"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "Stock Ledger", filters);
		});

		report.page.add_inner_button(__("Export with Images"), function () {
			frappe.show_alert({
				message: __("Generating Excel with images..."),
				indicator: "blue"
			});

			frappe.call({
				method: "franchise_erp.franchise_erp.report.custom_stock_report.export_with_images.export_custom_stock_report_with_images",
				args: {
					filters: report.get_filter_values()
				},
				callback: function (r) {
					if (r.message) {
						window.open(r.message);
						frappe.show_alert({
							message: __("Excel file ready!"),
							indicator: "green"
						});
					}
				},
			});
		});

		// Serial Number Popup
		$(document).off("click", ".show-serials");

		$(document).on("click", ".show-serials", function (e) {
			e.preventDefault();

			let serials = decodeURIComponent($(this).attr("data-serials"));

			let dialog = new frappe.ui.Dialog({
				title: __("Serial Numbers"),
				size: "large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "serial_list",
					},
				],
			});

			dialog.fields_dict.serial_list.$wrapper.html(`
				<div style="max-height:500px;overflow-y:auto;padding:10px;">
					${serials.split(", ").join("<br>")}
				</div>
			`);

			dialog.show();
		});
	},
};

erpnext.utils.add_inventory_dimensions("Custom Stock Report", 8);