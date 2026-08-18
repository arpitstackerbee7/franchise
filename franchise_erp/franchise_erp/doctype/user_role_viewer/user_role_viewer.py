# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserRoleViewer(Document):
    pass



@frappe.whitelist()
def get_roles_from_profile(role_profile):

    if not role_profile:
        return []

    roles = frappe.get_all(
        "Has Role",
        filters={
            "parent": role_profile
        },
        fields=["role"],
        order_by="role asc"
    )

    return roles


def remove_user_roles(doc, method=None):
    if not doc.user:
        return

    roles_to_remove = {
        row.role
        for row in doc.table_vjxt
        if row.role and row.check
    }

    if not roles_to_remove:
        return

    user = frappe.get_doc("User", doc.user)

    user.roles = [
        row
        for row in user.roles
        if row.role not in roles_to_remove
    ]

    user.save(ignore_permissions=True)

@frappe.whitelist()
def get_hidden_roles_for_user(user):
    if not user:
        return []

    viewer = frappe.db.get_value(
        "User Role Viewer",
        {
            "user": user,
            "enabled": 1
        },
        "name"
    )

    if not viewer:
        return []

    roles = frappe.get_all(
        "User Role Viewer Detail",
        filters={
            "parent": viewer,
            "parenttype": "User Role Viewer",
            "parentfield": "table_vjxt",
            "check": 1
        },
        pluck="role"
    )

    return roles