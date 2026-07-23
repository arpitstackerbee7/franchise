import frappe
from frappe.utils import add_days, getdate, nowdate

LEAVE_STATUSES = ("Absent", "On Leave")

# Safety cap: agar consecutive holidays isse zyada lambi chain ban jaaye,
# to loop yahin ruk jayega (data issue ka signal, infinite loop nahi banega)
MAX_HOLIDAY_CHAIN_LOOKUP = 15


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
    """Holiday se peeche jaate hue pehla non-holiday (working) din dhoondo aur uska status return karo."""
    d = add_days(date, -1)
    steps = 0
    while is_holiday(employee, d):
        d = add_days(d, -1)
        steps += 1
        if steps > MAX_HOLIDAY_CHAIN_LOOKUP:
            # Bahut lambi holiday chain — safety ke liye ruk jao, treat as "not found"
            return None, d
    return get_status(employee, d), d


def get_next_non_holiday_status(employee, date):
    """Holiday se aage jaate hue pehla non-holiday (working) din dhoondo aur uska status return karo."""
    d = add_days(date, 1)
    steps = 0
    while is_holiday(employee, d):
        d = add_days(d, 1)
        steps += 1
        if steps > MAX_HOLIDAY_CHAIN_LOOKUP:
            return None, d
    return get_status(employee, d), d


def mark_absent(employee, date):
    existing = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})
    if existing:
        doc = frappe.get_doc("Attendance", existing)
        if doc.docstatus == 1 and doc.status == "Absent":
            return  # already correctly marked, kuch nahi karna
        if doc.docstatus == 1:
            doc.cancel()
        doc.status = "Absent"
        doc.docstatus = 0
    else:
        doc = frappe.new_doc("Attendance")
        doc.employee = employee
        doc.attendance_date = date
        doc.status = "Absent"
        doc.company = frappe.db.get_value("Employee", employee, "company")

    doc.save(ignore_permissions=True)
    doc.submit()


def apply_sandwich_rule(employee, from_date, to_date):
    """
    Har holiday (weekly-off ya company holiday) ke liye check karo:
    - Uske pehle wale nearest working (non-holiday) din ka status
    - Uske baad wale nearest working (non-holiday) din ka status
    Agar dono side Absent/On Leave hain -> holiday bhi Absent mark ho jayega.

    Consecutive holidays (jaise Diwali + Sunday) ko chain treat kiya jaata hai:
    beech ke sab holidays ke "neighbors" hamesha nearest WORKING din hote hain,
    immediate adjacent din nahi (jo khud holiday ho sakta hai).
    """
    date = getdate(from_date)
    end = getdate(to_date)

    while date <= end:
        if is_holiday(employee, date):
            prev_status, _ = get_prev_non_holiday_status(employee, date)
            next_status, _ = get_next_non_holiday_status(employee, date)

            if prev_status in LEAVE_STATUSES and next_status in LEAVE_STATUSES:
                mark_absent(employee, date)
        date = add_days(date, 1)


def run_sandwich_check_for_all():
    """
    Daily scheduler ('all' hook, ~every 4 min) se chalta hai.

    IMPORTANT — date range decisions:
    - to_date = yesterday (aaj EXCLUDE): aaj ka Attendance/Leave status abhi
      finalized nahi hai (Leave Application cancel ho sakti hai, checkin abhi
      baaki ho sakta hai). Rolling window hone ki wajah se kal ye date khud
      apne aap process ho jayegi jab wo "yesterday" banegi — koi data miss
      nahi hota, sirf ek din delay hota hai jab tak wo finalize na ho jaaye.
    - from_date = to_date - 3 din: sandwich rule sirf immediate holiday ke
      around matter karta hai. Chain lookup (MAX_HOLIDAY_CHAIN_LOOKUP) already
      lambi consecutive holidays handle kar leta hai, isliye bada window
      chahiye hi nahi — bada window sirf load/lock-contention badhata hai.

    Overlap protection: agar pichla run abhi tak chal raha hai (bade dataset
    ki wajah se 4 min se zyada le raha ho), naya run silently skip ho jayega
    taaki dono runs ek sath Attendance table pe lock contention na banayein.
    """
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
                # Ek employee ka error poore batch ko na roke
                frappe.log_error(
                    title=f"Sandwich rule failed for employee {emp}",
                    message=frappe.get_traceback()
                )
    finally:
        frappe.cache().delete_value(lock_key)


def check_sandwich_on_leave_submit(doc, method=None):
    """
    Optional: Leave Application ke on_submit hook se call karo (hooks.py mein add karna hoga).
    Sirf us specific leave ke around ke dates check karta hai — bulk future-scan nahi,
    isliye future dates ke liye bhi safe hai (targeted, low blast-radius).

    hooks.py mein add karna:
    "Leave Application": {
        "on_submit": [
            ...,
            "franchise_erp.custom.attendance_helpers.check_sandwich_on_leave_submit"
        ]
    }
    """
    from_date = add_days(getdate(doc.from_date), -2)
    to_date = add_days(getdate(doc.to_date), 2)
    apply_sandwich_rule(doc.employee, from_date, to_date)