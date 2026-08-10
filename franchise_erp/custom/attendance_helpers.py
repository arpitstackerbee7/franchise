import frappe
from frappe.utils import add_days, getdate, nowdate

LEAVE_STATUSES = ("Absent", "On Leave")


MAX_HOLIDAY_CHAIN_LOOKUP = 15

SIX_DAY_RULE_COUNT = 6

def is_holiday(employee, date):
    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list") \
        or frappe.get_cached_value(
            "Company",
            frappe.db.get_value("Employee", employee, "company"),
            "default_holiday_list"
        )
    if not holiday_list:
        return False
    return bool(frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}))


def get_status(employee, date):
    return frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": date, "docstatus": 1},
        "status"
    )


def get_prev_non_holiday_status(employee, date):
    d = add_days(date, -1)
    steps = 0
    while is_holiday(employee, d):
        d = add_days(d, -1)
        steps += 1
        if steps > MAX_HOLIDAY_CHAIN_LOOKUP:
            
            return None, d
    return get_status(employee, d), d


def get_next_non_holiday_status(employee, date):
    d = add_days(date, 1)
    steps = 0
    while is_holiday(employee, d):
        d = add_days(d, 1)
        steps += 1
        if steps > MAX_HOLIDAY_CHAIN_LOOKUP:
            return None, d
    return get_status(employee, d), d


def get_prev_working_statuses(employee, date, count=SIX_DAY_RULE_COUNT):
    statuses = []
    d = date
    steps = 0
    max_steps = MAX_HOLIDAY_CHAIN_LOOKUP + count
    while len(statuses) < count and steps < max_steps:
        d = add_days(d, -1)
        steps += 1
        if is_holiday(employee, d):
            continue
        statuses.append(get_status(employee, d))
    return statuses


def mark_holiday_status(employee, date, status, leave_type=None, leave_application=None):
    existing = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})
    if existing:
        doc = frappe.get_doc("Attendance", existing)
        if doc.docstatus == 1 and doc.status == status :
            return  
        if doc.docstatus == 1:
            doc.cancel()
        doc.status = status
        doc.docstatus = 0
    else:
        doc = frappe.new_doc("Attendance")
        doc.employee = employee
        doc.attendance_date = date
        doc.status = status
        doc.company = frappe.db.get_value("Employee", employee, "company")

    if status == "On Leave":
        if leave_type:
            doc.leave_type = leave_type
        if leave_application:
            doc.leave_application = leave_application
    doc.flags.from_sandwich_rule = True 
    doc.save(ignore_permissions=True)
    doc.submit()

def get_leave_details(employee, date):
    
    leave_app = frappe.db.get_value(
        "Leave Application",
        {
            "employee": employee,
            "status": "Approved",
            "docstatus": 1,
            "from_date": ["<=", date],
            "to_date": [">=", date],
        },
        ["name", "leave_type"],
        as_dict=True,
    )
    if leave_app:
        return leave_app.leave_type, leave_app.name
    return None, None


def apply_sandwich_rule(employee, from_date, to_date):
    
    date = getdate(from_date)
    end = getdate(to_date)
 
    while date <= end:
        if is_holiday(employee, date):
            actual_status = get_status(employee, date)
 
            
            if actual_status == "Present":
                prev_six = get_prev_working_statuses(employee, date, SIX_DAY_RULE_COUNT)
                if len(prev_six) == SIX_DAY_RULE_COUNT and all(s in LEAVE_STATUSES for s in prev_six):
                    date = add_days(date, 1)
                    continue
 
            prev_status, _ = get_prev_non_holiday_status(employee, date)
            next_status, _ = get_next_non_holiday_status(employee, date)
 
            if prev_status in LEAVE_STATUSES and next_status in LEAVE_STATUSES:
                if prev_status == "On Leave" or next_status == "On Leave":
                    leave_type, leave_app = get_leave_details(employee, date) \
                        or get_leave_details(employee, add_days(date, -1)) \
                        or get_leave_details(employee, add_days(date, 1))
                    if not leave_type:
                        
                        prev_d = add_days(date, -1)
                        next_d = add_days(date, 1)
                        while is_holiday(employee, prev_d):
                            prev_d = add_days(prev_d, -1)
                        leave_type, leave_app = get_leave_details(employee, prev_d)
                        if not leave_type:
                            leave_type, leave_app = get_leave_details(employee, next_d)
                    mark_holiday_status(employee, date, "On Leave", leave_type, leave_app)
                else:
                    
                    mark_holiday_status(employee, date, "Absent")
        date = add_days(date, 1)
 


def run_sandwich_check_for_all():
    lock_key = "sandwich_check_running"

    if frappe.cache().get_value(lock_key):
        frappe.logger().info("Sandwich check already running, skipping this cycle.")
        return

    frappe.cache().set_value(lock_key, True, expires_in_sec=300)
    try:
        to_date = add_days(nowdate(), -1)
        from_date = add_days(to_date, -3)

        employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
        for emp in employees:
            try:
                apply_sandwich_rule(emp, from_date, to_date)
            except Exception:
                
                frappe.log_error(
                    title=f"Sandwich rule failed for employee {emp}",
                    message=frappe.get_traceback()
                )
    finally:
        frappe.cache().delete_value(lock_key)


def check_sandwich_on_leave_submit(doc, method=None):

    from_date = add_days(getdate(doc.from_date), -2)
    to_date = add_days(getdate(doc.to_date), 2)
    apply_sandwich_rule(doc.employee, from_date, to_date)

def check_sandwich_on_attendance_submit(doc, method=None):
    if doc.status != "Absent":
        return
    if doc.flags.get("from_sandwich_rule"):
        return
    frappe.enqueue(
        "franchise_erp.custom.attendance_helpers.apply_sandwich_rule",
        employee=doc.employee,
        from_date=add_days(getdate(doc.attendance_date), -2),
        to_date=add_days(getdate(doc.attendance_date), 2),
        queue="short",
        now=frappe.flags.in_test
    )   