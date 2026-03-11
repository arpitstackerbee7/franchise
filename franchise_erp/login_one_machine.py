import frappe

def check_single_session(login_manager):
    user = login_manager.user

    # Users to skip
    skip_users = ["Guest", "Administrator"]

    # Skip Guest, Administrator
    if user in skip_users:
        return

    # Check active sessions
    sessions = frappe.db.sql("""
        SELECT sid
        FROM `tabSessions`
        WHERE user=%s
    """, (user,), as_dict=True)

    # Agar pehle se session hai to login block
    if sessions:
        frappe.throw("User already logged in. Please logout from previous session.")
