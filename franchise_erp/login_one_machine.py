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

    # Skip system users
    if user in ["Guest", "Administrator"]:
        return

    # System Settings se expiry lo
    expiry_setting = frappe.db.get_single_value("System Settings", "session_expiry") or "00:30"
    h, m = map(int, expiry_setting.split(":"))
    expiry_delta = timedelta(hours=h, minutes=m)

    now = datetime.now()

    sessions = frappe.db.sql("""
        SELECT sid, lastupdate
        FROM `tabSessions`
        WHERE user=%s
    """, (user,), as_dict=True)

    active_sessions = []

    for s in sessions:
        expiry_time = s.lastupdate + expiry_delta

        # expired session delete kar do
        if expiry_time <= now:
            frappe.db.sql("DELETE FROM `tabSessions` WHERE sid=%s", s.sid)
        else:
            active_sessions.append(s.sid)

    frappe.db.commit()

    # current session remove karo list se
    current_sid = frappe.session.sid
    active_sessions = [sid for sid in active_sessions if sid != current_sid]

    # agar koi aur active session hai to block
    if active_sessions:
        frappe.throw("User already logged in on another device.")