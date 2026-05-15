# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class UserRoleViewer(Document):
    pass

@frappe.whitelist()
def get_logged_user_roles():

    user = frappe.session.user

    assigned_roles = frappe.get_roles(user)

    hidden_roles = ["Guest", "All"]

    all_roles = frappe.get_all(
        "Role",
        fields=["name"],
        order_by="name asc"
    )

    role_data = []

    for role in all_roles:

        if role.name not in hidden_roles:

            role_data.append({
                "role": role.name,
                "checked": role.name in assigned_roles
            })

    return {
        "user": user,
        "roles": role_data
    }