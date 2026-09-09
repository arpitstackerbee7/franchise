
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

	onload: function (report) {
		report.page.add_inner_button(
			__("Summary Export"),
			function () {
				let filters = report.get_values();

				frappe.call({
					method: "frappe.desk.query_report.run",

					args: {
						report_name: "Custom Sales Invoice",
						filters: filters,
						ignore_prepared_report: 1,
					},

					freeze: true,

					freeze_message: __(
						"Preparing Excel Export..."
					),

				}).then((r) => {
					let result = r.message || {};
					let data = result.result || [];


					if (!data.length) {
						frappe.msgprint(
							__(
								"No data found for the selected filters."
							)
						);

						return;
					}

					let headers = [
						"Sales Invoice",
						"Posting Date",
						"Customer",
						"Customer Name",
						"Customer agent name",
						"Class Name",
						"Company",
						"Quantity",
						"Gross Amount (Taxable Value (INR))",
						"Net Amount",
					];


					let total_qty = 0;
					let total_gross_amount = 0;
					let total_net_amount = 0;

					let rows = [];

					data.forEach((row) => {
						let sales_invoice =
							row.name || "";

						let posting_date =
							row.posting_date || "";

						let customer =
							row.customer || "";

						let customer_name =
							row.customer_name || "";


							let customer_agent_name =
							row.agent_supplier || "";

						let class_name =
							row.class_name || "";

						let company =
							row.company || "";

						let qty =
							flt(row.qty);


							let gross_amount =
							flt(row.grand_total);


							let net_amount =
							flt(row.rounded_total);

						rows.push([
							sales_invoice,
							posting_date,
							customer,
							customer_name,
							customer_agent_name,
							class_name,
							company,
							qty.toFixed(2),
							gross_amount.toFixed(2),
							net_amount.toFixed(2),
						]);

						total_qty += qty;
						total_gross_amount +=
							gross_amount;
						total_net_amount +=
							net_amount;
					});

	
					let html = `
						<html>
						<head>
							<meta charset="UTF-8">

							<style>
								table {
									border-collapse: collapse;
									width: 100%;
								}

								th {
									background-color: #f2f2f2;
									font-weight: bold;
									border: 1px solid #000000;
									padding: 6px;
									text-align: center;
								}

								td {
									border: 1px solid #000000;
									padding: 6px;
								}

								.total-row td {
									font-weight: bold;
									border-top: 2px solid #000000;
								}

								.number {
									text-align: right;
								}
							</style>
						</head>

						<body>

							<table>

								<thead>
									<tr>
					`;

					headers.forEach((header) => {
						html +=
							"<th>" +
							escape_html(header) +
							"</th>";
					});

					html += `
									</tr>
								</thead>

								<tbody>
					`;

					rows.forEach((row) => {
						html += "<tr>";

						row.forEach((value, index) => {
							let class_name =
								index >= 7
									? "number"
									: "";

							html +=
								'<td class="' +
								class_name +
								'">' +
								escape_html(value) +
								"</td>";
						});

						html += "</tr>";
					});


					html += `
						<tr class="total-row">
							<td>TOTAL</td>
							<td></td>
							<td></td>
							<td></td>
							<td></td>
							<td></td>
							<td></td>
							<td class="number">
								${total_qty.toFixed(2)}
							</td>
							<td class="number">
								${total_gross_amount.toFixed(2)}
							</td>
							<td class="number">
								${total_net_amount.toFixed(2)}
							</td>
						</tr>
					`;

					html += `
								</tbody>

							</table>

						</body>
						</html>
					`;

					let blob = new Blob(
						[
							"\ufeff" + html
						],
						{
							type:
								"application/vnd.ms-excel;charset=utf-8;",
						}
					);

					let url =
						URL.createObjectURL(blob);

		
					let link =
						document.createElement("a");

					link.href = url;

					link.download =
						"Custom_Sales_Invoice_Summary_" +
						frappe.datetime
							.now_datetime()
							.replace(
								/[: ]/g,
								"_"
							) +
						".xls";

					document.body.appendChild(link);

					link.click();

					document.body.removeChild(link);

					URL.revokeObjectURL(url);

					frappe.show_alert({
						message: __(
							"Excel file downloaded successfully."
						),
						indicator: "green",
					});
				});
			}
		);
	},
};


function escape_html(value) {
	if (
		value === null ||
		value === undefined
	) {
		return "";
	}

	return String(value)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}
