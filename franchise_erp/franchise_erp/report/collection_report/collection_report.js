// Copyright (c) 2026
// Collection Report - Filters

function get_fiscal_year_start() {
	let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	let year = today.getFullYear();
	let month = today.getMonth() + 1;

	if (month < 4) {
		year = year - 1;
	}

	return year + "-04-01";
}


frappe.query_reports["Collection Report"] = {
	filters: [

		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},

		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: get_fiscal_year_start(),
			reqd: 1
		},

		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},

		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "franchise_erp.franchise_erp.report.collection_report.collection_report.customer_query"
				};
			}
		},

		{
			fieldname: "asm",
			label: __("ASM"),
			fieldtype: "Link",
			options: "User",
			get_query: function() {
				return {
					filters: {
						enabled: 1
					}
				};
			}
		},

		{
			fieldname: "agent",
			label: __("Agent Name"),
			fieldtype: "Link",
			options: "Supplier",
			width: 200
		}

	],


	after_datatable_render: function(datatable_obj) {
		set_report_title();
	},


	onload: function(report) {
		set_report_title();
		override_print_title();
		inject_print_heading_style();
	},


	get_query_params: function() {
		let filters = frappe.query_report.get_filter_values();

		return {
			report_name: get_report_title(filters)
		};
	}

};


function get_report_title(filters) {
	let from_date = filters.from_date || "";
	let to_date = filters.to_date || "";

	let title = "Collection Report";

	if (from_date && to_date) {
		title = `Collection Report ${from_date} to ${to_date}`;
	} else if (to_date) {
		title = `Collection Report Till ${to_date}`;
	}

	return title;
}


function set_report_title() {
	let filters = frappe.query_report.get_filter_values();

	frappe.query_report.page.set_title(
		get_report_title(filters)
	);
}

function override_print_title() {

	if (frappe.query_report._period_title_patched) {
		return;
	}

	let original_print_report = frappe.query_report.print_report;

	frappe.query_report.print_report = function(print_settings) {

		let filters = frappe.query_report.get_filter_values();
		this.report_name = get_report_title(filters);

		return original_print_report.call(this, print_settings);
	};

	frappe.query_report._period_title_patched = true;

}

function inject_print_heading_style() {

	if (document.getElementById("collection-report-print-style")) {
		return;
	}

	let style = document.createElement("style");
	style.id = "collection-report-print-style";
	style.innerHTML = `
		.print-heading, .print-heading h2, .print-format-container h2 {
			font-weight: bold !important;
		}

		@media print {
			@page {
				size: A4 landscape;
				margin: 8mm;
			}

			.print-format-container table {
				table-layout: fixed !important;
				width: 100% !important;
				border-collapse: collapse !important;
			}

			.print-format-container table th,
			.print-format-container table td {
				font-size: 9px !important;
				padding: 3px 4px !important;
				word-wrap: break-word !important;
				white-space: normal !important;
				vertical-align: middle !important;
				border: 1px solid #999 !important;
			}

			.print-format-container table th {
				text-align: center !important;
			}

			.print-format-container table td {
				text-align: right !important;
			}

			.print-format-container table td:first-child,
			.print-format-container table th:first-child,
			.print-format-container table td:nth-child(2),
			.print-format-container table th:nth-child(2) {
				text-align: left !important;
			}
		}
	`;

	document.head.appendChild(style);

}