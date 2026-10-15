frappe.query_reports["Custom Trial Balance"] = {
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
			// Data field: breakdown rows ke saare naam (Purchase Receipt, Journal Entry,
			// Stock Entry - ..., etc.) bina options ke chal jaayein
			fieldname: "transaction_type",
			label: __("Transaction Type"),
			fieldtype: "Data",
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

		// Clickable rows: har breakdown row aur summary view ki rows.
		// Account ki normal row (SRBNB bhi) ERPNext ki default General Ledger link se chalti hai.
		const is_link =
			(column.fieldname === "account" && data.is_txn_link) ||
			(column.fieldname === "txn" && data.is_srbnb_txn_link);

		if (is_link) {
			const label = data.is_txn_link ? data.account_name : value;

			// Poori row nahi, sirf zaroori fields (chhota + safe)
			const payload = {
				company: data.company,
				from_date: data.from_date,
				to_date: data.to_date,
				account: data.link_account,
				transaction_type: data.transaction_type || "",
			};

			const encoded = encodeURIComponent(JSON.stringify(payload)).replace(
				/'/g,
				"%27"
			);

			return `<a href="#" class="srbnb-link"
				data-payload="${encoded}"
				onclick="window.open_srbnb_ledger('${encoded}'); return false;"
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

erpnext.utils.add_dimensions("Custom Trial Balance", 6);


// Click handler: document level par (capture phase), taaki datatable ya koi aur
// handler click ko rok na sake. Sirf ek baar bind hota hai.
if (!window.__srbnb_click_bound) {
	window.__srbnb_click_bound = true;

	document.addEventListener(
		"click",
		function (e) {
			const link = e.target && e.target.closest
				? e.target.closest("a.srbnb-link")
				: null;

			if (!link) return;

			e.preventDefault();
			e.stopPropagation();
			window.open_srbnb_ledger(link.getAttribute("data-payload"));
		},
		true
	);
}

// window par explicitly assign: script kisi bhi scope me eval ho, function global rahega
window.open_srbnb_ledger = function (encoded) {
	let p;
	try {
		p = JSON.parse(decodeURIComponent(encoded));
	} catch (e) {
		console.error("SRBNB link: bad payload", encoded, e);
		frappe.msgprint(__("Could not read link data."));
		return;
	}

	console.log("SRBNB link clicked:", p);

	if (!p.account || !p.company) {
		console.error("SRBNB link: missing account/company", p);
		frappe.msgprint(__("Account or Company is missing."));
		return;
	}

	// Transaction type hai -> us type ke documents.
	// Nahi hai (SRBNB parent row) -> transaction type wise summary.
	const options = {
		company: p.company,
		from_date: p.from_date,
		to_date: p.to_date,
		account: p.account,
		srbnb_view: p.transaction_type ? "Document" : "Transaction Type",
		transaction_type: p.transaction_type || "",
	};

	// Jo filters abhi report me lage hain, wahi aage carry karo,
	// taaki value TB ke breakdown se match kare
	const carry = [
		"fiscal_year",
		"cost_center",
		"project",
		"finance_book",
		"include_default_book_entries",
		"with_period_closing_entry_for_current_period",
	];

	carry.forEach((name) => {
		const v = frappe.query_report
			? frappe.query_report.get_filter_value(name)
			: null;

		const empty =
			v === undefined ||
			v === null ||
			v === "" ||
			(Array.isArray(v) && !v.length);

		if (!empty) {
			options[name] = v;
		}
	});

	const query = Object.keys(options)
		.map((key) => {
			let val = options[key];
			if (Array.isArray(val)) val = JSON.stringify(val);
			return encodeURIComponent(key) + "=" + encodeURIComponent(val);
		})
		.join("&");

	// true karoge to naye tab me khulega, false = isi tab me redirect
	const open_in_new_tab = false;

	// Full URL redirect: same-page route refresh ki problem nahi aati.
	// Back dabane par Trial Balance wapas aa jaata hai (filters URL me hote hain).
	const url =
		window.location.origin +
		"/app/query-report/" +
		encodeURIComponent("Custom Trial Balance") +
		"?" + query;

	console.log("SRBNB link url:", url);

	if (open_in_new_tab) {
		window.open(url, "_blank");
	} else {
		window.location.assign(url);
	}
};