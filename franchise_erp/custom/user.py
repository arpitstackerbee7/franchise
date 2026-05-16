import frappe
from frappe import _
from frappe.utils import cint


def validate(doc, method=None):

    blocked_roles = []

    viewer_doc = frappe.get_single("User Role Viewer")

    # collect blocked roles
    restricted_roles = [row.role for row in viewer_doc.table_vjxt if cint(row.check)]

    # find matches in current document
    for row in doc.roles:
        if row.role in restricted_roles:
            blocked_roles.append(row.role)

    # throw once with all roles
    if blocked_roles:
        frappe.throw(
            _("Roles Restricted: <b>{0}</b>").format(", ".join(blocked_roles))
        )