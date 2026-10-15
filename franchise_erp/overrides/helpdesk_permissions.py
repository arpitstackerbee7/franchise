import frappe
from helpdesk.helpdesk.doctype.hd_ticket import hd_ticket


_original_permission_query = hd_ticket.permission_query


def custom_permission_query(user=None):
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return

    return _original_permission_query(user)


def apply_helpdesk_permission_patch():
    hd_ticket.permission_query = custom_permission_query