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
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			default: "Distributor",
			on_change: function() {
				
				frappe.query_report.set_filter_value("customer", "");
				frappe.query_report.refresh();
			}
		},
		// {
		// 	fieldname: "customer",
		// 	label: __("Customer"),
		// 	fieldtype: "Link",
		// 	options: "Customer",
		// 	get_query: function() {
		// 		return {
		// 			query: "franchise_erp.franchise_erp.report.collection_report.collection_report.customer_query"
		// 		};
		// 	}
		// },
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "franchise_erp.franchise_erp.report.collection_report.collection_report.customer_query",
					filters: {
						customer_group: frappe.query_report.get_filter_value("customer_group")
					}
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
		add_period_groups(datatable_obj);
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
		.page-form.form-inline,
		.page-form {
			display: flex !important;
			flex-wrap: nowrap !important;
			gap: 8px;
			overflow: visible !important;
		}

		.page-form .form-group,
		.page-form .frappe-control {
			flex: 1 1 0;
			min-width: 100px;
			margin-bottom: 0 !important;
		}

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

function add_period_groups(datatable) {
	const wrapper = datatable.wrapper;
	build_period_groups(datatable);

	// bar gayab ho jaye (column change / re-render) to dobara banao
	if (wrapper.__groupWatch) wrapper.__groupWatch.disconnect();
	let timer = null;
	wrapper.__groupWatch = new MutationObserver(() => {
		clearTimeout(timer);
		timer = setTimeout(() => {
			if (!wrapper.querySelector(".period-group-bar")) {
				build_period_groups(datatable);
			}
		}, 50);
	});
	wrapper.__groupWatch.observe(wrapper, { childList: true, subtree: true });
}

function build_period_groups(datatable) {
	try {
		const groups = [
			{ label: "Previous Period", color: "#d9efbf", from: "net_sale_franchise", to: "pending_amount" },
			{ label: "Current Period", color: "#bfe6f7", from: "sale_qty_15", to: "collectable_amount_15" }
		];

		const wrapper = datatable.wrapper;
		const getHeaderRow = () => datatable.header.querySelector(".dt-row-header");
		if (!getHeaderRow()) return;

		// purani bar aur listeners hatao
		wrapper.querySelectorAll(".period-group-bar").forEach(e => e.remove());
		if (wrapper.__groupSync) {
			wrapper.removeEventListener("scroll", wrapper.__groupSync, true);
			window.removeEventListener("resize", wrapper.__groupSync);
			document.removeEventListener("mousemove", wrapper.__groupSync);
			document.removeEventListener("mouseup", wrapper.__groupSync);
		}

		const bar = document.createElement("div");
		bar.className = "period-group-bar";
		bar.style.cssText = "position:relative;overflow:hidden;height:35px;width:100%;";

		const items = groups.map(g => {
			const div = document.createElement("div");
			div.textContent = g.label;
			div.style.cssText =
				"position:absolute;top:0;height:100%;box-sizing:border-box;" +
				"display:flex;align-items:center;justify-content:center;" +
				"font-weight:bold;color:#333;border-right:1px solid #fff;" +
				"white-space:nowrap;background:" + g.color + ";";
			bar.appendChild(div);
			return { g, div };
		});

		datatable.header.parentNode.insertBefore(bar, datatable.header);

		// har baar fresh columns aur fresh header cells se measure karo
		const cellOf = (id) => {
			const headerRow = getHeaderRow();
			if (!headerRow) return null;
			const cols = datatable.datamanager.columns;
			const idx = cols.findIndex(c => c.id === id);
			if (idx < 0) return null;
			return (
				headerRow.querySelector(`.dt-cell--header-${cols[idx].colIndex}`) ||
				headerRow.querySelectorAll(".dt-cell")[idx] ||
				null
			);
		};

		const update = () => {
			const barRect = bar.getBoundingClientRect();
			items.forEach(({ g, div }) => {
				const a = cellOf(g.from);
				const b = cellOf(g.to);
				if (!a || !b) return;
				let l = a.getBoundingClientRect().left - barRect.left;
				let r = b.getBoundingClientRect().right - barRect.left;
				l = Math.max(l, 0);
				r = Math.min(r, barRect.width);
				if (r <= l) { div.style.display = "none"; return; }
				div.style.display = "flex";
				div.style.left = l + "px";
				div.style.width = (r - l) + "px";
			});
		};

		wrapper.__groupSync = () => requestAnimationFrame(update);
		wrapper.addEventListener("scroll", wrapper.__groupSync, true);
		window.addEventListener("resize", wrapper.__groupSync);
		document.addEventListener("mousemove", wrapper.__groupSync);
		document.addEventListener("mouseup", wrapper.__groupSync);

		update();
	} catch (e) {
		console.error("Period group header failed", e);
	}
}