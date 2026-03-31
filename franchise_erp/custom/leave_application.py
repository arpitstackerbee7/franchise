import frappe
from frappe.utils import date_diff, add_days, getdate

def update_late_log_on_short_leave(doc, method=None):

    # -----------------------------
    # 1. Only for Late Adjustment
    # -----------------------------
    if not doc.custom_is_late_adjustment:
        return

    if not doc.employee:
        return
    
    if doc.status != "Approved":
        return

    from frappe.utils import date_diff, add_days

    # -----------------------------
    # 2. Loop through all leave dates
    # -----------------------------
    no_of_days = date_diff(doc.to_date, doc.from_date) + 1

    for i in range(no_of_days):
        single_date = add_days(doc.from_date, i)

        # -----------------------------
        # 3. Find Late Log
        # -----------------------------
        late_log_name = frappe.db.get_value(
            "Employee Late Log",
            {
                "employee": doc.employee,
                "posting_date": single_date,
                "docstatus": 1
            },
            "name"
        )

        if not late_log_name:
            continue

        # -----------------------------
        # 4. Update Late Log (SAFE WAY)
        # -----------------------------
        frappe.db.set_value(
            "Employee Late Log",
            late_log_name,
            {   
                "leave_type": doc.leave_type,
                "status": "Adjusted",
                "leave_application": doc.name
            }
        )