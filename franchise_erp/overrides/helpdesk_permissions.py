# import frappe
# from helpdesk.helpdesk.doctype.hd_ticket import hd_ticket


# _original_permission_query = hd_ticket.permission_query


# def custom_permission_query(user=None):
#     if not user:
#         user = frappe.session.user

#     if "System Manager" in frappe.get_roles(user):
#         return

#     return _original_permission_query(user)


# def apply_helpdesk_permission_patch():
#     hd_ticket.permission_query = custom_permission_query


import frappe
from helpdesk.helpdesk.doctype.hd_ticket import hd_ticket


def _is_privileged(user):
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def custom_permission_query(user=None):
    if not user:
        user = frappe.session.user

    if _is_privileged(user):
        return ""

    escaped_user = frappe.db.escape(user)

    return f"""
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
    """


def custom_has_permission(doc, user=None, ptype=None):
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
            {"ticket": doc.name, "user": user},
        )
    )


def apply_helpdesk_permission_patch():
    hd_ticket.permission_query = custom_permission_query
    hd_ticket.has_permission = custom_has_permission