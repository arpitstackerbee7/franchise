import frappe
from frappe.utils import time_diff_in_hours

MAX_PAIR_GAP_HOURS = 24


def fix_shift_for_paired_checkin(doc, method=None):
	"""
	If the checkin's own shift came out blank/Off-Shift (from Frappe's default logic),
	check whether this is the OUT pair of an earlier IN checkin.
	If it is, copy that IN checkin's shift here as well.
	"""
	if doc.shift:
		return  # already assigned, don't touch it

	if doc.log_type != "OUT":
		return  # this logic is only for OUT checkins that cross midnight

	# Find the employee's last IN checkin before this OUT
	last_in = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": doc.employee,
			"log_type": "IN",
			"time": ["<", doc.time],
			"name": ["!=", doc.name],
		},
		["name", "time", "shift"],
		order_by="time desc",
	)

	if not last_in:
		return

	in_name, in_time, in_shift = last_in

	if not in_shift:
		return  # the IN checkin has no shift either, nothing to copy

	gap = time_diff_in_hours(doc.time, in_time)
	if 0 < gap <= MAX_PAIR_GAP_HOURS:
		doc.shift = in_shift