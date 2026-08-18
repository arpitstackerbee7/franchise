// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Counter Store-Level Performance"] = {
	filters: [
		{
			fieldname: "sales_manager",
			label: __("Sales Manager"),
			fieldtype: "Link",
			options: "User"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end()
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);


		if (
			column.fieldname === "sales_manager" &&
			data &&
			data.sales_manager
		) {
			return `
				<a
					href="#"
					class="sales-manager-link"
					data-user="${encodeURIComponent(data.sales_manager)}"
					style="font-weight: 600; cursor: pointer;"
				>
					${frappe.utils.escape_html(data.sales_manager)}
				</a>
			`;
		}


		if (
			column.fieldname === "counter_count" &&
			data &&
			data.counter_count
		) {
			if (
				frappe.query_report.get_filter_value(
					"sales_manager"
				)
			) {
				return `
					<a
						href="#"
						class="counter-count-link"
						data-counter-details="${encodeURIComponent(
							data.counter_details || "[]"
						)}"
					>
						${data.counter_count}
					</a>
				`;
			}

			return `
				<a
					href="#"
					class="counter-count-link"
					data-counter-details="${encodeURIComponent(
						data.counter_details || "[]"
					)}"
				>
					1
				</a>
			`;
		}

		return value;
	},

	onload: function () {


		$(document)
			.off(
				"click.custom_counter_report_manager",
				".sales-manager-link"
			)
			.on(
				"click.custom_counter_report_manager",
				".sales-manager-link",
				function (e) {
					e.preventDefault();
					e.stopPropagation();

					const user = decodeURIComponent(
						$(this).attr("data-user") || ""
					);

					open_sales_manager_delivery_notes(user);
				}
			);


		$(document)
			.off(
				"click.custom_counter_report",
				".counter-count-link"
			)
			.on(
				"click.custom_counter_report",
				".counter-count-link",
				function (e) {
					e.preventDefault();

					let counters = [];

					try {
						const counter_details =
							decodeURIComponent(
								$(this).attr(
									"data-counter-details"
								) || "%5B%5D"
							);

						counters = JSON.parse(
							counter_details
						);
					} catch (error) {
						console.error(
							"Unable to parse counter details:",
							error
						);

						frappe.msgprint(
							__(
								"Unable to load counter details."
							)
						);

						return;
					}

					if (
						!frappe.query_report.get_filter_value(
							"sales_manager"
						)
					) {
						const counter = counters[0];

						if (!counter) {
							frappe.msgprint(
								__("No counter found.")
							);
							return;
						}

						open_counter_delivery_notes(
							counter.represents_company
						);

						return;
					}

					show_counter_dialog(counters);
				}
			);
	}
};


function open_sales_manager_delivery_notes(user) {

	const from_date =
		frappe.query_report.get_filter_value(
			"from_date"
		);

	const to_date =
		frappe.query_report.get_filter_value(
			"to_date"
		);

	if (!user || !from_date || !to_date) {
		frappe.msgprint(
			__(
				"User, From Date and To Date are required."
			)
		);

		return;
	}

	const params = new URLSearchParams();

	params.set("owner", user);

	params.set("docstatus", "1");

	params.set(
		"posting_date",
		JSON.stringify([
			"Between",
			[from_date, to_date]
		])
	);

	const url =
		"/app/delivery-note/view/report?" +
		params.toString();

	window.open(url, "_blank");
}


function show_counter_dialog(counters) {

	const dialog = new frappe.ui.Dialog({
		title: __("Assigned Counters"),
		size: "small",

		fields: [
			{
				fieldname: "counter_list",
				fieldtype: "HTML"
			}
		]
	});

	let html = "";

	if (!counters || !counters.length) {

		html = `
			<div class="text-muted">
				${__("No counters found.")}
			</div>
		`;

	} else {

		html = `
			<div class="counter-list">

				${counters
					.map((counter, index) => {

						const customer_name =
							frappe.utils.escape_html(
								counter.customer_name ||
								counter.name
							);

						const customer_id =
							frappe.utils.escape_html(
								counter.name || ""
							);

						const company =
							frappe.utils.escape_html(
								counter.represents_company ||
								""
							);

						return `
							<div
								style="
									padding: 12px 4px;
									border-bottom: ${
										index ===
										counters.length - 1
											? "none"
											: "1px solid var(--border-color)"
									};
								"
							>

								<a
									href="#"
									class="counter-dn-link"
									data-customer="${customer_id}"
									data-company="${company}"
									style="
										font-weight: 600;
										cursor: pointer;
									"
								>
									${customer_name}
								</a>

								${
									customer_id !==
									customer_name
										? `
											<div
												class="text-muted"
												style="
													font-size: 12px;
													margin-top: 2px;
												"
											>
												${customer_id}
											</div>
										`
										: ""
								}

								${
									company
										? `
											<div
												class="text-muted"
												style="
													font-size: 12px;
													margin-top: 2px;
												"
											>
												${__(
													"Company"
												)}:
												${company}
											</div>
										`
										: ""
								}

							</div>
						`;
					})
					.join("")}

			</div>
		`;
	}

	dialog.fields_dict.counter_list.$wrapper.html(
		html
	);


	dialog.fields_dict.counter_list.$wrapper
		.off(
			"click",
			".counter-dn-link"
		)
		.on(
			"click",
			".counter-dn-link",
			function (e) {

				e.preventDefault();

				const company =
					$(this).attr(
						"data-company"
					);

				if (!company) {

					frappe.msgprint(
						__(
							"Represented Company is not set for this Counter."
						)
					);

					return;
				}

				open_counter_delivery_notes(
					company
				);
			}
		);

	dialog.show();
}


function open_counter_delivery_notes(company) {

	const from_date =
		frappe.query_report.get_filter_value(
			"from_date"
		);

	const to_date =
		frappe.query_report.get_filter_value(
			"to_date"
		);

	if (!company) {

		frappe.msgprint(
			__(
				"Represented Company is not set for this Counter."
			)
		);

		return;
	}

	if (!from_date || !to_date) {

		frappe.msgprint(
			__(
				"Please select From Date and To Date."
			)
		);

		return;
	}

	const params = new URLSearchParams();

	params.set(
		"company",
		company
	);

	params.set(
		"docstatus",
		"1"
	);

	params.set(
		"posting_date",
		JSON.stringify([
			"between",
			[from_date, to_date]
		])
	);

	const url =
		"/app/delivery-note/view/report?" +
		params.toString();

	window.open(
		url,
		"_blank"
	);
}