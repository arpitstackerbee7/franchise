# # Copyright (c) 2026, Franchise Erp and contributors
# # For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LoginSecuritySettings(Document):
	pass


# import frappe

# def validate_login_access():

#     # Guest ni skip cheyyi
#     if frappe.session.user == "Guest":
#         return

#     settings = frappe.get_single("Login Security Settings")

#     access_type = settings.access_type

#     if access_type == "Global Access":
#         return

  
#     if access_type == "IP Based":

#         user_ip = frappe.local.request_ip
#         allowed_ip = (settings.allowed_ip or "").strip()

#         if not allowed_ip:
#             frappe.throw("Allowed IP is not configured")

#         if user_ip != allowed_ip:
#             frappe.throw(
#                 f"Login not allowed from IP Address: {user_ip}"
#             )

#         return

   
#     if access_type == "Geo Location Based":

#         # Nee existing geo code ikkada petti continue cheyyi
#         return






# import frappe


# def validate_login_access():

#     if frappe.session.user == "Guest":
#         return

#     settings = frappe.get_single("Login Security Settings")

#     access_type = settings.access_type

#     if access_type == "Global Access":
#         return

#     user_ip = frappe.local.request.environ.get("REMOTE_ADDR") or ""

#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip()

#         if not allowed_ip:
#             return

#         if user_ip != allowed_ip:
#             frappe.throw(
#                 f"Login not allowed from IP Address: {user_ip}"
#             )
#         return





import frappe

def validate_login_access():

    if frappe.session.user == "Guest":
        return

    settings = frappe.get_single("Login Security Settings")

    if settings.access_type == "Global Access":
        return

    if settings.access_type == "IP Based":

        user_ip = frappe.local.request.environ.get("REMOTE_ADDR")
        allowed_ip = (settings.allowed_ip or "").strip()

        if not allowed_ip:
            return

        if user_ip != allowed_ip:
            frappe.throw(
                f"Login not allowed from IP Address: {user_ip}"
            )









# import frappe


# def validate_login_access():

#     # Allow system processes
#     if frappe.session.user == "Guest":
#         return

#     try:
#         settings = frappe.get_single("Login Security Settings")
#     except:
#         # If settings not found, don't block system
#         return

#     access_type = settings.access_type

#     # =========================
#     # GLOBAL ACCESS
#     # =========================
#     if access_type == "Global Access":
#         return

#     user_ip = frappe.local.request_ip or ""

#     # =========================
#     # IP BASED
#     # =========================
#     if access_type == "IP Based":

#         allowed_ip = (settings.allowed_ip or "").strip()

#         # If not configured, allow admin to avoid lock
#         if not allowed_ip:
#             return

#         if user_ip.strip() != allowed_ip:
#             frappe.throw(
#                 "Login not allowed from this IP Address"
#             )

#         return

#     # =========================
#     # GEO LOCATION (basic placeholder)
#     # =========================
#     if access_type == "Geo Location Based":

#         # If no geo configured, allow login
#         if not (settings.latitude and settings.longitude):
#             return

#         # You can later add geo distance logic here
#         return