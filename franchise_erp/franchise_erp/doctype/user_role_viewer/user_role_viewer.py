# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UserRoleViewer(Document):
    pass


# =========================================================
# ROLE PROFILE -> ROLES
# =========================================================

@frappe.whitelist()
def get_roles_from_profile(role_profile):

    if not role_profile:
        return []

    return frappe.get_all(
        "Has Role",
        filters={
            "parent": role_profile,
            "parenttype": "Role Profile"
        },
        fields=["role"],
        order_by="role asc"
    )


# =========================================================
# MODULE PROFILE -> ALLOWED MODULES
# =========================================================

@frappe.whitelist()
def get_roles_from_module_profile(module_profile):

    if not module_profile:
        return []

    module_profile_doc = frappe.get_doc(
        "Module Profile",
        module_profile
    )

    # -----------------------------------------------------
    # Modules blocked in selected Module Profile
    # -----------------------------------------------------

    blocked_modules = {
        row.module
        for row in module_profile_doc.block_modules
        if row.module
    }

    # -----------------------------------------------------
    # All Module Def
    # -----------------------------------------------------

    all_modules = frappe.get_all(
        "Module Def",
        fields=["name"],
        order_by="name asc"
    )

    # -----------------------------------------------------
    # Return allowed modules
    # -----------------------------------------------------

    return [
        {
            "role": module.name
        }
        for module in all_modules
        if module.name not in blocked_modules
    ]


# =========================================================
# REMOVE RESTRICTED ROLES FROM USER
# =========================================================

def remove_user_roles(doc, method=None):

    if not doc.user:
        return

    roles_to_remove = {
        row.role
        for row in doc.table_vjxt
        if row.role and row.check
    }

    if not roles_to_remove:
        return

    user = frappe.get_doc("User", doc.user)

    user.roles = [
        row
        for row in user.roles
        if row.role not in roles_to_remove
    ]

    user.save(ignore_permissions=True)


# =========================================================
# GET HIDDEN ROLES
# =========================================================

@frappe.whitelist()
def get_hidden_roles_for_user(user=None):

    current_user = frappe.session.user

    if current_user == "Administrator":
        return []

    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    if not viewer_docs:
        return []

    hidden_roles = set()

    for viewer in viewer_docs:

        # ---------------------------------------------
        # Role Profile roles
        # ---------------------------------------------

        rows = frappe.get_all(
            "User Role Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        hidden_roles.update(
            role for role in rows if role
        )

    return list(hidden_roles)


# =========================================================
# GET HIDDEN MODULES
# =========================================================
@frappe.whitelist()
def get_hidden_modules_for_user(user=None):

    current_user = frappe.session.user

    if current_user == "Administrator":
        return []

    # ---------------------------------------------------------
    # Current user's User Role Viewer records
    # ---------------------------------------------------------

    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    if not viewer_docs:
        return []

    # ---------------------------------------------------------
    # Get restricted modules from User Role Viewer
    #
    # module_profile_role:
    #     role = Module Def name
    #     check = 1
    # ---------------------------------------------------------

    restricted_modules = set()

    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Module Profile Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        restricted_modules.update(
            module for module in rows if module
        )

    return list(restricted_modules)


# =========================================================
# GET HIDDEN MODULE PROFILES
# =========================================================

@frappe.whitelist()
def get_hidden_module_profiles_for_user():

    current_user = frappe.session.user

    if current_user == "Administrator":
        return []

    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    if not viewer_docs:
        return []

    hidden_modules = set()

    # -----------------------------------------------------
    # module_profile_role contains allowed Module Def
    # names.
    #
    # Example:
    #
    # Accounts ✓
    # HR ✓
    # Stock ✓
    # -----------------------------------------------------

    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Module Profile Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        hidden_modules.update(
            module for module in rows if module
        )

    if not hidden_modules:
        return []

    # -----------------------------------------------------
    # Get all Module Profiles
    # -----------------------------------------------------

    module_profiles = frappe.get_all(
        "Module Profile",
        fields=["name"]
    )

    hidden_module_profiles = set()

    # -----------------------------------------------------
    # Check every Module Profile
    # -----------------------------------------------------

    for profile in module_profiles:

        profile_doc = frappe.get_doc(
            "Module Profile",
            profile.name
        )

        # Modules blocked in this Module Profile
        blocked_modules = {
            row.module
            for row in profile_doc.block_modules
            if row.module
        }

        # All Module Def
        all_modules = frappe.get_all(
            "Module Def",
            pluck="name"
        )

        # Modules available in this Module Profile
        allowed_modules = (
            set(all_modules) - blocked_modules
        )

        # -------------------------------------------------
        # If this profile contains ANY restricted module,
        # hide this Module Profile from User.
        # -------------------------------------------------

        if hidden_modules.intersection(allowed_modules):

            hidden_module_profiles.add(
                profile.name
            )

    return list(hidden_module_profiles)