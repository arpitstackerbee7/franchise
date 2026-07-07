import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def validate_back_date(doc, method=None):
    # Determine which date field the DocType uses
    if hasattr(doc, "posting_date"):
        date_field = "posting_date"
    elif hasattr(doc, "transaction_date"):
        date_field = "transaction_date"
    else:
        # Skip validation if the DocType has neither field
        return

    document_date = getdate(getattr(doc, date_field))

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

    # If no privilege record exists, allow only today's date
    if not privilege:
        allowed_days = 0
    else:
        allowed_days = privilege.allowed_days or 0

    # If editing an existing document, validate only when the date is changed
    if not doc.is_new():
        old_doc = frappe.get_doc(doc.doctype, doc.name)

        old_date = getdate(getattr(old_doc, date_field))
        new_date = getdate(getattr(doc, date_field))

        # If date is not changed, allow saving
        if old_date == new_date:
            return

    today = getdate(nowdate())

    difference = (today - document_date).days

    if difference > allowed_days:
        frappe.throw(
            _("You are allowed to create {0} only up to {1} day(s) back.")
            .format(doc.doctype, allowed_days)
        )