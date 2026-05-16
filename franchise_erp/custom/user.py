import frappe
from frappe import _
from frappe.utils import cint


def validate(doc, method=None):

    blocked_roles = []

    viewer_doc = frappe.get_single("User Role Viewer")

    for row in viewer_doc.table_vjxt:

        if cint(row.check):

            blocked_roles.append(row.role)

    for row in doc.roles:

        if row.role in blocked_roles:

            frappe.throw(
                _("Role <b>{0}</b> is restricted").format(row.role)
            )