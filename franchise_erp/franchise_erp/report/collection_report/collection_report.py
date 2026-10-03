
import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate, now_datetime


def execute(filters=None):
	filters = filters or {}

	validate_filters(filters)

	companies = get_counter_companies(filters)

	if not companies:
		frappe.msgprint(_("No companies found."))
		return [], []

	columns = get_columns()
	data = get_data(filters, companies)

	return columns, data



def validate_filters(filters):
	if not filters.get("from_date"):
		frappe.throw(_("From Date is required"))

	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))

	if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_counter_companies(filters):
	company = filters.get("company")

	company_filters = {}

	if company:
		company_filters["name"] = company

	return frappe.get_all(
		"Company",
		filters=company_filters,
		pluck="name"
	)


# def get_sis_company_map(customer_filter=None):

# 	customer_filters = {
# 		"disabled": 0
# 	}

# 	if customer_filter:
# 		customer_filters["name"] = customer_filter

# 	rows = frappe.get_all(
# 		"Customer",
# 		filters=customer_filters,
# 		fields=["name", "customer_name", "represents_company"]
# 	)

# 	result = {}

# 	for r in rows:

# 		sis_company = r.represents_company or r.customer_name

# 		if frappe.db.exists("Company", sis_company):
# 			result[r.name] = sis_company

# 	return result

def get_sis_company_map(customer_filter=None):

	customer_filters = {
		"disabled": 0
	}

	if customer_filter:
		customer_filters["name"] = customer_filter

	rows = frappe.get_all(
		"Customer",
		filters=customer_filters,
		fields=["name", "customer_name", "represents_company"]
	)

	chosen = {}

	for r in rows:

		sis_company = r.represents_company or r.customer_name

		if not frappe.db.exists("Company", sis_company):
			continue

		# lower number = higher priority
		if r.represents_company:
			priority = 0
		elif r.name == sis_company:
			priority = 1
		else:
			priority = 2

		prev = chosen.get(sis_company)

		if not prev or priority < prev[0]:
			chosen[sis_company] = (priority, r.name)

	return {
		name: company
		for company, (priority, name) in chosen.items()
	}

def get_customer_extra_fields(customers, filters=None):
	if not customers:
		return {}

	filters = filters or {}

	conditions = "c.name IN %(customers)s"

	values = {
		"customers": customers
	}

	if filters.get("agent"):
		conditions += " AND c.custom_agent = %(agent)s"
		values["agent"] = filters.get("agent")

	if filters.get("asm"):
		conditions += " AND c.account_manager = %(asm)s"
		values["asm"] = filters.get("asm")

	rows = frappe.db.sql(
		f"""
		SELECT
			c.name,
			c.custom_agent,
			u.full_name AS asm_name
		FROM `tabCustomer` c
		LEFT JOIN `tabUser` u
			ON u.name = c.account_manager
		WHERE {conditions}
		""",
		values,
		as_dict=True
	)

	return {
		r.name: r
		for r in rows
	}


def get_columns():
	return [

		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 130
		},

		{
			"label": _("Agent"),
			"fieldname": "agent",
			"fieldtype": "Data",
			"width": 90
		},

		{
			"label": _("ASM"),
			"fieldname": "asm",
			"fieldtype": "Data",
			"width": 90
		},

		{
			"label": _("Franchise Fees"),
			"fieldname": "net_sale_franchise",
			"fieldtype": "Currency",
			"width": 130
		},

		{
			"label": _("Previous Sale Qty"),
			"fieldname": "sale_qty_ytd",
			"fieldtype": "Float",
			"width": 85
		},

		{
			"label": _("Previous Sale Amount"),
			"fieldname": "amount_ytd",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Credit Note"),
			"fieldname": "credit_note",
			"fieldtype": "Currency",
			"width": 85
		},

		{
			"label": _("Debit Note"),
			"fieldname": "debit_note",
			"fieldtype": "Currency",
			"width": 85
		},

		{
			"label": _("Payment Receivable"),
			"fieldname": "payment_received",
			"fieldtype": "Currency",
			"width": 90
		},

		{
			"label": _("Collectable Amount"),
			"fieldname": "collectable_amount",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Last 15 Days Sale Qty"),
			"fieldname": "sale_qty_15",
			"fieldtype": "Float",
			"width": 90
		},

		{
			"label": _("Last 15 Days Sale Amount"),
			"fieldname": "amount_15",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Credit Note (Last 15 Days)"),
			"fieldname": "credit_note_15",
			"fieldtype": "Currency",
			"width": 90
		},

		{
			"label": _("Debit Note (Last 15 Days)"),
			"fieldname": "debit_note_15",
			"fieldtype": "Currency",
			"width": 90
		},

		{
			"label": _("Collectable Amount Last 15 Days"),
			"fieldname": "collectable_amount_15",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Total Collectable Amount"),
			"fieldname": "total_collectable_amount",
			"fieldtype": "Currency",
			"width": 100
		}


	]


def get_data(filters, companies):

	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	last_15_start = from_date

	customer_filter = filters.get("customer")

	if customer_filter:
		customer_filter = (
			frappe.db.exists("Customer", customer_filter)
			or frappe.db.get_value(
				"Customer",
				{"customer_name": customer_filter, "disabled": 0},
				"name",
				order_by="IFNULL(represents_company, '') = '' asc, creation asc"
			)
			or customer_filter
		)

	sis_map = get_sis_company_map(customer_filter)

	sales_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start,
		"prev_to_date": add_days(from_date, -1)
	}

	customer_condition = ""

	if customer_filter:
		customer_condition = " AND si.customer = %(customer)s"
		sales_values["customer"] = customer_filter


	from erpnext.accounts.report.trial_balance.trial_balance import execute as trial_balance_execute

	tb_to_date = add_days(from_date, -1)

	opening_map = {}

	for customer, sis_company in sis_map.items():

		fiscal_year = frappe.db.get_value(
			"Fiscal Year",
			{
				"year_start_date": ["<=", tb_to_date],
				"year_end_date": [">=", tb_to_date],
				"disabled": 0
			},
			["name", "year_start_date", "year_end_date"],
			as_dict=True
		)

		if not fiscal_year:
			frappe.throw(
				_("No active Fiscal Year found for {0}").format(tb_to_date)
			)

		tb_filters = frappe._dict({
			"company": sis_company,
			"fiscal_year": fiscal_year.name,
			"from_date": fiscal_year.year_start_date,
			"to_date": tb_to_date,
			"with_period_closing_entry_for_opening": 1,
			"with_period_closing_entry_for_current": 1,
			"show_net_values": 1,
			"show_group_accounts": 1,
			"include_default_book_entries": 1,
		})

		columns, trial_balance_data = trial_balance_execute(tb_filters)

		closing_dr = 0

		for row in trial_balance_data:
			if row.get("account_name") == "Stock Expenses":
				closing_dr = row.get("closing_debit") or 0
				break

		opening_map[customer] = frappe._dict({
			"opening_stock": closing_dr
		})

	# =====================================================
	# SALE QUANTITY


	from franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log import fetch_invoices

	qty_map = {}
	first_delivery_data = frappe.db.sql(
		"""
		SELECT
			dn.company AS customer,
			MIN(dn.posting_date) AS first_date
		FROM `tabDelivery Note` dn
		WHERE
			dn.docstatus = 1
		GROUP BY dn.company
		""",
		as_dict=True
	)
	first_delivery_map = {
    (d.customer or "").strip().lower(): d.first_date
    for d in first_delivery_data
    }

	# -----------------------------------------------------
	# Customer rows ke liye
	# -----------------------------------------------------

	for customer, sis_company in sis_map.items():

		qty_map[customer] = {
			"qty_ytd": 0,
			"qty_15": 0,
			"amount_ytd": 0,
			"amount_15": 0
		}

		# -------------------------------------------------
		# PREVIOUS PERIOD
		# -------------------------------------------------

		first_delivery_date = first_delivery_map.get((sis_company or "").strip().lower())
		previous_period_end = add_days(from_date, -1)

		if first_delivery_date and getdate(first_delivery_date) <= previous_period_end:
			previous_result = fetch_invoices(
				company=sis_company,
				from_date=str(first_delivery_date),
				to_date=str(previous_period_end)
			)
		else:
			previous_result = {}

		for row in (previous_result.get("invoice_list") or []):
			qty_map[customer]["qty_ytd"] += float(row.get("qty") or 0)
			qty_map[customer]["amount_ytd"] += float(row.get("invoice_value") or 0)


		# -------------------------------------------------
		# LAST 15 DAYS
		# -------------------------------------------------

		last_15_result = fetch_invoices(
			company=sis_company,
			from_date=str(last_15_start),
			to_date=str(to_date)
		)

		for row in (last_15_result.get("invoice_list") or []):
			qty_map[customer]["qty_15"] += float(row.get("qty") or 0)
			qty_map[customer]["amount_15"] += float(row.get("invoice_value") or 0)


	# =====================================================
	# NET SALE UNDER FRANCHISE FEES
	# Sales Invoice Item where item_code = 'Franchise Services'
	# Cumulative since inception till "today" (system date when
	# report is run) - NOT bound by the from_date/to_date filters.
	# =====================================================

	franchise_customer_condition = ""

	franchise_values = {
		"companies": companies,
		"now": now_datetime()
	}

	if customer_filter:
		franchise_customer_condition = " AND si.customer = %(customer)s"
		franchise_values["customer"] = customer_filter

	franchise_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,
			SUM(
				ROUND(
					sii.net_amount + IFNULL(
						(
							SELECT SUM(
								CAST(
									JSON_UNQUOTE(
										JSON_EXTRACT(stc.item_wise_tax_detail, CONCAT('$."', sii.item_code, '"[1]'))
									) AS DECIMAL(18,2)
								)
							)
							FROM `tabSales Taxes and Charges` stc
							WHERE stc.parent = si.name
								AND stc.account_head LIKE 'Output Tax%%'
						),
						0
					)
				)
			) AS net_sale_franchise

		FROM `tabSales Invoice Item` sii

		INNER JOIN `tabSales Invoice` si
			ON si.name = sii.parent

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.creation <= %(now)s
			AND sii.item_code = 'Franchise Services'
			{franchise_customer_condition}

		GROUP BY si.customer
		""",
		franchise_values,
		as_dict=True
	)

	franchise_map = {
		d.customer: d
		for d in franchise_data
	}


	# =====================================================
	# CREDIT NOTE / DEBIT NOTE
	# From General Ledger, Voucher Type = Journal Entry only
	# Previous period: first delivery date (by company) -> from_date - 1
	# Last 15 Days: last_15_start -> to_date
	# =====================================================

	journal_note_customer_condition = ""

	if customer_filter:
		journal_note_customer_condition = " AND gle.party = %(customer)s"

	journal_note_data = frappe.db.sql(
		f"""
		SELECT
			gle.party AS customer,

			SUM(
				CASE
					WHEN gle.posting_date <= %(prev_to_date)s
						AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					THEN gle.credit
					ELSE 0
				END
			) AS credit_note,

			SUM(
				CASE
					WHEN gle.posting_date >= %(last_15_start)s
						AND gle.posting_date <= %(to_date)s
						AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					THEN gle.credit
					ELSE 0
				END
			) AS credit_note_15,

			SUM(
				CASE
					WHEN gle.posting_date <= %(prev_to_date)s
						AND gle.voucher_subtype IN ('Debit Note', 'Journal Entry')
					THEN gle.debit
					ELSE 0
				END
			) AS debit_note,

			SUM(
				CASE
					WHEN gle.posting_date >= %(last_15_start)s
						AND gle.posting_date <= %(to_date)s
						AND gle.voucher_subtype IN ('Debit Note', 'Journal Entry')
					THEN gle.debit
					ELSE 0
				END
			) AS debit_note_15

		FROM `tabGL Entry` gle

		WHERE
			gle.is_cancelled = 0
			AND gle.company IN %(companies)s
			AND gle.posting_date <= %(to_date)s
			AND gle.party_type = 'Customer'
			AND IFNULL(gle.party, '') != ''
			AND gle.voucher_type = 'Journal Entry'
			AND gle.voucher_subtype IN ('Credit Note', 'Debit Note', 'Journal Entry')
			{journal_note_customer_condition}

		GROUP BY gle.party
		""",
		sales_values,
		as_dict=True
	)

	journal_note_map = {
		d.customer: d
		for d in journal_note_data
	}


	# =====================================================
	# PAYMENT / COLLECTION
	# =====================================================

	payment_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start
	}

	payment_customer_condition = ""

	if customer_filter:
		payment_customer_condition = " AND pe.party = %(customer)s"
		payment_values["customer"] = customer_filter


	payment_data = frappe.db.sql(
		f"""
		SELECT
			pe.party AS customer,

			SUM(
				CASE
					WHEN pe.posting_date < %(last_15_start)s
					THEN pe.paid_amount
					ELSE 0
				END
			) AS previous_collection_amount,

			SUM(
				CASE
					WHEN pe.posting_date >= %(last_15_start)s
					THEN pe.paid_amount
					ELSE 0
				END
			) AS collection_15

		FROM `tabPayment Entry` pe

		WHERE
			pe.docstatus = 1
			AND pe.payment_type = 'Receive'
			AND pe.party_type = 'Customer'
			AND pe.company IN %(companies)s
			AND pe.posting_date >= %(from_date)s
			AND pe.posting_date <= %(to_date)s
			{payment_customer_condition}

		GROUP BY pe.party
		""",
		payment_values,
		as_dict=True
	)

	payment_map = {
		d.customer: d
		for d in payment_data
	}

	# =====================================================
	# PAYMENT RECEIVED (Cumulative till exact date+time when
	# report is run, using Payment Entry's creation timestamp
	# as cutoff - NOT bound by from_date/to_date filters)
	# =====================================================

	payment_received_customer_condition = ""

	payment_received_values = {
		"companies": companies
	}

	if customer_filter:
		payment_received_customer_condition = " AND gle.party = %(customer)s"
		payment_received_values["customer"] = customer_filter

	payment_received_data = frappe.db.sql(
		f"""
		SELECT
			gle.party AS customer,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Receive'
					THEN gle.credit
					ELSE 0
				END
			) AS payment_receive,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Pay'
					THEN gle.debit
					ELSE 0
				END
			) AS payment_pay,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Receive'
					THEN gle.credit
					WHEN gle.voucher_subtype = 'Pay'
					THEN -gle.debit
					ELSE 0
				END
			) AS payment_received

		FROM `tabGL Entry` gle

		WHERE
			gle.is_cancelled = 0
			AND gle.company IN %(companies)s
			AND gle.party_type = 'Customer'
			AND IFNULL(gle.party, '') != ''
			AND gle.voucher_type = 'Payment Entry'
			AND gle.voucher_subtype IN ('Receive', 'Pay')
			{payment_received_customer_condition}

		GROUP BY gle.party
		""",
		payment_received_values,
		as_dict=True
	)

	payment_received_map = {
		d.customer: d
		for d in payment_received_data
	}

	# =====================================================
	# ALL CUSTOMERS
	# =====================================================

	customers = sorted(
		set(
			list(opening_map)
			+ list(qty_map)
			+ list(franchise_map)
			+ list(journal_note_map)
			+ list(payment_map)
			+ list(payment_received_map)
		)
	)

	if not customers:
		return []


	# =====================================================
	# AGENT AND ASM FILTERING
	# =====================================================

	customer_map = get_customer_extra_fields(
		customers,
		filters
	)

	if filters.get("agent") or filters.get("asm"):

		customers = [
			customer
			for customer in customers
			if customer in customer_map
		]


	# =====================================================
	# FINAL DATA
	# =====================================================

	data = []

	for customer in customers:

		cust = customer_map.get(
			customer,
			frappe._dict()
		)

		opening = opening_map.get(
			customer,
			frappe._dict()
		)
		qty = qty_map.get(
			customer,
			frappe._dict()
		)

		franchise = franchise_map.get(
			customer,
			frappe._dict()
		)



		journal_note = journal_note_map.get(
			customer,
			frappe._dict()
		)

		payment = payment_map.get(
			customer,
			frappe._dict()
		)


		opening_stock = opening.get("opening_stock") or 0

		net_sale_franchise = franchise.get("net_sale_franchise") or 0

		sale_qty_ytd = qty.get("qty_ytd") or 0
		sale_qty_15 = qty.get("qty_15") or 0

		amount_ytd = qty.get("amount_ytd") or 0
		amount_15 = qty.get("amount_15") or 0

		credit_note = journal_note.get("credit_note") or 0
		credit_note_15 = journal_note.get("credit_note_15") or 0

		debit_note = journal_note.get("debit_note") or 0
		debit_note_15 = journal_note.get("debit_note_15") or 0

		previous_collection_amount = (
			payment.get("previous_collection_amount") or 0
		)

		collection_15 = (
			payment.get("collection_15") or 0
		)


		payment_rec = payment_received_map.get(
			customer,
			frappe._dict()
		)

		payment_received = payment_rec.get("payment_received") or 0

		collectable_amount = (
			net_sale_franchise
			+ amount_ytd
			+ debit_note
			- credit_note
			- payment_received
		)


		collectable_amount_15 = (
			amount_15
			+ debit_note_15
			- credit_note_15
		)


		total_collectable_amount = (
			collectable_amount
			+ collectable_amount_15
		)





		data.append({
			"customer_name": customer,
			"agent": cust.get("custom_agent"),
			"asm": cust.get("asm_name"),

			"net_sale_franchise": net_sale_franchise,

			"sale_qty_ytd": sale_qty_ytd,
			"amount_ytd": amount_ytd,

			"credit_note": credit_note,
			"debit_note": debit_note,

			"payment_received": payment_received,
			"collectable_amount": collectable_amount,

			"sale_qty_15": sale_qty_15,
			"amount_15": amount_15,

			"credit_note_15": credit_note_15,
			"debit_note_15": debit_note_15,

			"collectable_amount_15": collectable_amount_15,

			"total_collectable_amount": total_collectable_amount

			
		})


	return data

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		SELECT name, customer_name
		FROM `tabCustomer`
		WHERE disabled = 0
			AND (
				name LIKE %(txt)s
				OR customer_name LIKE %(txt)s
			)
		ORDER BY
			CASE WHEN customer_name LIKE %(start_txt)s THEN 0 ELSE 1 END,
			customer_name
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"txt": f"%{txt}%",
			"start_txt": f"{txt}%",
			"start": start,
			"page_len": page_len
		}
	)