import frappe
import math
from frappe.utils import flt


def override_leave_encashment_calculation(doc, method):
    if not doc.employee or not doc.leave_period or not doc.leave_type:
        return

    
    if doc.leave_type != "Earned Leave":
        return

    
    employee_category = frappe.db.get_value("Employee", doc.employee, "custom_employee_category")
    if employee_category != "Company Employee":
        return

    leave_period = frappe.get_doc("Leave Period", doc.leave_period)
    from_date = leave_period.from_date
    to_date = leave_period.to_date

    annual_entitlement = flt(
        frappe.db.get_value("Leave Type", doc.leave_type, "max_leaves_allowed")
    )
    if not annual_entitlement:
        frappe.throw(
            f"'Maximum Leave Allocation Allowed per Leave Period' is not set for Leave Type '{doc.leave_type}'"
        )

    remaining_paid_leaves = flt(doc.actual_encashable_days)
    paid_leaves_availed = annual_entitlement - remaining_paid_leaves

    lwp_days = get_lwp_days(doc.employee, from_date, to_date)
    total_leaves_taken = paid_leaves_availed + lwp_days

    deduction = get_slab_deduction(total_leaves_taken)
    final_encashment_days = max(0, remaining_paid_leaves - deduction)

    doc.custom_lwp_days = lwp_days
    doc.custom_total_leaves_taken = total_leaves_taken
    doc.custom_encashment_deduction = deduction

    old_days = remaining_paid_leaves
    old_amount = flt(doc.encashment_amount)
    per_day_rate = (old_amount / old_days) if old_days else 0

    doc.encashment_days = final_encashment_days
    doc.encashment_amount = round(final_encashment_days * per_day_rate, 2)


def get_lwp_days(employee, from_date, to_date):
    leave_types = frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")
    if not leave_types:
        return 0

    applications = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "status": "Approved",
            "leave_type": ["in", leave_types],
            "from_date": [">=", from_date],
            "to_date": ["<=", to_date],
        },
        fields=["total_leave_days"],
    )
    return sum(flt(a.total_leave_days) for a in applications)


def get_slab_deduction(total_leaves_taken):
    if total_leaves_taken <= 30:
        return 0
    slab_count = min(math.ceil((total_leaves_taken - 30) / 10), 6)
    return round(slab_count * 1.13, 2)