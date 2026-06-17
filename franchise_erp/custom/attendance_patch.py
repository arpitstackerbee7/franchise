import frappe
import hrms.hr.doctype.attendance.attendance as attendance_module
import hrms.hr.doctype.shift_type.shift_type as shift_type

def custom_mark_attendance(
    employee,
    attendance_date,
    status,
    shift=None,
    leave_type=None,
    late_entry=False,
    early_exit=False,
    half_day_status=None,
):
    savepoint = "attendance_creation"

    try:
        frappe.db.savepoint(savepoint)

        attendance = frappe.new_doc("Attendance")
        attendance.update({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": status,
            "shift": shift,
            "leave_type": leave_type,
            "late_entry": late_entry,
            "early_exit": early_exit,
            "half_day_status": half_day_status,
        })

        attendance.insert(ignore_permissions=True)
        attendance.submit()

    except (
        attendance_module.DuplicateAttendanceError,
        attendance_module.OverlappingShiftAttendanceError,
    ):
        frappe.db.rollback(save_point=savepoint)
        return

    return attendance.name


def load_patch():
    attendance_module.mark_attendance = custom_mark_attendance
    shift_type.mark_attendance = custom_mark_attendance

load_patch()