import frappe
from frappe import _

def validate_unique_custom_user(doc, method=None):

    if not doc.custom_user:
        return

    existing = frappe.db.exists(
        "Sales Person",
        {
            "custom_user": doc.custom_user,
            "name": ["!=", doc.name]
        }
    )

    if existing:
        frappe.throw(
            _("User {0} is already linked to Sales Person {1}")
            .format(doc.custom_user, existing)
        )
