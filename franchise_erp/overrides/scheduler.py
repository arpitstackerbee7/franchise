import frappe
from hrms.hr.doctype.shift_type.shift_type import (
    process_auto_attendance_for_all_shifts as _process_auto_attendance_for_all_shifts,
)


def process_auto_attendance_for_all_shifts_all():
    """Runs hrms's attendance processing on every scheduler tick (registered under 'all')."""
    _process_auto_attendance_for_all_shifts()


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