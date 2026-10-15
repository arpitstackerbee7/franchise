# import frappe
# from frappe.utils import date_diff, add_days, getdate

# def update_late_log_on_short_leave(doc, method=None):

#     # -----------------------------
#     # 1. Only for Late Adjustment
#     # -----------------------------
#     if not doc.custom_is_late_adjustment:
#         return

#     if not doc.employee:
#         return
    
#     if doc.status != "Approved":
#         return

#     from frappe.utils import date_diff, add_days

#     # -----------------------------
#     # 2. Loop through all leave dates
#     # -----------------------------
#     no_of_days = date_diff(doc.to_date, doc.from_date) + 1

#     for i in range(no_of_days):
#         single_date = add_days(doc.from_date, i)

#         # -----------------------------
#         # 3. Find Late Log
#         # -----------------------------
#         late_log_name = frappe.db.get_value(
#             "Employee Late Log",
#             {
#                 "employee": doc.employee,
#                 "posting_date": single_date,
#                 "docstatus": 1
#             },
#             "name"
#         )

#         if not late_log_name:
#             continue

#         # -----------------------------
#         # 4. Update Late Log (SAFE WAY)
#         # -----------------------------
#         frappe.db.set_value(
#             "Employee Late Log",
#             late_log_name,
#             {   
#                 "leave_type": doc.leave_type,
#                 "status": "Adjusted",
#                 "leave_application": doc.name
#             }
#         )

import frappe
from frappe.utils import date_diff, add_days, getdate


def update_late_log_on_short_leave(doc, method=None):

    if not doc.employee:
        return

    if doc.status != "Approved":
        return

   
    
    is_short_leave = frappe.db.get_value(
        "Leave Type", doc.leave_type, "custom_is_short_leave"
    )
    if not is_short_leave:
        return

   
    no_of_days = date_diff(doc.to_date, doc.from_date) + 1

    for i in range(no_of_days):
        single_date = add_days(doc.from_date, i)

        
       
        if doc.custom_is_late_adjustment:
            late_log_name = frappe.db.get_value(
                "Employee Late Log",
                {
                    "employee": doc.employee,
                    "posting_date": single_date,
                    "docstatus": 1
                },
                "name"
            )

            if late_log_name:
                # SAFE WAY: db.set_value bypasses validate on submitted doc
                frappe.db.set_value(
                    "Employee Late Log",
                    late_log_name,
                    {
                        "leave_type": doc.leave_type,
                        "status": "Adjusted",
                        "leave_application": doc.name
                    }
                )

        
        
        fix_attendance_status(doc.employee, single_date)


def fix_attendance_status(employee, attendance_date):
    

    attendance = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": ["!=", 2]  # skip cancelled records
        },
        ["name", "status", "leave_type"],
        as_dict=True
    )

    if not attendance:
        return

    if attendance.status != "On Leave":
        return

    if not attendance.leave_type:
        return

    is_short_leave = frappe.db.get_value(
        "Leave Type", attendance.leave_type, "custom_is_short_leave"
    )
    if not is_short_leave:
        
        return

    checkin_count = frappe.db.count(
        "Employee Checkin",
        {
            "employee": employee,
            "time": ["between", [
                f"{attendance_date} 00:00:00",
                f"{attendance_date} 23:59:59"
            ]]
        }
    )

    if checkin_count >= 2:
        new_status = "Present"
    if checkin_count >= 2:
        frappe.db.set_value(
            "Attendance",
            attendance.name,
            "status",
            "Present"
        )
        frappe.db.commit()
    else:
        # no checkin at all -> genuinely on leave, don't touch
        return

    frappe.db.set_value("Attendance", attendance.name, "status", new_status)
    frappe.db.commit()


def update_attendance_on_checkin(doc, method=None):

    if not doc.employee or not doc.time:
        return

    checkin_date = getdate(doc.time)
    fix_attendance_status(doc.employee, checkin_date)


def scheduled_fix_short_leave_attendance():

    records = frappe.get_all(
        "Attendance",
        filters={
            "status": "On Leave",
            "docstatus": ["!=", 2],
        },
        fields=["name", "employee", "attendance_date", "leave_type"],
    )

    for att in records:
        if not att.leave_type:
            continue
        fix_attendance_status(att.employee, att.attendance_date)


def patch_fix_existing_short_leave_attendance():
    

    records = frappe.get_all(
        "Attendance",
        filters={
            "status": "On Leave",
            "docstatus": ["!=", 2],
        },
        fields=["name", "employee", "attendance_date", "leave_type"],
    )

    fixed = 0
    for att in records:
        if not att.leave_type:
            continue
        before = frappe.db.get_value("Attendance", att.name, "status")
        fix_attendance_status(att.employee, att.attendance_date)
        after = frappe.db.get_value("Attendance", att.name, "status")
        if before != after:
            fixed += 1
            print(f"Fixed {att.name}: {before} -> {after}")

    print(f"\nDone. {fixed} record(s) fixed out of {len(records)} checked.")