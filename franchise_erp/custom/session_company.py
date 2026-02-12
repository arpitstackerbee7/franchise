import frappe

def set_session_company_from_user():
    user = frappe.session.user

    if user == "Guest":
        return

    # 🔥 User master se company uthao
    user_company = frappe.db.get_value("User", user, "company")

    if not user_company:
        return

    # 🔥 FORCE overwrite defaults
    frappe.defaults.set_user_default("company", user_company)
    frappe.defaults.set_user_default("default_company", user_company)

    frappe.local.default_company = user_company

    frappe.logger().info(
        f"✅ Session company force-set from User master: {user_company} for {user}"
    )
