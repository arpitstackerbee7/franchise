import frappe
from frappe.utils import now_datetime

def run_auto_attendance():
    shifts = frappe.get_all(
        "Shift Type",
        filters={"enable_auto_attendance": 1},
        pluck="name"
    )

    for shift_name in shifts:
        shift = frappe.get_doc("Shift Type", shift_name)

        if not shift.last_sync_of_checkin:
            frappe.db.set_value(
                "Shift Type",
                shift_name,
                "last_sync_of_checkin",
                now_datetime()
            )

        shift.reload()
        shift.process_auto_attendance()

    frappe.db.commit()