import frappe
from frappe import _
from frappe.core.doctype.role_profile.role_profile import RoleProfile


class CustomRoleProfile(RoleProfile):

    def validate(self):
        validate_role_profile(self)


@frappe.whitelist()
def get_current_user_roles():
    if frappe.session.user == "Administrator":
        return frappe.get_roles("Administrator")

    roles = frappe.get_roles(frappe.session.user)

    return [
        role
        for role in roles
        if role not in {"All", "Guest", "Desk User"}
    ]


def validate_role_profile(doc, method=None):
    current_user = frappe.session.user

    if current_user == "Administrator":
        return

    allowed_roles = set(frappe.get_roles(current_user))
    allowed_roles -= {"All", "Guest", "Desk User"}

    selected_roles = {
        row.role
        for row in (doc.roles or [])
        if row.role
    }

    old_doc = doc.get_doc_before_save()

    existing_roles = set()

    if old_doc:
        existing_roles = {
            row.role
            for row in (old_doc.roles or [])
            if row.role
        }

    newly_added_roles = selected_roles - existing_roles
    unauthorized_roles = newly_added_roles - allowed_roles

    if unauthorized_roles:
        frappe.throw(
            _(
                "You are not allowed to add these roles:<br><b>{0}</b>"
            ).format(", ".join(sorted(unauthorized_roles)))
        )