# Copyright (c) 2026
# Collection Report - Script Report

import frappe
from frappe import _
from frappe.utils import add_days, getdate


def execute(filters=None):
	filters = filters or {}
	validate_filters(filters)

	companies = get_counter_companies(filters)

	if not companies:
		frappe.msgprint(_("No companies found."))
		return [], []

	return get_columns(), get_data(filters, companies)


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


def get_customer_extra_fields(customers):
	if not customers:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT
			c.name,
			c.custom_agent,
			u.full_name AS asm_name
		FROM `tabCustomer` c
		LEFT JOIN `tabUser` u
			ON u.name = c.account_manager
		WHERE c.name IN %(customers)s
		""",
		{"customers": customers},
		as_dict=True
	)

	return {r.name: r for r in rows}


def get_columns():
	return [
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200,
		},
		{
			"label": _("Agent"),
			"fieldname": "agent",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("ASM"),
			"fieldname": "asm",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Opening Amount"),
			"fieldname": "opening_stock",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Credit Note"),
			"fieldname": "credit_note",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Debit Note"),
			"fieldname": "debit_note",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Previous Sale Qty"),
			"fieldname": "sale_qty_ytd",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Previous Sale Amount"),
			"fieldname": "amount_ytd",
			"fieldtype": "Currency",
			"width": 170,
		},
		{
			"label": _("Payment Rec"),
			"fieldname": "payment_received",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Previous Collection Amount"),
			"fieldname": "previous_collection_amount",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Last 15 Days Sale Qty"),
			"fieldname": "sale_qty_15",
			"fieldtype": "Float",
			"width": 160,
		},
		{
			"label": _("Last 15 Days Sale Amount"),
			"fieldname": "amount_15",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Last 15 Days Collection Amount"),
			"fieldname": "collection_15",
			"fieldtype": "Currency",
			"width": 190,
		},
		{
			"label": _("Credit Note (Last 15 Days)"),
			"fieldname": "credit_note_15",
			"fieldtype": "Currency",
			"width": 170,
		},
		{
			"label": _("Debit Note (Last 15 Days)"),
			"fieldname": "debit_note_15",
			"fieldtype": "Currency",
			"width": 170,
		},
		{
			"label": _("Collectable Amount Last 15 Days"),
			"fieldname": "collectable_amount_15",
			"fieldtype": "Currency",
			"width": 210,
		},
		{
			"label": _("Total Collectable Amount"),
			"fieldname": "total_collectable_amount",
			"fieldtype": "Currency",
			"width": 190,
		},
		{
			"label": _("Pending"),
			"fieldname": "pending",
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters, companies):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	last_15_start = add_days(to_date, -14)

	customer_filter = filters.get("customer")

	sales_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start,
	}

	customer_condition = ""

	if customer_filter:
		customer_condition = " AND si.customer = %(customer)s"
		sales_values["customer"] = customer_filter

	
	opening_sales_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,

			SUM(
				CASE
					WHEN IFNULL(si.is_return, 0) = 0
					THEN si.grand_total
					ELSE 0
				END
			) AS total_sales,

			ABS(
				SUM(
					CASE
						WHEN IFNULL(si.is_return, 0) = 1
						THEN si.grand_total
						ELSE 0
					END
				)
			) AS credit_note

		FROM `tabSales Invoice` si

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.posting_date < %(from_date)s
			{customer_condition}

		GROUP BY si.customer
		""",
		sales_values,
		as_dict=True
	)


	opening_payment_values = {
		"companies": companies,
		"from_date": from_date,
	}

	opening_payment_customer_condition = ""

	if customer_filter:
		opening_payment_customer_condition = " AND pe.party = %(customer)s"
		opening_payment_values["customer"] = customer_filter


	opening_payment_data = frappe.db.sql(
		f"""
		SELECT
			pe.party AS customer,
			SUM(pe.paid_amount) AS total_payment

		FROM `tabPayment Entry` pe

		WHERE
			pe.docstatus = 1
			AND pe.payment_type = 'Receive'
			AND pe.party_type = 'Customer'
			AND pe.company IN %(companies)s
			AND pe.posting_date < %(from_date)s
			{opening_payment_customer_condition}

		GROUP BY pe.party
		""",
		opening_payment_values,
		as_dict=True
	)


	opening_sales_map = {
		d.customer: d
		for d in opening_sales_data
	}

	opening_payment_map = {
		d.customer: d
		for d in opening_payment_data
	}


	opening_map = {}

	opening_customers = set(
		list(opening_sales_map)
		+ list(opening_payment_map)
	)

	for customer in opening_customers:

		sales = opening_sales_map.get(customer, frappe._dict())
		payment = opening_payment_map.get(customer, frappe._dict())

		total_sales = sales.get("total_sales") or 0
		credit_note = sales.get("credit_note") or 0
		total_payment = payment.get("total_payment") or 0

		opening_stock = (
			total_sales
			- credit_note
			- total_payment
		)

		opening_map[customer] = frappe._dict({
			"opening_stock": opening_stock
		})

	
	qty_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,

			SUM(
				CASE
					WHEN si.posting_date < %(last_15_start)s
					THEN sii.qty
					ELSE 0
				END
			) AS qty_ytd,

			SUM(
				CASE
					WHEN si.posting_date >= %(last_15_start)s
					THEN sii.qty
					ELSE 0
				END
			) AS qty_15

		FROM `tabSales Invoice` si

		INNER JOIN `tabSales Invoice Item` sii
			ON sii.parent = si.name

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.posting_date >= %(from_date)s
			AND si.posting_date <= %(to_date)s
			AND IFNULL(si.is_return, 0) = 0
			{customer_condition}

		GROUP BY si.customer
		""",
		sales_values,
		as_dict=True
	)

	qty_map = {d.customer: d for d in qty_data}

	
	amount_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,

			SUM(
				CASE
					WHEN si.posting_date < %(last_15_start)s
					THEN si.grand_total
					ELSE 0
				END
			) AS amount_ytd,

			SUM(
				CASE
					WHEN si.posting_date >= %(last_15_start)s
					THEN si.grand_total
					ELSE 0
				END
			) AS amount_15

		FROM `tabSales Invoice` si

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.posting_date >= %(from_date)s
			AND si.posting_date <= %(to_date)s
			AND IFNULL(si.is_return, 0) = 0
			{customer_condition}

		GROUP BY si.customer
		""",
		sales_values,
		as_dict=True
	)

	amount_map = {d.customer: d for d in amount_data}

	
	credit_note_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,

			ABS(
				SUM(
					CASE
						WHEN si.posting_date < %(last_15_start)s
						THEN si.grand_total
						ELSE 0
					END
				)
			) AS credit_note,

			ABS(
				SUM(
					CASE
						WHEN si.posting_date >= %(last_15_start)s
						THEN si.grand_total
						ELSE 0
					END
				)
			) AS credit_note_15

		FROM `tabSales Invoice` si

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.posting_date >= %(from_date)s
			AND si.posting_date <= %(to_date)s
			AND IFNULL(si.is_return, 0) = 1
			{customer_condition}

		GROUP BY si.customer
		""",
		sales_values,
		as_dict=True
	)

	credit_note_map = {d.customer: d for d in credit_note_data}

	debit_note_data = frappe.db.sql(
		f"""
		SELECT
			jea.party AS customer,

			SUM(
				CASE
					WHEN je.posting_date < %(last_15_start)s
					THEN jea.debit_in_account_currency
					ELSE 0
				END
			) AS debit_note,

			SUM(
				CASE
					WHEN je.posting_date >= %(last_15_start)s
				THEN jea.debit_in_account_currency
					ELSE 0
				END
			) AS debit_note_15

		FROM `tabJournal Entry` je

		INNER JOIN `tabJournal Entry Account` jea
			ON jea.parent = je.name

		WHERE
			je.docstatus = 1
			AND je.company IN %(companies)s
			AND je.posting_date >= %(from_date)s
			AND je.posting_date <= %(to_date)s
			AND jea.party_type = 'Customer'
			AND IFNULL(jea.party, '') != ''
			AND jea.debit_in_account_currency > 0
			{customer_condition.replace("si.customer", "jea.party")}

		GROUP BY jea.party
		""",
		sales_values,
		as_dict=True
	)

	debit_note_map = {
		d.customer: d
		for d in debit_note_data
	}

	payment_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start,
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

	payment_map = {d.customer: d for d in payment_data}

	# All Customers
	customers = sorted(
		set(
			list(opening_map)
			+ list(qty_map)
			+ list(amount_map)
			+ list(credit_note_map)
			+ list(payment_map)
		)
	)

	if not customers:
		return []

	customer_map = get_customer_extra_fields(customers)

	data = []

	for customer in customers:
		cust = customer_map.get(customer, frappe._dict())
		opening = opening_map.get(customer, frappe._dict())
		qty = qty_map.get(customer, frappe._dict())
		amt = amount_map.get(customer, frappe._dict())
		credit = credit_note_map.get(customer, frappe._dict())
		debit = debit_note_map.get(customer, frappe._dict())
		payment = payment_map.get(customer, frappe._dict())

		opening_stock = opening.get("opening_stock") or 0

		sale_qty_ytd = qty.get("qty_ytd") or 0
		sale_qty_15 = qty.get("qty_15") or 0

		amount_ytd = amt.get("amount_ytd") or 0
		amount_15 = amt.get("amount_15") or 0

		credit_note = credit.get("credit_note") or 0
		credit_note_15 = credit.get("credit_note_15") or 0

		debit_note = debit.get("debit_note") or 0
		debit_note_15 = debit.get("debit_note_15") or 0

		previous_collection_amount = (
			payment.get("previous_collection_amount") or 0
		)

		collection_15 = payment.get("collection_15") or 0

		payment_received = (
			previous_collection_amount
			+ collection_15
		)

		collectable_amount_15 = (
			amount_15
			- credit_note_15
			+ debit_note_15
		)

		total_collectable_amount = (
			opening_stock
			+ amount_ytd
			- credit_note
			+ debit_note
			+ collectable_amount_15
		)

		pending = (
			total_collectable_amount
			- payment_received
		)

		data.append({
			"customer_name": customer,
			"agent": cust.get("custom_agent"),
			"asm": cust.get("asm_name"),
			"opening_stock": opening_stock,
			"credit_note": credit_note,
			"debit_note": debit_note,
			"sale_qty_ytd": sale_qty_ytd,
			"amount_ytd": amount_ytd,
			"payment_received": payment_received,
			"previous_collection_amount": previous_collection_amount,
			"sale_qty_15": sale_qty_15,
			"amount_15": amount_15,
			"collection_15": collection_15,
			"credit_note_15": credit_note_15,
			"debit_note_15": debit_note_15,
			"collectable_amount_15": collectable_amount_15,
			"total_collectable_amount": total_collectable_amount,
			"pending": pending,
		})

	return data