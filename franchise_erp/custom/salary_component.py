import frappe
def validate_short_leave_component(doc, method=None):

    if not doc.custom_is_short_leave_deduction:
        return

    # Check if another component already has this checked
    existing = frappe.db.get_value(
        "Salary Component",
        {
            "custom_is_short_leave_deduction": 1,
            "name": ["!=", doc.name]
        },
        "name"
    )

    if existing:
        frappe.throw(
            f"Short Leave Deduction is already assigned to Salary Component: {existing}"
        )