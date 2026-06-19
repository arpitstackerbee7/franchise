# Copyright (c) 2026
# Collection Report - Script Report
#
# PLACEHOLDERS TO CONFIRM:
# 1. "custom_agent" - Data field on Customer for Agent. Confirm fieldname.
# 2. "custom_asm" - Link field on Customer pointing to Employee, for ASM. Confirm this
#    field exists; create it if not (Link, options: Employee).
# 3. Collection/Pending use Sales Invoice's outstanding_amount, which the framework keeps
#    correct automatically for FIFO-style payment allocation and any Credit Note / Sales
#    Return linked via return_against. If Debit/Credit Notes in your setup are standalone
#    Journal Entries NOT linked to a specific Sales Invoice, those won't be reflected here.

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
	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))


def get_counter_companies(filters):
	company = filters.get("company")
	company_filters = {}
	if company:
		company_filters["name"] = company
	return frappe.get_all("Company", filters=company_filters, pluck="name")


def get_customer_extra_fields(customers):
	if not customers:
		return {}
	rows = frappe.db.sql("""
		select
			c.name,
			c.custom_agent,
			u.full_name as asm_name
		from `tabCustomer` c
		left join `tabUser` u on u.name = c.account_manager
		where c.name in %(customers)s
	""", {"customers": customers}, as_dict=True)
	return {r.name: r for r in rows}


def get_columns():
	return [
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Link",
			"options": "Customer", "width": 200},
		{"label": _("Agent"), "fieldname": "agent", "fieldtype": "Data", "width": 150},
		{"label": _("ASM (TL)"), "fieldname": "asm", "fieldtype": "Data", "width": 150},
		{"label": _("Sale Qty YTD"), "fieldname": "sale_qty_ytd", "fieldtype": "Float", "width": 110},
		{"label": _("Collection Amount YTD"), "fieldname": "amount_ytd", "fieldtype": "Currency", "width": 160},
		{"label": _("Sale Qty (Last 15 Days)"), "fieldname": "sale_qty_15", "fieldtype": "Float", "width": 150},
		{"label": _("Collection Amount (Last 15 Days)"), "fieldname": "amount_15", "fieldtype": "Currency", "width": 180},
		{"label": _("Total Sale Qty"), "fieldname": "total_sale_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Total Collection Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 170},
		{"label": _("Collection"), "fieldname": "collection", "fieldtype": "Currency", "width": 120},
		{"label": _("Pending"), "fieldname": "pending", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters, companies):
	to_date = getdate(filters.get("to_date"))
	from_date = filters.get("from_date")
	last_15_start = add_days(to_date, -14)

	conditions = "si.docstatus = 1 and si.company in %(companies)s and si.posting_date <= %(to_date)s"
	values = {"companies": companies, "to_date": to_date, "last_15_start": last_15_start}

	if from_date:
		conditions += " and si.posting_date >= %(from_date)s"
		values["from_date"] = from_date

	if filters.get("customer"):
		conditions += " and si.customer = %(customer)s"
		values["customer"] = filters["customer"]

	# Qty split
	qty_data = frappe.db.sql(f"""
		select
			si.customer as customer,
			sum(case when si.posting_date < %(last_15_start)s then sii.qty else 0 end) as qty_ytd,
			sum(case when si.posting_date >= %(last_15_start)s then sii.qty else 0 end) as qty_15
		from `tabSales Invoice` si
		inner join `tabSales Invoice Item` sii on sii.parent = si.name
		where {conditions}
		group by si.customer
	""", values, as_dict=True)

	# Amount split
	amount_data = frappe.db.sql(f"""
		select
			si.customer as customer,
			sum(case when si.posting_date < %(last_15_start)s then si.grand_total else 0 end) as amount_ytd,
			sum(case when si.posting_date >= %(last_15_start)s then si.grand_total else 0 end) as amount_15
		from `tabSales Invoice` si
		where {conditions}
		group by si.customer
	""", values, as_dict=True)

	# Collection = actual payments received from customer in the date range
	payment_conditions = "pe.docstatus = 1 and pe.payment_type = 'Receive' and pe.company in %(companies)s and pe.posting_date <= %(to_date)s"
	payment_values = {"companies": companies, "to_date": to_date}

	if from_date:
		payment_conditions += " and pe.posting_date >= %(from_date)s"
		payment_values["from_date"] = from_date

	if filters.get("customer"):
		payment_conditions += " and pe.party = %(customer)s"
		payment_values["customer"] = filters["customer"]

	collection_data = frappe.db.sql(f"""
		select
			pe.party as customer,
			sum(pe.paid_amount) as collection
		from `tabPayment Entry` pe
		where pe.party_type = 'Customer'
		and {payment_conditions}
		group by pe.party
	""", payment_values, as_dict=True)

	qty_map = {d.customer: d for d in qty_data}
	amount_map = {d.customer: d for d in amount_data}
	collection_map = {d.customer: d for d in collection_data}
	customers = sorted(set(list(qty_map) + list(amount_map)))

	if not customers:
		return []

	customer_map = get_customer_extra_fields(customers)

	data = []
	for customer in customers:
		qty = qty_map.get(customer, frappe._dict())
		amt = amount_map.get(customer, frappe._dict())
		cust = customer_map.get(customer, frappe._dict())
		col = collection_map.get(customer, frappe._dict())

		sale_qty_ytd = qty.get("qty_ytd") or 0
		sale_qty_15 = qty.get("qty_15") or 0
		amount_ytd = amt.get("amount_ytd") or 0
		amount_15 = amt.get("amount_15") or 0
		total_amount = amount_ytd + amount_15
		collection = col.get("collection") or 0
		pending = total_amount - collection

		data.append({
			"customer_name": customer,
			"agent": cust.get("custom_agent"),
			"asm": cust.get("asm_name"),
			"sale_qty_ytd": sale_qty_ytd,
			"amount_ytd": amount_ytd,
			"sale_qty_15": sale_qty_15,
			"amount_15": amount_15,
			"total_sale_qty": sale_qty_ytd + sale_qty_15,
			"total_amount": total_amount,
			"collection": collection,
			"pending": pending,
		})

	return data