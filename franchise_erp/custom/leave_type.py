import frappe 

def validate_only_one_short_leave(doc,method):
    if doc.custom_is_short_leave:

        existing = frappe.db.get_value(
            "Leave Type",
            {
                "custom_is_short_leave": 1,
                "name": ["!=", doc.name]
            },
            "name"
        )

        if existing:
            frappe.throw(
                f"Short Leave is already enabled for Leave Type: {existing}. Only one Leave Type can have this enabled."
            )