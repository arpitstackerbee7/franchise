# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _, scrub
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})

	get_ticket_statuses()

	statuses = frappe.local.custom_ticket_summary_statuses

	columns = get_columns(statuses)
	data = get_data(filters, statuses)
	chart = get_chart(data, filters, statuses)
	report_summary = get_report_summary(data, statuses)

	return columns, data, None, chart, report_summary


# ============================================================
# STATUS
# ============================================================

def get_ticket_statuses():
	"""
	Get all enabled HD Ticket statuses.
	"""

	status_data = frappe.get_all(
		"HD Ticket Status",
		filters={"enabled": 1},
		fields=["label_agent", "color", "category"],
		order_by="`tabHD Ticket Status`.order",
	)

	statuses = []

	status_colors = {}

	status_categories = {}

	for status in status_data:

		status_name = status.label_agent

		statuses.append(status_name)

		status_colors[status_name] = get_color_hex(
			status.color
		)

		status_categories[status_name] = status.category

	frappe.local.custom_ticket_summary_statuses = statuses
	frappe.local.custom_ticket_summary_status_colors = status_colors
	frappe.local.custom_ticket_summary_status_categories = status_categories


def get_color_hex(color_name):

	color_map = {
		"Black": "#000000",
		"Gray": "#6b7280",
		"Blue": "#3b82f6",
		"Green": "#22c55e",
		"Red": "#ef4444",
		"Pink": "#ec4899",
		"Orange": "#f97316",
		"Amber": "#f59e0b",
		"Yellow": "#eab308",
		"Cyan": "#06b6d4",
		"Teal": "#14b8a6",
		"Violet": "#8b5cf6",
		"Purple": "#a855f7",
	}

	return color_map.get(
		color_name,
		"#6b7280",
	)


# ============================================================
# COLUMNS
# ============================================================

def get_columns(statuses):

	columns = []

	# ----------------------------------------------------------
	# BASED ON
	# ----------------------------------------------------------

	columns.append(
		{
			"label": _("Based On"),
			"fieldname": "based_on_value",
			"fieldtype": "Data",
			"width": 180,
		}
	)

	# ----------------------------------------------------------
	# TICKET
	# ----------------------------------------------------------

	columns.append(
		{
			"label": _("Ticket"),
			"fieldname": "ticket",
			"fieldtype": "Link",
			"options": "HD Ticket",
			"width": 120,
		}
	)

	# ----------------------------------------------------------
	# NEW USER / DATETIME FIELDS
	# ----------------------------------------------------------

	columns.append(
		{
			"label": _("Created By"),
			"fieldname": "created_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 180,
		}
	)

	columns.append(
		{
			"label": _("Assigned To"),
			"fieldname": "assigned_to",
			"fieldtype": "Link",
			"options": "User",
			"width": 180,
		}
	)

	columns.append(
		{
			"label": _("Resolved By"),
			"fieldname": "resolved_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 180,
		}
	)

	columns.append(
		{
			"label": _("Created Datetime"),
			"fieldname": "created_datetime",
			"fieldtype": "Datetime",
			"width": 180,
		}
	)

	columns.append(
		{
			"label": _("Assigned Datetime"),
			"fieldname": "assigned_datetime",
			"fieldtype": "Datetime",
			"width": 180,
		}
	)

	columns.append(
		{
			"label": _("Resolved Datetime"),
			"fieldname": "resolved_datetime",
			"fieldtype": "Datetime",
			"width": 180,
		}
	)

	# ----------------------------------------------------------
	# CORE STATUS COLUMNS
	# ----------------------------------------------------------

	for status in statuses:

		columns.append(
			{
				"label": _(status),
				"fieldname": scrub(status),
				"fieldtype": "Int",
				"width": 80,
			}
		)

	# ----------------------------------------------------------
	# TOTAL TICKET
	# ----------------------------------------------------------

	columns.append(
		{
			"label": _("Total Ticket"),
			"fieldname": "total_tickets",
			"fieldtype": "Int",
			"width": 100,
		}
	)

	# ----------------------------------------------------------
	# SLA
	# ----------------------------------------------------------

	columns.append(
		{
			"label": _("SLA Failed"),
			"fieldname": "sla_failed",
			"fieldtype": "Int",
			"width": 100,
		}
	)

	columns.append(
		{
			"label": _("SLA Fulfilled"),
			"fieldname": "sla_fulfilled",
			"fieldtype": "Int",
			"width": 100,
		}
	)

	columns.append(
		{
			"label": _("SLA Ongoing"),
			"fieldname": "sla_ongoing",
			"fieldtype": "Int",
			"width": 100,
		}
	)

	# ----------------------------------------------------------
	# AVERAGE / TIME METRICS
	# ----------------------------------------------------------

	metrics = [
		("Avg First Response Time", "avg_first_response_time"),
		("Avg Response Time", "avg_response_time"),
		("Avg Hold Time", "avg_hold_time"),
		("Avg Resolution Time", "avg_resolution_time"),
		("Avg User Resolution Time", "avg_user_resolution_time"),
	]

	for label, fieldname in metrics:

		columns.append(
			{
				"label": _(label),
				"fieldname": fieldname,
				"fieldtype": "Duration",
				"width": 170,
			}
		)

	return columns


# ============================================================
# DATA
# ============================================================

def get_data(filters, statuses):

	conditions = []
	values = {}

	# ----------------------------------------------------------
	# DATE
	# ----------------------------------------------------------

	if filters.get("from_date"):

		conditions.append(
			"DATE(t.creation) >= %(from_date)s"
		)

		values["from_date"] = filters.from_date

	if filters.get("to_date"):

		conditions.append(
			"DATE(t.creation) <= %(to_date)s"
		)

		values["to_date"] = filters.to_date

	# ----------------------------------------------------------
	# STATUS
	# ----------------------------------------------------------

	if filters.get("status"):

		conditions.append(
			"t.status = %(status)s"
		)

		values["status"] = filters.status

	# ----------------------------------------------------------
	# PRIORITY
	# ----------------------------------------------------------

	if filters.get("priority"):

		conditions.append(
			"t.priority = %(priority)s"
		)

		values["priority"] = filters.priority

	# ----------------------------------------------------------
	# CONTACT
	# ----------------------------------------------------------

	if filters.get("contact"):

		conditions.append(
			"t.contact = %(contact)s"
		)

		values["contact"] = filters.contact

	# ----------------------------------------------------------
	# ASSIGNED TO FILTER
	# ----------------------------------------------------------

	assigned_filter = ""

	if filters.get("assigned_to"):

		assigned_filter = """
			AND EXISTS (
				SELECT 1
				FROM `tabToDo` td_filter
				WHERE
					td_filter.reference_type = 'HD Ticket'
					AND td_filter.reference_name = t.name
					AND td_filter.allocated_to = %(assigned_to)s
					AND td_filter.status != 'Cancelled'
			)
		"""

		values["assigned_to"] = filters.assigned_to

	# ----------------------------------------------------------
	# WHERE
	# ----------------------------------------------------------

	where_clause = ""

	if conditions:

		where_clause = (
			"WHERE " + " AND ".join(conditions)
		)

	# ----------------------------------------------------------
	# GET TICKETS
	# ----------------------------------------------------------

	tickets = frappe.db.sql(
		f"""
		SELECT
			t.name AS ticket,
			t.contact,
			t.ticket_type,
			t.priority,
			t.status,

			t.owner AS created_by,
			t.creation AS created_datetime,

			t.avg_response_time,
			t.first_response_time,
			t.total_hold_time,
			t.user_resolution_time,
			t.resolution_time,

			t.agreement_status,
			t.resolution_date,

			t.subject

		FROM `tabHD Ticket` t

		{where_clause}

		{assigned_filter}

		ORDER BY t.creation DESC
		""",
		values,
		as_dict=True,
	)

	data = []

	for ticket in tickets:

		# ------------------------------------------------------
		# ASSIGNMENT
		# ------------------------------------------------------

		assignment = get_assignment(
			ticket.ticket
		)

		assigned_to = (
			assignment.get("assigned_to")
			or ""
		)

		assigned_datetime = (
			assignment.get("assigned_datetime")
		)

		# ------------------------------------------------------
		# RESOLVED BY
		# ------------------------------------------------------

		resolved_by = get_resolved_by(
			ticket.ticket,
			ticket.resolution_date,
		)

		# ------------------------------------------------------
		# BASED ON
		# ------------------------------------------------------

		based_on_value = get_based_on_value(
			filters.get("based_on"),
			ticket,
			assigned_to,
		)

		# ------------------------------------------------------
		# ROW
		# ------------------------------------------------------

		row = {
			"based_on_value": based_on_value,

			"ticket": ticket.ticket,

			"created_by": ticket.created_by or "",

			"assigned_to": assigned_to,

			"resolved_by": resolved_by,

			"created_datetime": ticket.created_datetime,

			"assigned_datetime": assigned_datetime,

			"resolved_datetime": ticket.resolution_date,

			"total_tickets": 1,

			"avg_first_response_time": (
				ticket.first_response_time or 0
			),

			"avg_response_time": (
				ticket.avg_response_time or 0
			),

			"avg_hold_time": (
				ticket.total_hold_time or 0
			),

			"avg_resolution_time": (
				ticket.resolution_time or 0
			),

			"avg_user_resolution_time": (
				ticket.user_resolution_time or 0
			),
		}

		# ------------------------------------------------------
		# STATUS COLUMN
		# ------------------------------------------------------

		for status in statuses:

			row[scrub(status)] = 0

		if ticket.status:

			status_field = scrub(
				ticket.status
			)

			row[status_field] = 1

		# ------------------------------------------------------
		# SLA STATUS
		# ------------------------------------------------------

		row["sla_failed"] = 0
		row["sla_fulfilled"] = 0
		row["sla_ongoing"] = 0

		agreement_status = (
			scrub(ticket.agreement_status)
			if ticket.agreement_status
			else ""
		)

		if agreement_status == "failed":

			row["sla_failed"] = 1

		elif agreement_status == "fulfilled":

			row["sla_fulfilled"] = 1

		elif agreement_status == "ongoing":

			row["sla_ongoing"] = 1

		data.append(row)

	return data


# ============================================================
# BASED ON VALUE
# ============================================================

def get_based_on_value(
	based_on,
	ticket,
	assigned_to
):

	if based_on == "Contact":

		return (
			ticket.contact
			or _("Not Specified")
		)

	if based_on == "Ticket Type":

		return (
			ticket.ticket_type
			or _("Not Specified")
		)

	if based_on == "Ticket Priority":

		return (
			ticket.priority
			or _("Not Specified")
		)

	if based_on == "Assigned To":

		return (
			assigned_to
			or _("Not Specified")
		)

	return _("Not Specified")


# ============================================================
# ASSIGNMENT
# ============================================================

def get_assignment(ticket_name):

	try:

		assignment = frappe.db.sql(
			"""
			SELECT
				allocated_to,
				creation
			FROM `tabToDo`
			WHERE
				reference_type = 'HD Ticket'
				AND reference_name = %s
				AND status != 'Cancelled'
				AND allocated_to IS NOT NULL
				AND allocated_to != ''
			ORDER BY creation ASC
			LIMIT 1
			""",
			(ticket_name,),
			as_dict=True,
		)

		if assignment:

			return {
				"assigned_to":
					assignment[0].allocated_to,

				"assigned_datetime":
					assignment[0].creation,
			}

	except Exception:

		frappe.log_error(
			frappe.get_traceback(),
			"Custom Ticket Summary - Assignment",
		)

	return {
		"assigned_to": "",
		"assigned_datetime": None,
	}


def get_resolved_by(
	ticket_name,
	resolved_datetime=None
):

	if not resolved_datetime:

		return ""

	try:

		versions = frappe.db.get_all(
			"Version",
			filters={
				"ref_doctype": "HD Ticket",
				"docname": ticket_name,
			},
			fields=[
				"name",
				"owner",
				"creation",
				"data",
			],
			order_by="creation ASC",
		)

		for version in versions:

			if not version.data:
				continue

			try:

				version_data = json.loads(
					version.data
				)

			except Exception:

				continue

			changed = version_data.get(
				"changed",
				[]
			)

			for change in changed:

				if not isinstance(
					change,
					list
				):

					continue

				if len(change) < 3:

					continue

				fieldname = change[0]
				new_value = change[2]

				if fieldname != "status":

					continue

				if not new_value:

					continue

				status_category = (
					frappe.db.get_value(
						"HD Ticket Status",
						new_value,
						"category",
					)
				)

				if status_category == "Resolved":

					return (
						version.owner
						or ""
					)

				if (
					str(new_value).lower()
					== "resolved"
				):

					return (
						version.owner
						or ""
					)

		# Fallback
		resolved_user = frappe.db.get_value(
			"HD Ticket",
			ticket_name,
			"modified_by",
		)

		return resolved_user or ""

	except Exception:

		frappe.log_error(
			frappe.get_traceback(),
			"Custom Ticket Summary - Resolved By",
		)

		return ""


def get_chart(
	data,
	filters,
	statuses
):

	if not data:

		return None

	grouped = {}


	for row in data:

		entity = (
			row.get("based_on_value")
			or _("Not Specified")
		)

		status = None

		for status_name in statuses:

			if row.get(scrub(status_name)):

				status = status_name
				break

		if entity not in grouped:

			grouped[entity] = {}

		if status:

			grouped[entity][status] = (
				grouped[entity].get(
					status,
					0
				) + 1
			)


	labels = []

	datasets = []

	for entity in grouped:

		labels.append(entity)

	for status in statuses:

		values = []

		for entity in labels:

			values.append(
				grouped.get(
					entity,
					{}
				).get(
					status,
					0
				)
			)

		datasets.append(
			{
				"name": status,
				"values": values[:30],
				"color": frappe.local
				.custom_ticket_summary_status_colors
				.get(
					status,
					"#6b7280"
				),
			}
		)

	return {
		"data": {
			"labels": labels[:30],
			"datasets": datasets,
		},
		"type": "bar",
		"barOptions": {
			"stacked": True
		},
	}



def get_report_summary(
	data,
	statuses
):

	if not data:

		return []

	status_totals = {}

	for status in statuses:

		status_totals[
			scrub(status)
		] = 0

	for row in data:

		for status in statuses:

			status_totals[
				scrub(status)
			] += flt(
				row.get(
					scrub(status),
					0
				)
			)

	report_summary = []

	for status in statuses:

		report_summary.append(
			{
				"value": status_totals[
					scrub(status)
				],
				"indicator":
					get_status_indicator(
						status
					),
				"label": _(status),
				"datatype": "Int",
			}
		)

	return report_summary



def get_status_indicator(status):

	try:

		category = frappe.db.get_value(
			"HD Ticket Status",
			status,
			"category",
		)

		color_map = {
			"Open": "Red",
			"Paused": "Orange",
			"Resolved": "Green",
		}

		return color_map.get(
			category,
			"Grey"
		)

	except Exception:

		return "Grey"