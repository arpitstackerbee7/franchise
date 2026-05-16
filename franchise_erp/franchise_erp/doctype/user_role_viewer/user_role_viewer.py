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