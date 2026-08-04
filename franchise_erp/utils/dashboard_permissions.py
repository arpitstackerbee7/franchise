# franchise_erp/utils/dashboard_permissions.py
import frappe

def get_allowed_company(filters):
    user = frappe.session.user
    user_company = frappe.db.get_value("User", user, "company")
    dashboard_company = frappe.db.get_single_value(
        "TZU Settings", "dashboard_company"
    )
    is_tzu = user == "Administrator" or user_company == dashboard_company
    requested = filters.get("company")

    if is_tzu:
        return requested  

    if requested and requested != user_company:
        frappe.throw("Not permitted to view other company's data", frappe.PermissionError)
    return user_company