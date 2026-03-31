import frappe
from frappe.utils import flt, cstr, date_diff

def apply_leave_rule_deductions(doc, method):
    # -----------------------------
    # 1. Fetch Late Logs (Adjusted only)
    # -----------------------------
    late_logs = frappe.get_all(
        "Employee Late Log",
        filters={
            "employee": doc.employee,
            "docstatus": 1,
            "status": "Adjusted",
            "posting_date": ["between", [doc.start_date, doc.end_date]]
        },
        fields=["name", "leave_type"]
    )

    if not late_logs:
        return

    # -----------------------------
    # 2. Calculate Total Deduction Days
    # -----------------------------
    total_days = 0.0
    valid_logs = []

    for log in late_logs:

        if not log.leave_type:
            continue

        leave_type = frappe.db.get_value(
            "Leave Type",
            log.leave_type,
            ["custom_is_short_leave", "custom_deduction_unit"],
            as_dict=True
        )

        if not leave_type or not leave_type.custom_is_short_leave:
            continue

        unit = flt(leave_type.custom_deduction_unit or 0)
        total_days += unit

        valid_logs.append(log.name)   # ✅ store valid logs

    # -----------------------------
    # 1. Get Short Leave Type
    # -----------------------------
    short_leave = frappe.db.get_value(
        "Leave Type",
        {"custom_is_short_leave": 1},
        ["name", "custom_deduction_unit"],
        as_dict=True
    )

    if not short_leave:
        return

    leave_type_name = short_leave.name
    unit = flt(short_leave.custom_deduction_unit or 0)

    if not unit:
        return

    # -----------------------------
    # 2. Fetch Leave Applications
    # -----------------------------
    short_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": doc.employee,
            "leave_type": leave_type_name,
            "custom_is_late_adjustment": 0,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ["<=", doc.end_date],
            "to_date": [">=", doc.start_date]
        },
        fields=["from_date", "to_date"]
    )

    # -----------------------------
    # 3. Calculate Deduction
    # -----------------------------
    for sl in short_leaves:
        days = date_diff(sl.to_date, sl.from_date) + 1
        total_days += unit * days

    # -----------------------------
    # 4. Nothing to Deduct
    # -----------------------------
    if total_days == 0:
        return

    # -----------------------------
    # 5. Calculate Deduction Amount
    # -----------------------------
    gross = flt(doc.gross_pay)
    payment_days = flt(doc.payment_days)
    working_days = flt(doc.total_working_days)

    if working_days <= 0:
        return

    if payment_days > 0:
        gross_full = gross * (working_days / payment_days)
    else:
        gross_full = gross

    per_day = gross_full / working_days
    deduction_amount = flt(per_day * total_days, 2)

    # -----------------------------
    # 6. Get Salary Component (Checkbox Based)
    # -----------------------------
    component = frappe.db.get_value(
        "Salary Component",
        {"custom_is_short_leave_deduction": 1},
        "name"
    )

    if not component:
        frappe.throw("Please configure Salary Component for Short Leave Deduction")

    # -----------------------------
    # 7. Avoid Duplicate Row
    # -----------------------------
    existing = next(
        (d for d in (doc.get("deductions") or [])
         if cstr(d.salary_component or "").strip() == component),
        None
    )

    # -----------------------------
    # 8. Apply / Update / Remove
    # -----------------------------
    if deduction_amount > 0:
        if existing:
            existing.amount = deduction_amount
        else:
            doc.append("deductions", {
                "salary_component": component,
                "amount": deduction_amount,
            })
    else:
        if existing:
            doc.get("deductions").remove(existing)

    # -----------------------------
    # 9. On Submit → Mark Logs Processed
    # -----------------------------
    if method == "on_submit":
        for log_name in valid_logs:
            frappe.db.set_value(
                "Employee Late Log",
                log_name,
                {
                    "salary_slip": doc.name,
                    "status": "Deducted"
                }
            )