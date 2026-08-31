import frappe
from frappe import _
import json


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [

		# =========================
		# SALES INVOICE DETAILS
		# =========================

		{
			"label": _("Sales Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Class Name"),
			"fieldname": "class_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},

		# =========================
		# ITEM DETAILS
		# =========================

		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Serial No"),
			"fieldname": "serial_no",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Data",
			"width": 90,
		},

		# =========================
		# ORIGINAL CUSTOM FIELDS
		# =========================

		{
			"label": _("Bottom Fabric"),
			"fieldname": "custom_bottom_fabric",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Dupatta Fabric"),
			"fieldname": "custom_dupatta_fabric",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Top Fabric"),
			"fieldname": "custom_top_fabric",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("MRP"),
			"fieldname": "custom_mrp",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Count Of Pcs"),
			"fieldname": "custom_count_of_pcs",
			"fieldtype": "Data",
			"width": 120,
		},

		# =========================
		# SUPPLIER DETAILS
		# =========================

		{
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Sup Design No."),
			"fieldname": "sup_design_no",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Agent Supplier"),
			"fieldname": "agent_supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
	]


def get_data(filters):

	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	item = frappe.qb.DocType("Item")

	# =========================
	# MAIN QUERY
	#
	# Sales Invoice Item
	#       ↓
	# Item Master
	#       ↓
	# custom_sup_design_no
	# =========================

	query = (
		frappe.qb.from_(si)
		.inner_join(sii)
		.on(sii.parent == si.name)

		.left_join(item)
		.on(item.name == sii.item_code)

		.select(

			# =========================
			# SALES INVOICE FIELDS
			# =========================

			si.name,
			si.posting_date,
			si.customer,
			si.customer_name,
			si.custom_class_name.as_("class_name"),
			si.company,
			si.grand_total,
			si.currency,

			# =========================
			# SALES INVOICE ITEM FIELDS
			# =========================

			sii.name.as_("sales_invoice_item"),
			sii.item_code,
			sii.item_name,
			sii.serial_no,
			sii.qty,
			sii.rate,
			sii.amount,

			# =========================
			# CUSTOM FIELDS FROM SI ITEM
			# =========================

			sii.custom_bottom_fabric,
			sii.custom_dupatta_fabric,
			sii.custom_top_fabric,
			sii.custom_mrp,
			sii.custom_count_of_pcs,

			# =========================
			# SUP DESIGN NO FROM ITEM MASTER
			# =========================

			item.custom_sup_design_no.as_("sup_design_no"),
		)

		.where(si.docstatus == 1)
	)

	# =========================
	# DATE FILTER
	# =========================

	if filters.get("from_date"):
		query = query.where(
			si.posting_date >= filters.get("from_date")
		)

	if filters.get("to_date"):
		query = query.where(
			si.posting_date <= filters.get("to_date")
		)

	# =========================
	# CUSTOMER FILTER
	# =========================

	customers = get_filter_list(
		filters.get("customer")
	)

	if customers:
		query = query.where(
			si.customer.isin(customers)
		)

	# =========================
	# CLASS NAME FILTER
	# =========================

	class_names = get_filter_list(
		filters.get("class_name")
	)

	if class_names:
		query = query.where(
			si.custom_class_name.isin(class_names)
		)

	# =========================
	# SALES INVOICE / ID FILTER
	# =========================

	invoice_ids = get_filter_list(
		filters.get("sales_invoice")
		or filters.get("id")
	)

	if invoice_ids:
		query = query.where(
			si.name.isin(invoice_ids)
		)

	# =========================
	# RUN MAIN QUERY
	# =========================

	data = query.orderby(
		si.posting_date,
		order=frappe.qb.desc
	).run(as_dict=True)

	# =====================================================
	# SUPPLIER + AGENT SUPPLIER
	#
	# Sales Invoice Item Serial No
	#            ↓
	# Purchase Receipt Item
	#            ↓
	# Purchase Receipt Supplier
	#            ↓
	# Supplier.custom_agent_supplier
	# =====================================================

	for row in data:

		row["supplier_name"] = None
		row["agent_supplier"] = None

		# Serial No nahi hai to GRN se supplier nahi milega
		if not row.get("serial_no"):
			continue

		supplier_data = frappe.db.sql(
			"""
			SELECT
				pr.supplier AS supplier_name,
				s.custom_agent_supplier AS agent_supplier

			FROM
				`tabPurchase Receipt Item` pri

			INNER JOIN
				`tabPurchase Receipt` pr
				ON pr.name = pri.parent

			LEFT JOIN
				`tabSupplier` s
				ON s.name = pr.supplier

			WHERE
				pr.docstatus = 1

				AND pri.item_code = %(item_code)s

				AND (
					pri.serial_no = %(serial_no)s

					OR FIND_IN_SET(
						%(serial_no)s,

						REPLACE(
							REPLACE(
								pri.serial_no,
								'\\n',
								','
							),
							'\\r',
							''
						)
					) > 0
				)

			ORDER BY
				pr.posting_date DESC

			LIMIT 1
			""",
			{
				"item_code": row.get("item_code"),
				"serial_no": row.get("serial_no"),
			},
			as_dict=True,
		)

		if supplier_data:

			row["supplier_name"] = supplier_data[0].get(
				"supplier_name"
			)

			row["agent_supplier"] = supplier_data[0].get(
				"agent_supplier"
			)

	# =========================
	# AGENT FILTER
	#
	# Filter based on Supplier's
	# custom_agent_supplier
	# =========================

	agents = get_filter_list(
		filters.get("agent_supplier")
		or filters.get("agent")
	)

	if agents:
		data = [
			row
			for row in data
			if row.get("agent_supplier") in agents
		]

	return data


def get_filter_list(value):

	if not value:
		return []

	# Already a list
	if isinstance(value, list):
		return value

	# MultiSelectList usually sends string
	if isinstance(value, str):

		# Try JSON list
		try:
			parsed_value = json.loads(value)

			if isinstance(parsed_value, list):
				return parsed_value

		except Exception:
			pass

		# Comma-separated values
		return [
			x.strip()
			for x in value.split(",")
			if x.strip()
		]

	return [value]