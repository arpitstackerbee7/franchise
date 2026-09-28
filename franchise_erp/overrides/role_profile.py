import frappe
from frappe import _
from frappe.core.doctype.role_profile.role_profile import RoleProfile


class CustomRoleProfile(RoleProfile):

    def validate(self):
        validate_role_profile(self)


@frappe.whitelist()
def get_current_user_roles():

    # Administrator can see all roles
    if frappe.session.user == "Administrator":

        return [
            role.name
            for role in frappe.get_all(
                "Role",
                filters={"disabled": 0},
                fields=["name"],
                order_by="name asc"
            )
            if role.name not in {
                "All",
                "Guest",
                "Desk User"
            }
        ]

    all_roles = frappe.get_all(
        "Role",
        filters={"disabled": 0},
        fields=["name"],
        order_by="name asc"
    )

    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": frappe.session.user,
            "enabled": 1
        },
        pluck="name"
    )

    restricted_roles = set()

    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Role Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        restricted_roles.update(
            role
            for role in rows
            if role
        )

    return [
        role.name
        for role in all_roles
        if role.name not in {
            "All",
            "Guest",
            "Desk User"
        }
        and role.name not in restricted_roles
    ]



def validate_role_profile(doc, method=None):

    current_user = frappe.session.user

    if current_user == "Administrator":
        return

    selected_roles = {
        row.role
        for row in (doc.roles or [])
        if row.role
    }

    # Get old document
    old_doc = doc.get_doc_before_save()

    existing_roles = set()

    if old_doc:
        existing_roles = {
            row.role
            for row in (old_doc.roles or [])
            if row.role
        }

    newly_added_roles = selected_roles - existing_roles

    if not newly_added_roles:
        return

    # Get current user's User Role Viewer records
    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    # Get restricted roles
    restricted_roles = set()

    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Role Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        restricted_roles.update(
            role
            for role in rows
            if role
        )

    unauthorized_roles = (
        newly_added_roles & restricted_roles
    )

    if unauthorized_roles:

        frappe.throw(
            _(
                "You are not allowed to add these roles:<br><b>{0}</b>"
            ).format(
                "<br>".join(
                    sorted(unauthorized_roles)
                )
            )
        )