import frappe
from frappe import _
from frappe.utils import getdate, nowdate

def validate_back_date(doc, method=None):
    # Skip if posting_date doesn't exist
    if not hasattr(doc, "posting_date"):
        return

    # Find privilege for logged-in user
    privilege = frappe.db.get_value(
        "Back Date Privilege",
        {
            "user": frappe.session.user,
            "enabled": 1
        },
        ["allowed_days"],
        as_dict=True
    )

    # If no privilege record exists, don't restrict
    if not privilege:
        return

    allowed_days = privilege.allowed_days or 0

    posting_date = getdate(doc.posting_date)
    today = getdate(nowdate())

    difference = (today - posting_date).days

    frappe.msgprint(
        f"User: {frappe.session.user}<br>"
        f"Allowed Days: {allowed_days}<br>"
        f"Difference: {difference}"
    )

    if difference > allowed_days:
        frappe.throw(
            _("You are allowed to create Purchase Invoice only up to {0} day(s) back.")
            .format(allowed_days)
        )