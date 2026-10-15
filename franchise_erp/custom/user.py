import frappe
from frappe import _


def validate_user_roles(doc, method=None):

    # =====================================================
    # Administrator bypass
    # =====================================================

    current_user = frappe.session.user

    if current_user == "Administrator":
        return

    # =====================================================
    # Get User Role Viewer
    # =====================================================

    viewer_docs = frappe.get_all(
        "User Role Viewer",
        filters={
            "user": current_user,
            "enabled": 1
        },
        pluck="name"
    )

    if not viewer_docs:
        return

    # =====================================================
    # ROLE PROFILE
    # =====================================================

    restricted_roles = set()

    for viewer in viewer_docs:

        rows = frappe.get_all(
            "User Role Viewer Detail",
            filters={
                "parent": viewer,
                "parenttype": "User Role Viewer",
                "check": 1
            },
            pluck="role"
        )

        restricted_roles.update(
            role for role in rows if role
        )

    # =====================================================
    # MODULE PROFILE
    # =====================================================

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

    # =====================================================
    # CHECK USER ROLES
    # =====================================================

    assigned_roles = {
        row.role
        for row in doc.roles
        if row.role
    }

    blocked_roles = assigned_roles.intersection(
        restricted_roles
    )

    if blocked_roles:

        frappe.throw(
            _(
                "You are not allowed to assign these roles:<br><b>{0}</b>"
            ).format(
                ", ".join(sorted(blocked_roles))
            )
        )

    # =====================================================
    # CHECK USER MODULE PROFILE
    # =====================================================

    user_module_profile = doc.module_profile

    if (
        user_module_profile
        and restricted_modules
    ):

        # Get selected Module Profile
        module_profile_doc = frappe.get_doc(
            "Module Profile",
            user_module_profile
        )

        # Modules blocked by selected Module Profile
        blocked_modules = {
            row.module
            for row in module_profile_doc.block_modules
            if row.module
        }

        # Modules allowed by selected Module Profile
        all_modules = frappe.get_all(
            "Module Def",
            fields=["name"]
        )

        allowed_modules = {
            row.name
            for row in all_modules
            if row.name not in blocked_modules
        }

        # Check whether restricted modules are accessible
        restricted_access = (
            allowed_modules.intersection(
                restricted_modules
            )
        )

        if restricted_access:

            frappe.throw(
                _(
                    "You are not allowed to use these modules:<br><b>{0}</b>"
                ).format(
                    ", ".join(sorted(restricted_access))
                )
            )