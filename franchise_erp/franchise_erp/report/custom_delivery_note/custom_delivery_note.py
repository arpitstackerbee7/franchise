# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


import json

import frappe
from frappe import _
from frappe.query_builder.terms import ValueWrapper

# ============================================================
# CONFIG
# ============================================================

# Custom Sales Invoice report ka python module path (supplier logic reuse karne ke liye).
# "your_app" aur "your_module" ko apne app/module ke naam se badlo.
# Agar import fail hua to Supplier Name / Supplier Agent columns khali rahenge.
SALES_INVOICE_REPORT_MODULE = (
	"franchise_erp.franchise_erp.report.custom_sales_invoice.custom_sales_invoice"
)

# Delivery Note Item par ye custom fields ho to wahi use honge,
# warna Item master se uthaye jayenge (agar Item me hon).
ITEM_FIELDS_ON_DN_ITEM = [
	"custom_bottom_fabric",
	"custom_dupatta_fabric",
	"custom_top_fabric",
	"custom_count_of_pcs",
]

# (report fieldname, [candidate fieldnames])
# STD / WSP / MRP ke fieldnames yahan confirm karke badlo.
PRICE_FIELDS = {
	"custom_std": ["custom_std", "custom_standard_rate"],
	"custom_wsp": ["custom_wsp", "custom_wholesale_price"],
	"custom_mrp": ["custom_mrp"],
}


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data


# ============================================================
# COLUMNS
# ============================================================

def get_columns():
	return [
		{"label": _("Delivery Note"), "fieldname": "name", "fieldtype": "Link", "options": "Delivery Note", "width": 160},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": _("Customer Agent"), "fieldname": "customer_agent", "fieldtype": "Link", "options": "Supplier", "width": 180},
		{"label": _("Customer Group"), "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group", "width": 180},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Link", "options": "Supplier", "width": 180},
		{"label": _("Supplier Agent"), "fieldname": "supplier_agent", "fieldtype": "Link", "options": "Supplier", "width": 180},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Class Name"), "fieldname": "class_name", "fieldtype": "Data", "width": 140},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Data", "width": 180},
		{"label": _("Quantity"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "options": "currency", "width": 110},
		# ---- NEW COLUMNS (ticket #0573) ----
		{"label": _("STD"), "fieldname": "custom_std", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("WSP"), "fieldname": "custom_wsp", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("MRP"), "fieldname": "custom_mrp", "fieldtype": "Currency", "options": "currency", "width": 120},
		# ------------------------------------
		{"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "width": 90},
		{"label": _("Bottom Fabric"), "fieldname": "custom_bottom_fabric", "fieldtype": "Data", "width": 160},
		{"label": _("Dupatta Fabric"), "fieldname": "custom_dupatta_fabric", "fieldtype": "Data", "width": 170},
		{"label": _("Top Fabric"), "fieldname": "custom_top_fabric", "fieldtype": "Data", "width": 160},
		{"label": _("Count Of Pcs"), "fieldname": "custom_count_of_pcs", "fieldtype": "Data", "width": 120},
		{"label": _("Sup Design No."), "fieldname": "sup_design_no", "fieldtype": "Data", "width": 170},
	]


# ============================================================
# DATA
# ============================================================

def _resolve_field(doctype, candidates):
	for f in candidates:
		if frappe.db.has_column(doctype, f):
			return f
	return None


def get_data(filters):
	dn = frappe.qb.DocType("Delivery Note")
	dni = frappe.qb.DocType("Delivery Note Item")
	item = frappe.qb.DocType("Item")
	customer = frappe.qb.DocType("Customer")

	selects = [
		# ---------------- DELIVERY NOTE ----------------
		dn.name,
		dn.posting_date,
		dn.customer,
		dn.customer_name,
		dn.company,
		dn.currency,
		dn.is_return,
		dn.return_against,
		dn.net_total.as_("gross_amount"),
		dn.rounded_total.as_("net_amount"),
		# ---------------- CUSTOMER ----------------
		customer.custom_agent.as_("customer_agent"),
		customer.customer_group.as_("customer_group"),
		# ---------------- DELIVERY NOTE ITEM ----------------
		dni.name.as_("sales_invoice_item"),  # key name supplier logic ke saath same rakha hai
		dni.item_code,
		dni.item_name,
		dni.serial_no,
		dni.serial_and_batch_bundle,
		dni.batch_no,
		dni.qty,
		dni.rate,
		dni.amount,
		# ---------------- ITEM ----------------
		item.custom_sup_design_no.as_("sup_design_no"),
	]

	# class name (Delivery Note par ho to)
	if frappe.db.has_column("Delivery Note", "custom_class_name"):
		selects.append(dn.custom_class_name.as_("class_name"))
	else:
		selects.append(ValueWrapper(None).as_("class_name"))

	# fabric / count fields
	for f in ITEM_FIELDS_ON_DN_ITEM:
		if frappe.db.has_column("Delivery Note Item", f):
			selects.append(dni[f].as_(f))
		elif frappe.db.has_column("Item", f):
			selects.append(item[f].as_(f))
		else:
			selects.append(ValueWrapper(None).as_(f))

	# STD / WSP / MRP : pehle Delivery Note Item, phir Item master
	for out_name, candidates in PRICE_FIELDS.items():
		dn_field = _resolve_field("Delivery Note Item", candidates)
		item_field = _resolve_field("Item", candidates)

		if dn_field:
			selects.append(dni[dn_field].as_(out_name))
		elif item_field:
			selects.append(item[item_field].as_(out_name))
		else:
			selects.append(ValueWrapper(0).as_(out_name))

	query = (
		frappe.qb.from_(dn)
		.inner_join(dni).on(dni.parent == dn.name)
		.left_join(item).on(item.name == dni.item_code)
		.left_join(customer).on(customer.name == dn.customer)
		.select(*selects)
		.where(dn.docstatus == 1)
	)

	# ---------------- FILTERS ----------------
	if filters.get("from_date"):
		query = query.where(dn.posting_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(dn.posting_date <= filters.get("to_date"))

	customers = get_filter_list(filters.get("customer"))
	if customers:
		query = query.where(dn.customer.isin(customers))

	customer_groups = get_filter_list(filters.get("customer_group"))
	if customer_groups:
		query = query.where(customer.customer_group.isin(customer_groups))

	class_names = get_filter_list(filters.get("class_name"))
	if class_names and frappe.db.has_column("Delivery Note", "custom_class_name"):
		query = query.where(dn.custom_class_name.isin(class_names))

	dn_ids = get_filter_list(filters.get("delivery_note") or filters.get("id"))
	if dn_ids:
		query = query.where(dn.name.isin(dn_ids))

	agents = get_filter_list(filters.get("agent"))
	if agents:
		query = query.where(customer.custom_agent.isin(agents))

	data = query.orderby(dn.posting_date, order=frappe.qb.desc).run(as_dict=True)

	# ---------------- SUPPLIER LOOKUP (reuse) ----------------
	add_supplier_columns(data)

	return data


def add_supplier_columns(data):
	try:
		module = frappe.get_attr(SALES_INVOICE_REPORT_MODULE + ".bulk_resolve_suppliers")
		agent_fn = frappe.get_attr(SALES_INVOICE_REPORT_MODULE + ".get_supplier_agent")
	except Exception:
		frappe.log_error(
			title="Custom Delivery Note: supplier logic import failed",
			message=f"Check SALES_INVOICE_REPORT_MODULE = {SALES_INVOICE_REPORT_MODULE}",
		)
		for row in data:
			row["supplier_name"] = None
			row["supplier_agent"] = None
		return

	frappe.local.cs_supplier_cache = {}
	suppliers = module(data)

	for row in data:
		supplier = suppliers.get(row.get("sales_invoice_item"))
		row["supplier_name"] = supplier
		row["supplier_agent"] = agent_fn(supplier)


# ============================================================
# FILTER LIST
# ============================================================

def get_filter_list(value):
	if not value:
		return []

	if isinstance(value, list):
		return value

	if isinstance(value, str):
		try:
			parsed_value = json.loads(value)
			if isinstance(parsed_value, list):
				return parsed_value
		except Exception:
			pass

		return [x.strip() for x in value.split(",") if x.strip()]

	return [value]