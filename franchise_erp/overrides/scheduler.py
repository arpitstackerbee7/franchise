import frappe

def set_custom_scheduler_frequencies():
    """Force process_auto_attendance_for_all_shifts to run on every scheduler tick,
    overriding hrms core's 'hourly' registration, without touching core hooks.py"""
    method = "hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts"
    job_name = frappe.db.get_value("Scheduled Job Type", {"method": method}, "name")
    if job_name:
        frappe.db.set_value("Scheduled Job Type", job_name, "frequency", "All")
        frappe.db.commit()