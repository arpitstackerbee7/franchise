# import frappe


# def permission_query(user=None):
#     if not user:
#         user = frappe.session.user

#     # System Manager can see all Helpdesk tickets
#     if "System Manager" in frappe.get_roles(user):
#         return ""

#     # For all other users, use standard Helpdesk restrictions
#     from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import (
#         permission_query as helpdesk_permission_query,
#     )

#     return helpdesk_permission_query(user)


import frappe
import helpdesk.helpdesk.doctype.hd_ticket.hd_ticket as helpdesk_hd_ticket


def _is_privileged(user):
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def permission_query(user=None):
    if not user:
        user = frappe.session.user

    if _is_privileged(user):
        return ""

    escaped_user = frappe.db.escape(user)

    return f"""(
        `tabHD Ticket`.name in (
            select todo.reference_name
            from `tabToDo` todo
            where todo.reference_type = 'HD Ticket'
                and todo.status != 'Cancelled'
                and (
                    todo.allocated_to = {escaped_user}
                    or todo.assigned_by = {escaped_user}
                )
        )
    )"""


def has_permission(doc, user=None, ptype=None, **kwargs):
    if not user:
        user = frappe.session.user

    if _is_privileged(user):
        return True

    return bool(
        frappe.db.sql(
            """
            select name from `tabToDo`
            where reference_type = 'HD Ticket'
                and reference_name = %(ticket)s
                and status != 'Cancelled'
                and (allocated_to = %(user)s or assigned_by = %(user)s)
            limit 1
            """,
            {"ticket": str(doc.name), "user": user},
        )
    )


def _helpdesk_permission_query_noop(user=None):
    # Helpdesk's own OR-based condition breaks our AND logic, so disable it.
    return ""


# Helpdesk's own check denies tickets where the user is only the assigner,
# so replace it with our rule (it must still return False for other users).
helpdesk_hd_ticket.permission_query = _helpdesk_permission_query_noop
helpdesk_hd_ticket.has_permission = has_permission