import frappe
from frappe.utils import add_to_date, get_datetime, getdate

def update_last_sync(doc, method):
    if not doc.shift:
        return
    
    try:
        shift = frappe.get_doc("Shift Type", doc.shift)
        end_of_day = get_datetime(str(getdate(doc.time)) + " 23:59:00")
        if shift.last_sync_of_checkin is None or end_of_day > shift.last_sync_of_checkin:
            shift.last_sync_of_checkin = end_of_day
            shift.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        pass