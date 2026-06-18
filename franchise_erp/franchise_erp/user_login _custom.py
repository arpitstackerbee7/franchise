# import frappe


# def validate_login_access():

#     # Allow guest/system calls
#     if frappe.session.user == "Guest":
#         return

#     # Get settings safely
#     settings = frappe.get_single("Login Security Settings")

#     access_type = settings.access_type

#     # =========================
#     # GLOBAL ACCESS
#     # =========================
#     if access_type == "Global Access":
#         return

#     # Get real IP
#     user_ip = frappe.local.request.environ.get("REMOTE_ADDR") or ""

#     # =========================
#     # IP BASED ACCESS
#     # =========================
#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip()

#         # safety: avoid lock if empty
#         if not allowed_ip:
#             return

#         if user_ip != allowed_ip:
#             frappe.throw(
#                 f"Login not allowed from IP Address: {user_ip}"
#             )

#         return

#     # =========================
#     # GEO LOCATION (placeholder)
#     # =========================
#     if access_type == "Geo Location Based":
#         return



# import frappe


# def validate_login_access():

#     if frappe.session.user == "Guest":
#         return

#     settings = frappe.get_single("Login Security Settings")

#     if settings.access_type == "Global Access":
#         return

#     user_ip = frappe.local.request_ip  # ✅ CORRECT WAY
#     allowed_ip = (settings.allowed_ip or "").strip()

#     if settings.access_type == "IP Based":

#         if not allowed_ip:
#             return

#         if user_ip != allowed_ip:
#             frappe.throw(f"Login not allowed from IP Address: {user_ip}")

#         return

# http://127.0.0.1:8000/app/login-security-settings

# Login not allowed from IP Address: 127.0.0.1

# import frappe


# def validate_login_access():

#     if frappe.session.user == "Guest":
#         return

#     # safe fetch
#     try:
#         settings = frappe.get_single("Login Security Settings")
#     except:
#         return

#     access_type = settings.access_type

#     if access_type == "Global Access":
#         return

#     user_ip = (frappe.local.request_ip or "").strip()

#     # ======================
#     # IP BASED
#     # ======================
#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip()

#         if not allowed_ip:
#             return  # safety fallback

#         if user_ip != allowed_ip:
#             frappe.throw(f"Login not allowed from IP Address: {user_ip}")

#         return

#     # ======================
#     # GEO (future safe)
#     # ======================
#     if access_type == "Geo Location Based":
#         return







# auth_hooks = [
#     "franchise_erp.utils.login_security.validate_login_access"
# ]




# import frappe

# def validate_login_access():

#     if frappe.session.user == "Guest":
#         return

#     try:
#         settings = frappe.get_single("Login Security Settings")
#     except:
#         return

#     access_type = settings.access_type

#     if access_type == "Global Access":
#         return

#     user_ip = (frappe.local.request_ip or "").strip()

#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip()

#         if not allowed_ip:
#             return

#         if user_ip != allowed_ip:
#             frappe.throw(f"Login not allowed from IP Address: {user_ip}")

#         return

#     if access_type == "Geo Location Based":
#         return



# import frappe


# def validate_login_access():

#     # ======================
#     # 1. Skip Guest
#     # ======================
#     if frappe.session.user == "Guest":
#         return

#     # ======================
#     # 2. Get Settings safely
#     # ======================
#     try:
#         settings = frappe.get_single("Login Security Settings")
#     except Exception:
#         return

#     access_type = settings.access_type

#     # ======================
#     # 3. Global Access
#     # ======================
#     if access_type == "Global Access":
#         return

#     # ======================
#     # 4. Get User IP
#     # ======================
#     user_ip = (frappe.local.request_ip or "").strip()

#     # ======================
#     # 5. IP Based Access
#     # ======================
#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip().replace(" ", "")

#         if not allowed_ip:
#             return  # safety fallback

#         if user_ip != allowed_ip:
#             frappe.throw(
#                 f"Login not allowed from IP Address: {user_ip}"
#             )

#         return

#     # ======================
#     # 6. Geo Location (future)
#     # ======================
#     if access_type == "Geo Location Based":
#         return



# ippudu vere ip number isthe logout kala super but agin same ip ichiinappududiu same error chupisthundi open logout kavali ga




import frappe

def validate_login_access():

    if frappe.session.user == "Guest":
        return

    settings = frappe.get_single("Login Security Settings")

    access_type = settings.access_type

    if access_type == "Global Access":
        return

    user_ip = (frappe.local.request_ip or "").strip()

    if access_type == "IP Based":

        allowed_ip = (settings.allowed_ip or "").strip()

        # ❌ allowed IP set cheyyakapothe
        if not allowed_ip:
            frappe.throw("Allowed IP set cheyyaledu")

        # ❌ WRONG IP MESSAGE (CLEAR GA)
        if user_ip != allowed_ip:
            frappe.throw(
                f"❌ Access Denied!\nMee IP: {user_ip}\nAllowed IP: {allowed_ip}"
            )

        return

    if access_type == "Geo Location Based":
        return