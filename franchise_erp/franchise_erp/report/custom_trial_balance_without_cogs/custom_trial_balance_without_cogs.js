frappe.query_reports["Custom Trial Balance Without COGS"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(
				frappe.datetime.get_today()
			),
			reqd: 1,
			on_change: function (query_report) {
				var fiscal_year = query_report.get_values().fiscal_year;
				if (!fiscal_year) return;

				frappe.model.with_doc("Fiscal Year", fiscal_year, function () {
					var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
					frappe.query_report.set_filter_value({
						from_date: fy.year_start_date,
						to_date: fy.year_end_date,
					});
				});
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(
				frappe.datetime.get_today(),
				true
			)[1],
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(
				frappe.datetime.get_today(),
				true
			)[2],
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			options: "Cost Center",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			options: "Project",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "with_period_closing_entry_for_opening",
			label: __("With Period Closing Entry For Opening Balances"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "with_period_closing_entry_for_current_period",
			label: __("Period Closing Entry For Current Period"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_zero_values",
			label: __("Show zero values"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_unclosed_fy_pl_balances",
			label: __("Show unclosed fiscal year's P&L balances"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_default_book_entries",
			label: __("Include Default FB Entries"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_net_values",
			label: __("Show net values in opening and closing columns"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_group_accounts",
			label: __("Show Group Accounts"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_breakdown",
			label: __("Show Transaction-wise Breakdown"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "srbnb_view",
			label: __("SRBNB View"),
			fieldtype: "Select",
			options: "\nTransaction Type\nDocument",
			default: "",
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
						is_group: 0,
					},
				};
			},
		},
{
	fieldname: "transaction_type",
	label: __("Transaction Type"),
	fieldtype: "Select",
	options: [
		"",
		"Purchase Receipt",
		"Purchase Return (Receipt)",
		"Purchase Invoice",
		"Debit Note (Purchase Return)",
		"Landed Cost Voucher",
		"Journal Entry (Manual)",
	].join("\n"),
	depends_on: "eval:doc.srbnb_view == 'Document'",
},

		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			depends_on: "eval:doc.srbnb_view == 'Document'",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (!data) {
			return erpnext.financial_statements.formatter(
				value, row, column, data, default_formatter
			);
		}

		// SRBNB account aur uske transaction rows ko clickable banayein
		if (
			column.fieldname === "account" &&
			(data.is_srbnb_account || data.is_srbnb_breakdown)
		) {
			const label = data.is_srbnb_breakdown
				? data.account_name
				: value;

			const safeData = JSON.stringify(data).replace(/'/g, "\\u0027");

			return `<a href="#" onclick='open_srbnb_ledger(${safeData}); return false;'
				style="color: var(--link-color); text-decoration: underline;">
				${frappe.utils.escape_html(label || "")}
			</a>`;
		}

		// Existing transaction breakdown formatting
		if (data.is_breakdown) {
			if (column.fieldname === "account") {
				value = data.account_name;
			} else {
				value = default_formatter(value, row, column, data);
			}

			return `<span style="color: var(--text-muted); font-style: italic;">
				${value || ""}
			</span>`;
		}

		return erpnext.financial_statements.formatter(
			value,
			row,
			column,
			data,
			default_formatter
		);
	},

	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
};

erpnext.utils.add_dimensions("Custom Trial Balance Without COGS", 6);


function open_srbnb_ledger(data) {
	const account = data.parent_account || data.account;

	if (!account || !data.company) {
		frappe.msgprint(
			__("Account or Company is missing.")
		);
		return;
	}

	if (!data.transaction_type) {
		frappe.msgprint(
			__("Transaction Type is missing.")
		);
		return;
	}

	frappe.set_route(
		"query-report",
		"Custom Trial Balance Without COGS",
		{
			company: data.company,
			from_date: data.from_date,
			to_date: data.to_date,
			account: account,
			srbnb_view: "Document",
			transaction_type: data.transaction_type,
		}
	);
}
