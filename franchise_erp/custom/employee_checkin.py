import frappe 

def process_late_entry(doc, method=None):

    # -----------------------------
    # 1. Only IN logs
    # -----------------------------
    if doc.log_type != "IN":
        return

    if not doc.employee:
        return

    employee = frappe.get_doc("Employee", doc.employee)

    # Apply only for Company Employee
    if employee.custom_employee_category != "Company Employee":
        return

    from frappe.utils import get_datetime, get_first_day, get_last_day

    log_date = doc.time.date()

    # -----------------------------
    # 2. Get Shift
    # -----------------------------
    shift_name = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": doc.employee,
            "start_date": ["<=", log_date],
            "end_date": [">=", log_date],
            "docstatus": 1
        },
        "shift_type"
    )

    if not shift_name:
        return

    shift = frappe.get_doc("Shift Type", shift_name)

    if not shift.start_time:
        return

    # -----------------------------
    # 3. Company Monthly Buffer
    # -----------------------------
    company = frappe.get_doc("Company", employee.company)
    monthly_buffer = company.custom_late_allowed_minutes or 60

    # -----------------------------
    # 4. Calculate TODAY late minutes
    # -----------------------------
    shift_start = get_datetime(f"{log_date} {shift.start_time}")
    in_time = get_datetime(doc.time)

    today_late = int((in_time - shift_start).total_seconds() / 60)

    if today_late <= 0:
        return

    # -----------------------------
    # 5. Calculate MONTHLY late from Checkins (NOT logs)
    # -----------------------------
    month_start = get_first_day(log_date)
    month_end = get_last_day(log_date)

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": doc.employee,
            "log_type": "IN",
            "time": ["between", [month_start, month_end]]
        },
        fields=["time"]
    )

    total_monthly_late = 0

    for c in checkins:
        c_time = get_datetime(c.time)
        c_date = c_time.date()

        shift_name_loop = frappe.db.get_value(
            "Shift Assignment",
            {
                "employee": doc.employee,
                "start_date": ["<=", c_date],
                "end_date": [">=", c_date],
                "docstatus": 1
            },
            "shift_type"
        )

        if not shift_name_loop:
            continue

        shift_loop = frappe.get_doc("Shift Type", shift_name_loop)

        if not shift_loop.start_time:
            continue

        shift_start_loop = get_datetime(f"{c_date} {shift_loop.start_time}")

        late = int((c_time - shift_start_loop).total_seconds() / 60)

        if late > 0:
            total_monthly_late += late

    # -----------------------------
    # 6. If still within buffer → do nothing
    # -----------------------------
    if total_monthly_late <= monthly_buffer:
        return

    # -----------------------------
    # 7. Calculate EXCESS
    # -----------------------------
    previous_late = total_monthly_late - today_late

    if previous_late >= monthly_buffer:
        excess_minutes = today_late
    else:
        excess_minutes = total_monthly_late - monthly_buffer

    # -----------------------------
    # 8. Prevent duplicate log per day
    # -----------------------------
    if frappe.db.exists("Employee Late Log", {
        "employee": doc.employee,
        "posting_date": log_date
    }):
        return

    # -----------------------------
    # 9. Create Late Log ONLY after buffer crossed
    # -----------------------------
    new_late_doc = frappe.get_doc({
        "doctype": "Employee Late Log",
        "employee": doc.employee,
        "posting_date": log_date,
        "late_minutes": excess_minutes,
        "status": "Pending",
        "company": employee.company
    })

    new_late_doc.insert(ignore_permissions=True)
    new_late_doc.submit()