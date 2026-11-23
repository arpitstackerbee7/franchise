# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "supplier", "label": _("Supplier ID"), "fieldtype": "Link", "options": "Supplier", "width": 150},
		{"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "supplier_group", "label": _("Supplier Group"), "fieldtype": "Link", "options": "Supplier Group", "width": 150},
		{"fieldname": "supplier_type", "label": _("Supplier Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "city", "label": _("City"), "fieldtype": "Data", "width": 150},
		{"fieldname": "state", "label": _("State"), "fieldtype": "Data", "width": 130},
		{"fieldname": "pincode", "label": _("Pincode"), "fieldtype": "Data", "width": 90},
		{"fieldname": "country", "label": _("Country"), "fieldtype": "Link", "options": "Country", "width": 130},
		{"fieldname": "tax_id", "label": _("Tax ID"), "fieldtype": "Data", "width": 150},
		{"fieldname": "default_currency", "label": _("Default Currency"), "fieldtype": "Link", "options": "Currency", "width": 120},
		{"fieldname": "payment_terms", "label": _("Payment Terms"), "fieldtype": "Link", "options": "Payment Terms Template", "width": 180},
		{"fieldname": "website", "label": _("Website"), "fieldtype": "Data", "width": 180},
		{"fieldname": "email_id", "label": _("Email"), "fieldtype": "Data", "width": 180},
		{"fieldname": "mobile_no", "label": _("Mobile No"), "fieldtype": "Data", "width": 140},
		{"fieldname": "disabled", "label": _("Disabled"), "fieldtype": "Check", "width": 90},
		{"fieldname": "creation", "label": _("Created On"), "fieldtype": "Datetime", "width": 150},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("supplier"):
		conditions.append("s.name = %(supplier)s")
		values["supplier"] = filters.supplier

	if filters.get("supplier_group"):
		conditions.append("s.supplier_group = %(supplier_group)s")
		values["supplier_group"] = filters.supplier_group

	if filters.get("supplier_type"):
		conditions.append("s.supplier_type = %(supplier_type)s")
		values["supplier_type"] = filters.supplier_type

	if filters.get("country"):
		conditions.append("s.country = %(country)s")
		values["country"] = filters.country

	if filters.get("city"):
		conditions.append("addr.city LIKE %(city)s")
		values["city"] = f"%{filters.city}%"

	# Works with both Check (1/0) and Select (Yes/No) filter types
	if filters.get("disabled") in (1, "1", "Yes"):
		conditions.append("s.disabled = 1")
	elif filters.get("disabled") == "No":
		conditions.append("s.disabled = 0")

	where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

	return frappe.db.sql(
		f"""
		SELECT
			s.name AS supplier,
			s.supplier_name,
			s.supplier_group,
			s.supplier_type,
			GROUP_CONCAT(DISTINCT addr.city SEPARATOR ', ') AS city,
			GROUP_CONCAT(DISTINCT addr.state SEPARATOR ', ') AS state,
			GROUP_CONCAT(DISTINCT addr.pincode SEPARATOR ', ') AS pincode,
			s.country,
			s.tax_id,
			s.default_currency,
			s.payment_terms,
			s.website,
			s.email_id,
			s.mobile_no,
			s.disabled,
			s.creation
		FROM `tabSupplier` s
		LEFT JOIN `tabDynamic Link` dl
			ON dl.link_doctype = 'Supplier'
			AND dl.link_name = s.name
			AND dl.parenttype = 'Address'
			AND dl.parentfield = 'links'
		LEFT JOIN `tabAddress` addr
			ON addr.name = dl.parent
			AND IFNULL(addr.disabled, 0) = 0
		{where_clause}
		GROUP BY s.name
		ORDER BY s.supplier_name ASC
		""",
		values,
		as_dict=True,
	)