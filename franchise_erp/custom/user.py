
import frappe
from frappe import _


def validate_user_roles(doc, method=None):

    # current logged in user
    current_user = frappe.session.user

    # Administrator bypass
    if current_user == "Administrator":
        return

    # get enabled User Role Viewer docs
    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    if not viewer_docs:
        return

    restricted_roles = []

    # get checked restricted roles
    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Role Viewer Detail",
            filters={
                "parent": viewer,
                "check": 1
            },
            pluck="role"
        )

        restricted_roles.extend(rows)

    if not restricted_roles:
        return

    # roles selected in User form
    assigned_roles = [d.role for d in doc.roles]

    # restricted roles match
    blocked_roles = list(
        set(assigned_roles) & set(restricted_roles)
    )

    if blocked_roles:

        frappe.throw(
            _("You are not allowed to assign these roles:<br><b>{0}</b>")
            .format(", ".join(blocked_roles))
        )