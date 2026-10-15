import frappe
from datetime import datetime


def fix_working_hours(doc, method):
    # if not doc.working_hours:
    #     return

    # total_minutes = round(float(doc.working_hours) * 60)
    # hours = total_minutes // 60
    # minutes = total_minutes % 60

    # new_value = float(f"{hours}.{minutes:02d}")

    # if doc.working_hours != new_value:
    #     doc.db_set("working_hours", new_value, update_modified=False)


    if doc.shift:
        shift = frappe.get_doc("Shift Type", doc.shift)

        if shift.start_time and shift.end_time:
            start = datetime.strptime(str(shift.start_time), "%H:%M:%S")
            end = datetime.strptime(str(shift.end_time), "%H:%M:%S")

            diff = end - start

            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            doc.working_hours = f"{hours}.{minutes:02d}"