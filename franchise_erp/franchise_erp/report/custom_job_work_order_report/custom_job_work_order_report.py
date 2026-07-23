# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if filters.get("from_date") and filters.get("to_date"):
		if filters.from_date >= filters.to_date:
			frappe.throw(_("To Date must be greater than From Date"))

	data = []
	columns = get_columns(filters)
	get_data(data, filters)

	return columns, data


def get_columns(filters):
	return [
		{
			"label": _("ID"),
			"fieldname": "id",
			"fieldtype": "Link",
			"options": filters.order_type,
			"width": 160,
		},
		{
			"label": _("Subcontracting Purchase Order"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 180,
		},
		{
			"label": _("Job Worker Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Finished Good Item"),
			"fieldname": "fg_item_code",
			"fieldtype": "Link",
			"fieldname": "fg_item_code",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Required Quantity"),
			"fieldname": "required_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Received Quantity"),
			"fieldname": "received_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Pending Quantity"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_data(data, filters):
	orders = get_subcontract_orders(filters)
	orders_name = [order.name for order in orders]

	subcontracted_items = get_subcontract_order_supplied_item(
		filters.order_type, orders_name
	)

	for item in subcontracted_items:
		for order in orders:
			if order.name == item.parent and item.received_qty < item.qty:
				row = {
					"id": order.name,
					"purchase_order": order.purchase_order,
					"supplier_name": order.supplier_name,
					"company": order.company,
					"date": order.transaction_date,
					"grand_total": order.base_grand_total,
					"status": order.status,
					"fg_item_code": item.item_code,
					"item_name": item.item_name,
					"required_qty": item.qty,
					"received_qty": item.received_qty,
					"pending_qty": item.qty - item.received_qty,
				}

				data.append(row)


def get_subcontract_orders(filters):
	record_filters = [
		["supplier", "=", filters.supplier],
		["transaction_date", "<=", filters.to_date],
		["transaction_date", ">=", filters.from_date],
		["docstatus", "=", 1],
	]

	if filters.order_type == "Purchase Order":
		record_filters.append(["is_old_subcontracting_flow", "=", 1])

	return frappe.get_all(
		filters.order_type,
		filters=record_filters,
		fields=[
			"name",
			"purchase_order",
			"supplier",
			"supplier_name",
			"company",
			"transaction_date",
			"base_grand_total",
			"status",
		],
	)


def get_subcontract_order_supplied_item(order_type, orders):
	return frappe.get_all(
		f"{order_type} Item",
		filters=[("parent", "IN", orders)],
		fields=[
			"parent",
			"item_code",
			"item_name",
			"qty",
			"received_qty",
		],
	)