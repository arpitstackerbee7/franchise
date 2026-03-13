# import frappe

# def check_single_session(login_manager):
#     user = login_manager.user

#     # Users to skip
#     skip_users = ["Guest", "Administrator"]

#     # Skip Guest, Administrator
#     if user in skip_users:
#         return

#     # Check active sessions
#     sessions = frappe.db.sql("""
#         SELECT sid
#         FROM `tabSessions`
#         WHERE user=%s
#     """, (user,), as_dict=True)

#     # Agar pehle se session hai to login block
#     if sessions:
#         frappe.throw("User already logged in. Please logout from previous session.")


import frappe
from datetime import datetime, timedelta

def check_single_session(login_manager):
    user = login_manager.user

    if user in ["Guest", "Administrator"]:
        return

    # System Settings se session expiry lo
    expiry_setting = frappe.db.get_single_value("System Settings", "session_expiry") or "00:01"

    h, m = map(int, expiry_setting.split(":"))
    expiry_delta = timedelta(hours=h, minutes=m)

    sessions = frappe.db.sql("""
        SELECT sid, lastupdate
        FROM `tabSessions`
        WHERE user=%s
    """, (user,), as_dict=True)

    now = datetime.now()

    for s in sessions:
        expiry_time = s.lastupdate + expiry_delta

        # Agar session abhi bhi active hai
        if expiry_time > now:
            frappe.throw("User already logged in. Please logout from previous session.")