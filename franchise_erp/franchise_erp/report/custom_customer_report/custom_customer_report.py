import frappe
from frappe import _

# Change these if the custom fieldnames are different
COMPANY_FIELD = "company"
AGENT_FIELD = "agent"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("ID"), "fieldname": "party", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": _("Customer Name"), "fieldname": "party_name", "fieldtype": "Data", "width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Customer Type"), "fieldname": "customer_type", "fieldtype": "Data", "width": 120},
		{"label": _("Customer Group"), "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group", "width": 140},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Data", "width": 200},
		{"label": _("Agent"), "fieldname": "agent", "fieldtype": "Data", "width": 160},
		{"label": _("Territory"), "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 120},
		{"label": _("City"), "fieldname": "city", "fieldtype": "Data", "width": 150},
		{"label": _("State"), "fieldname": "state", "fieldtype": "Data", "width": 130},
		{"label": _("Pincode"), "fieldname": "pincode", "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	meta = frappe.get_meta("Customer")

	def ccol(fieldname):
		# Select the column only if the field exists on Customer
		return f"c.`{fieldname}`" if meta.has_field(fieldname) else "''"

	conditions = ""
	values = {}

	if filters.get("city"):
		conditions += " AND a.city LIKE %(city)s"
		values["city"] = f"%{filters.city}%"

	if filters.get("territory"):
		conditions += " AND c.territory = %(territory)s"
		values["territory"] = filters.territory

	if filters.get("customer_group"):
		conditions += " AND c.customer_group = %(customer_group)s"
		values["customer_group"] = filters.customer_group

	if filters.get("status") == "Enabled":
		conditions += " AND c.disabled = 0"
	elif filters.get("status") == "Disabled":
		conditions += " AND c.disabled = 1"

	return frappe.db.sql(
		f"""
		SELECT
			c.name AS party,
			c.customer_name AS party_name,
			IF(c.disabled = 1, 'Disabled', 'Enabled') AS status,
			c.customer_type AS customer_type,
			c.customer_group AS customer_group,
			{ccol(COMPANY_FIELD)} AS company,
			{ccol(AGENT_FIELD)} AS agent,
			c.territory AS territory,
			GROUP_CONCAT(DISTINCT a.city SEPARATOR ', ') AS city,
			GROUP_CONCAT(DISTINCT a.state SEPARATOR ', ') AS state,
			GROUP_CONCAT(DISTINCT a.pincode SEPARATOR ', ') AS pincode
		FROM `tabCustomer` c
		LEFT JOIN `tabDynamic Link` dl
			ON dl.link_doctype = 'Customer'
			AND dl.link_name = c.name
			AND dl.parenttype = 'Address'
		LEFT JOIN `tabAddress` a
			ON a.name = dl.parent
		WHERE 1 = 1 {conditions}
		GROUP BY c.name
		ORDER BY c.name
		""",
		values,
		as_dict=True,
	)