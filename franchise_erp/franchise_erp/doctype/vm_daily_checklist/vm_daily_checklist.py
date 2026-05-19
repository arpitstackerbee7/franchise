# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VMDailyChecklist(Document):
	pass



def get_permission_query_conditions(user):

    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    return f"""
        (
            `tabVM Daily Checklist`.user_id = {frappe.db.escape(user)}
            OR
            `tabVM Daily Checklist`.asmtl_user_id = {frappe.db.escape(user)}
        )
    """


def has_permission(doc, user=None, permission_type=None):

    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return True

    if getattr(doc, "user_id", None) == user:
        return True

    if getattr(doc, "asmtl_user_id", None) == user:
        return True

    return False