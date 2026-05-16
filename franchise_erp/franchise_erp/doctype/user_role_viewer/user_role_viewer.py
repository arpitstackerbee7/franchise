# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt
# user_role_viewer.py

import frappe
from frappe.model.document import Document


class UserRoleViewer(Document):
    pass


@frappe.whitelist()
def get_logged_user_roles():

    all_roles = frappe.get_all(
        "Role",
        fields=["name"],
        filters={
            "disabled": 0
        },
        order_by="name asc"
    )

    return {
        "user": frappe.session.user,
        "roles": all_roles
    }