import frappe


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return ""

    user = frappe.db.escape(user)

    return f"""
        (
            `tabHD Ticket`.`owner` = {user}
            OR
            EXISTS (
                SELECT 1
                FROM `tabToDo` todo
                WHERE todo.reference_type = 'HD Ticket'
                  AND todo.reference_name = `tabHD Ticket`.`name`
                  AND todo.allocated_to = {user}
            )
        )
    """