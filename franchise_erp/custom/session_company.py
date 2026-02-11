import frappe

def set_session_company_from_user():
    user = frappe.session.user

    if user == "Guest":
        return

    # Agar already session company set hai → kuch mat karo
    if frappe.defaults.get_user_default("company"):
        return

    # 🔥 User master se company uthao
    user_company = frappe.db.get_value("User", user, "company")

    if user_company:
        frappe.defaults.set_user_default("company", user_company)
        frappe.defaults.set_user_default("default_company", user_company)

        frappe.logger().info(
            f"Session company auto-set from User master: {user_company} for {user}"
        )
