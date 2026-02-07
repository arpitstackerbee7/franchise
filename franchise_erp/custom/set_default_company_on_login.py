import frappe

def set_default_company_on_login(login_manager):
    user = frappe.session.user
    if user == "Administrator":
        return

    # User ki allowed companies
    companies = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Company"
        },
        pluck="for_value",
        order_by="creation asc"
    )

    if not companies:
        return

    # Deterministic pick
    company = companies[0]

    # User Defaults
    frappe.defaults.set_user_default("company", company)
    frappe.defaults.set_user_default("default_company", company)

    # Session Defaults
    frappe.local.default_company = company
    frappe.session.user_defaults = frappe.session.user_defaults or {}
    frappe.session.user_defaults["company"] = company
