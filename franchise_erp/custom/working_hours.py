import frappe

def fix_working_hours(doc, method):
    if not doc.working_hours:
        return

    total_minutes = round(float(doc.working_hours) * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    new_value = float(f"{hours}.{minutes:02d}")

    if doc.working_hours != new_value:
        doc.db_set("working_hours", new_value, update_modified=False)