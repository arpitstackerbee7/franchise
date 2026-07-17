
import frappe
from frappe.utils import get_datetime, time_diff_in_hours, getdate, now_datetime

MAX_PAIR_GAP_HOURS = 24

ORPHAN_THRESHOLD_HOURS = 20




def disable_core_hourly_job():
	"""Stops hrms core's hourly-registered job so it doesn't run twice,
	since we now run it via our own 'all' registration above."""
	core_method = "hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts"
	job_name = frappe.db.get_value("Scheduled Job Type", {"method": core_method}, "name")
	if job_name:
		frappe.db.set_value("Scheduled Job Type", job_name, "stopped", 1)
		frappe.db.commit()


def enable_create_log_for_all_shifts_job():
	"""Turns on 'Create Log' for our custom scheduler job so it doesn't need
	to be checked manually in the UI after every migrate/sync."""
	our_method = "franchise_erp.overrides.scheduler.process_auto_attendance_for_all_shifts_all"
	job_name = frappe.db.get_value("Scheduled Job Type", {"method": our_method}, "name")
	if job_name:
		frappe.db.set_value("Scheduled Job Type", job_name, "create_log", 1)
		frappe.db.commit()

def process_auto_attendance_for_all_shifts_all():
	employees = frappe.get_all(
		"Employee Checkin",
		filters={"attendance": ["is", "not set"]},
		pluck="employee",
		distinct=True,
	)
	for employee in employees:
		process_checkins_for_employee(employee)

def process_checkins_for_employee(employee):
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "attendance": ["is", "not set"]},
		fields=["name", "employee_name", "time", "log_type", "shift"],
		order_by="time asc",
	)
	if not checkins:
		return

	i = 0
	while i < len(checkins):
		current = checkins[i]
		if current.log_type != "IN":
			flag_if_stale(current)
			i += 1
			continue

		next_checkin = checkins[i + 1] if i + 1 < len(checkins) else None

		if next_checkin and next_checkin.log_type == "OUT":
			gap = time_diff_in_hours(next_checkin.time, current.time)
			if 0 < gap <= MAX_PAIR_GAP_HOURS:
				try:
					create_or_update_attendance(employee, current, next_checkin)
					frappe.db.commit()
				except Exception:
					frappe.db.rollback()
					frappe.log_error(
						title=f"Attendance Pairing Failed: {employee}",
						message=frappe.get_traceback(),
					)
				i += 2
				continue

		flag_if_stale(current)
		i += 1
def create_or_update_attendance(employee, in_checkin, out_checkin):
	attendance_date = getdate(in_checkin.time)
	working_hours = round(time_diff_in_hours(out_checkin.time, in_checkin.time), 2)

	existing = frappe.db.exists(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date, "docstatus": ["!=", 2]},
	)

	if existing:
		att = frappe.get_doc("Attendance", existing)
		if att.docstatus == 1:
			new_working_hours = round((att.working_hours or 0) + working_hours, 2)
			frappe.db.set_value("Attendance", att.name, {
				"out_time": out_checkin.time,
				"working_hours": new_working_hours,
			})
			frappe.db.set_value("Employee Checkin", in_checkin.name, "attendance", att.name)
			frappe.db.set_value("Employee Checkin", out_checkin.name, "attendance", att.name)
			return
		else:
			att.status = "Present"
			att.in_time = in_checkin.time
			att.out_time = out_checkin.time
			att.working_hours = working_hours
			att.save(ignore_permissions=True)
			att.submit()
	else:
		att = frappe.new_doc("Attendance")
		att.employee = employee
		att.employee_name = in_checkin.employee_name
		att.attendance_date = attendance_date
		att.company = frappe.db.get_value("Employee", employee, "company")
		att.shift = in_checkin.shift
		att.status = "Present"
		att.in_time = in_checkin.time
		att.out_time = out_checkin.time
		att.working_hours = working_hours
		att.insert(ignore_permissions=True)
		att.submit()

	frappe.db.set_value("Employee Checkin", in_checkin.name, "attendance", att.name)
	frappe.db.set_value("Employee Checkin", out_checkin.name, "attendance", att.name)

def flag_if_stale(checkin):
	age_hours = time_diff_in_hours(now_datetime(), checkin.time)
	if age_hours < ORPHAN_THRESHOLD_HOURS:
		return  

	already_flagged = frappe.db.get_value(
		"Employee Checkin", checkin.name, "custom_flagged_for_review"
	)
	if already_flagged:
		return

	frappe.db.set_value("Employee Checkin", checkin.name, "custom_flagged_for_review", 1)
	frappe.log_error(
		title="Unpaired Employee Checkin",
		message=(
			f"Checkin {checkin.name} ({checkin.employee}, {checkin.log_type}) "
			f"at {checkin.time} ko {ORPHAN_THRESHOLD_HOURS}+ hours se pair nahi mila. "
			f"Manual review chahiye."
		),
	)