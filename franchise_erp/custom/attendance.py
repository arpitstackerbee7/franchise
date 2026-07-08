import frappe
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime

def update_last_sync(doc, method):
    if not doc.shift:
        return
    
    try:
        shift = frappe.get_doc("Shift Type", doc.shift)
        end_of_day = get_datetime(str(getdate(doc.time)) + " 23:59:00")
        if shift.last_sync_of_checkin is None or end_of_day > shift.last_sync_of_checkin:
            shift.last_sync_of_checkin = end_of_day
            shift.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        pass

def mark_absent_for_missing_checkout():
    now = now_datetime()

    pending = frappe.db.sql("""
        SELECT a.name, a.employee, a.attendance_date, a.shift
        FROM `tabAttendance` a
        WHERE a.status = 'Present'
        AND a.docstatus = 1
        AND EXISTS (
            SELECT 1 FROM `tabEmployee Checkin` c
            WHERE c.attendance = a.name AND c.log_type = 'IN'
        )
        AND NOT EXISTS (
            SELECT 1 FROM `tabEmployee Checkin` c
            WHERE c.attendance = a.name AND c.log_type = 'OUT'
        )
    """, as_dict=True)

    for att in pending:
        if not att.shift:
            continue
        shift = frappe.get_cached_doc("Shift Type", att.shift)
        shift_end = get_datetime(f"{att.attendance_date} {shift.end_time}")
        checkout_deadline = add_to_date(
            shift_end, minutes=shift.allow_check_out_after_shift_end_time or 0
        )

        if now < checkout_deadline:
            continue

        doc = frappe.get_doc("Attendance", att.name)
        doc.cancel()
        doc.status = "Absent"
        doc.working_hours = 0
        doc.remarks = (doc.remarks or "") + " | Auto-marked Absent: missed checkout"
        doc.save(ignore_permissions=True)
        doc.submit()

    frappe.db.commit()


def validate_attendance_request(doc, method):
    if not doc.custom_missed_checkout:
        return
    if not doc.custom_checkout_time:
        frappe.throw("Please provide checkout time.")
    if not doc.reason:
        frappe.throw("Reason is mandatory when providing checkout time.")

    real_out_exists = frappe.db.exists("Employee Checkin", {
        "employee": doc.employee,
        "log_type": "OUT",
        "time": ["between", [f"{doc.from_date} 00:00:00", f"{doc.to_date} 23:59:59"]]
    })
    if real_out_exists:
        frappe.throw("Checkout already recorded for this date. Cannot override.")


def on_attendance_request_submit(doc, method):
    if not doc.custom_missed_checkout or not doc.custom_checkout_time:
        return

    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": doc.employee, "attendance_date": doc.from_date, "docstatus": ["!=", 2]},
        ["name", "shift"], as_dict=True
    )
    if not attendance:
        frappe.throw("Attendance record not found for this date.")

    
    in_checkin = frappe.db.get_value(
        "Employee Checkin",
        {"employee": doc.employee, "log_type": "IN", "attendance": attendance.name},
        ["name", "time"], as_dict=True
    )
    if not in_checkin:
        frappe.throw(f"No IN checkin found for {doc.employee} on {doc.from_date}. Cannot calculate working hours.")

    
    checkin = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": doc.employee,
        "log_type": "OUT",
        "time": doc.custom_checkout_time,
        "shift": attendance.shift,
        "custom_attendance_request": doc.name
    })
    checkin.insert(ignore_permissions=True)

    working_hours = (get_datetime(doc.custom_checkout_time) - get_datetime(in_checkin.time)).total_seconds() / 3600

    att_doc = frappe.get_doc("Attendance", attendance.name)

    if att_doc.docstatus == 1:
        att_doc.cancel()

        
        final_doc = frappe.copy_doc(att_doc)
        final_doc.amended_from = att_doc.name
        final_doc.docstatus = 0
    else:
        final_doc = att_doc

    final_doc.status = "Present"
    final_doc.working_hours = round(working_hours, 2)
    final_doc.save(ignore_permissions=True)
    final_doc.submit()

    
    checkin.db_set("attendance", final_doc.name)
    frappe.db.set_value("Employee Checkin", in_checkin.name, "attendance", final_doc.name)

    frappe.db.commit()