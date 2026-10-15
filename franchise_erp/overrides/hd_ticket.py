import frappe


def permission_query(user=None):
    if not user:
        user = frappe.session.user

    # System Manager can see all Helpdesk tickets
    if "System Manager" in frappe.get_roles(user):
        return ""

    # For all other users, use standard Helpdesk restrictions
    from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import (
        permission_query as helpdesk_permission_query,
    )

    return helpdesk_permission_query(user)