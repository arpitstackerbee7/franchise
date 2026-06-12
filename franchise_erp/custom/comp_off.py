import frappe
from frappe.utils import add_days, today, get_datetime


def set_comp_off_expiry(doc, method=None):
    """
    Set expiry date on Leave Allocation created from
    Compensatory Leave Request.
    """

    if not doc.leave_allocation:
        return

    allocation = frappe.get_doc(
        "Leave Allocation",
        doc.leave_allocation
    )

    allocation.db_set(
        "custom_expiry_date",
        add_days(doc.work_end_date, 15)
    )

    allocation.db_set(
        "custom_is_expired",
        0
    )


def expire_comp_off_allocations():
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "leave_type": "Compensatory Off",
            "custom_is_expired": 0,
            "custom_expiry_date": ["<=", today()],
            "docstatus": 1
        },
        fields=[
            "name",
            "employee",
            "custom_expiry_date"
        ]
    )

    for allocation in allocations:
        frappe.db.set_value(
            "Leave Allocation",
            allocation.name,
            "custom_is_expired",
            1
        )

    frappe.db.commit()

def validate_comp_off_submission(doc, method=None):

    deadline = get_datetime(
        f"{add_days(doc.work_end_date, 1)} 17:00:00"
    )

    if get_datetime() > deadline:
        frappe.throw(
            "Comp Off Request can only be submitted until 2:00 PM of the next day."
        )