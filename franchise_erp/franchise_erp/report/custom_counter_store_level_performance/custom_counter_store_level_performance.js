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


	// =====================================================
	// FORMATTER
	// =====================================================

	formatter: function (
		value,
		row,
		column,
		data,
		default_formatter
	) {

		value = default_formatter(
			value,
			row,
			column,
			data
		);


		// =================================================
		// SALES MANAGER
		// =================================================

		if (
			column.fieldname === "sales_manager" &&
			data &&
			data.sales_manager
		) {

			return `
				<a
					href="#"
					class="sales-manager-link"
					data-user="${encodeURIComponent(
						data.sales_manager
					)}"
					style="
						font-weight: 600;
						cursor: pointer;
					"
				>
					${frappe.utils.escape_html(
						data.sales_manager
					)}
				</a>
			`;
		}


		// =================================================
		// COUNTER COUNT
		// =================================================

		if (
			column.fieldname === "counter_count" &&
			data
		) {

			return `
				<a
					href="#"
					class="counter-count-link"
					data-counter-details="${encodeURIComponent(
						data.counter_details || "[]"
					)}"
					style="
						cursor: pointer;
						font-weight: 600;
					"
				>
					${data.counter_count || 0}
				</a>
			`;
		}


		return value;
	},


	// =====================================================
	// ONLOAD
	// =====================================================

	onload: function () {


		// =================================================
		// SALES MANAGER CLICK
		// =================================================

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

					const user =
						decodeURIComponent(
							$(this).attr(
								"data-user"
							) || ""
						);

					open_sales_manager_delivery_notes(
						user
					);
				}
			);


		// =================================================
		// COUNTER COUNT CLICK
		// =================================================

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
					e.stopPropagation();

					let counters = [];

					try {

						const counter_details =
							decodeURIComponent(
								$(this).attr(
									"data-counter-details"
								) || "%5B%5D"
							);

						counters =
							JSON.parse(
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
						!counters.length
					) {

						frappe.msgprint(
							__(
								"No counters found."
							)
						);

						return;
					}


					show_counter_dialog(
						counters
					);
				}
			);
	}
};


// =========================================================
// OPEN SALES MANAGER DELIVERY NOTES
// =========================================================
function open_sales_manager_delivery_notes(user) {

	const from_date =
		frappe.query_report.get_filter_value("from_date");

	const to_date =
		frappe.query_report.get_filter_value("to_date");

	if (!user || !from_date || !to_date) {
		frappe.msgprint(
			__("User, From Date and To Date are required.")
		);
		return;
	}

	// =====================================================
	// GET CURRENT SALES MANAGER ROW
	// =====================================================

	const report_data = frappe.query_report.data || [];

	const manager_row = report_data.find(
		row => row.sales_manager === user
	);

	if (!manager_row) {
		frappe.msgprint(
			__("Sales Manager data not found.")
		);
		return;
	}

	// =====================================================
	// GET ASSIGNED COUNTERS
	// =====================================================

	let counters = [];

	try {
		counters = JSON.parse(
			manager_row.counter_details || "[]"
		);
	} catch (error) {
		console.error(
			"Unable to parse counter details:",
			error
		);

		frappe.msgprint(
			__("Unable to load assigned counters.")
		);

		return;
	}

	// =====================================================
	// GET UNIQUE COMPANIES
	// =====================================================

	const companies = [
		...new Set(
			counters
				.map(counter =>
					(counter.represents_company || "").trim()
				)
				.filter(Boolean)
		)
	];

	if (!companies.length) {
		frappe.msgprint(
			__("No company found for assigned counters.")
		);
		return;
	}

	// =====================================================
	// OPEN DELIVERY NOTE REPORT
	// =====================================================

	const params = new URLSearchParams();

	/*
	 * IMPORTANT:
	 * Frappe MultiSelect/List filter format:
	 *
	 * company = ["in", ["Company 1", "Company 2"]]
	 */

	params.set(
		"company",
		JSON.stringify([
			"in",
			companies
		])
	);

	params.set(
		"docstatus",
		"1"
	);

	params.set(
		"posting_date",
		JSON.stringify([
			"Between",
			[
				from_date,
				to_date
			]
		])
	);

	const url =
		"/app/delivery-note/view/report?" +
		params.toString();

	console.log("Companies:", companies);
	console.log("Delivery Note URL:", url);

	window.open(
		url,
		"_blank"
	);
}


// =========================================================
// SHOW COUNTER DIALOG
// =========================================================

function show_counter_dialog(
	counters
) {

	const dialog =
		new frappe.ui.Dialog({

			title: __(
				"Assigned Counters"
			),

			size: "small",

			fields: [
				{
					fieldname:
						"counter_list",

					fieldtype:
						"HTML"
				}
			]
		});


	let html = "";


	if (
		!counters ||
		!counters.length
	) {

		html = `
			<div class="text-muted">
				${__(
					"No counters found."
				)}
			</div>
		`;

	} else {

		html = `
			<div class="counter-list">

				${counters
					.map(
						(
							counter,
							index
						) => {

							const customer_name =
								frappe.utils.escape_html(
									counter.customer_name ||
									counter.name ||
									""
								);


							const customer_id =
								frappe.utils.escape_html(
									counter.name ||
									""
								);


							const company =
								frappe.utils.escape_html(
									counter.represents_company ||
									""
								);


							const counter_owner =
								frappe.utils.escape_html(
									counter.counter_owner ||
									""
								);


							return `
								<div
									style="
										padding: 12px 4px;
										border-bottom:
											${
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
										data-customer="${encodeURIComponent(
											counter.name || ""
										)}"
										style="
											font-weight: 600;
											cursor: pointer;
										"
									>
										${customer_name}
									</a>


									${
										customer_id &&
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


									${
										counter_owner
											? `
												<div
													class="text-muted"
													style="
														font-size: 12px;
														margin-top: 2px;
													"
												>
													${__(
														"Created By"
													)}:
													${counter_owner}
												</div>
											`
											: ""
									}

								</div>
							`;
						}
					)
					.join("")}

			</div>
		`;
	}


	dialog.fields_dict
		.counter_list
		.$wrapper
		.html(
			html
		);


	// =====================================================
	// COUNTER CLICK
	// =====================================================

	dialog.fields_dict
		.counter_list
		.$wrapper

		.off(
			"click",
			".counter-dn-link"
		)

		.on(
			"click",
			".counter-dn-link",
			function (e) {

				e.preventDefault();

				const customer =
					decodeURIComponent(
						$(this).attr(
							"data-customer"
						) || ""
					);


				if (!customer) {

					frappe.msgprint(
						__(
							"Customer is not set for this Counter."
						)
					);

					return;
				}


				open_counter_delivery_notes(
					customer
				);
			}
		);


	dialog.show();
}


// =========================================================
// OPEN COUNTER DELIVERY NOTES
// =========================================================

function open_counter_delivery_notes(
	customer
) {

	const from_date =
		frappe.query_report.get_filter_value(
			"from_date"
		);

	const to_date =
		frappe.query_report.get_filter_value(
			"to_date"
		);


	if (!customer) {

		frappe.msgprint(
			__(
				"Customer is not set for this Counter."
			)
		);

		return;
	}


	if (
		!from_date ||
		!to_date
	) {

		frappe.msgprint(
			__(
				"Please select From Date and To Date."
			)
		);

		return;
	}


	const params =
		new URLSearchParams();


	// =================================================
	// Specific Counter / Customer
	// =================================================

	params.set(
		"customer",
		customer
	);


	params.set(
		"docstatus",
		"1"
	);


	params.set(
		"posting_date",
		JSON.stringify([
			"Between",
			[
				from_date,
				to_date
			]
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