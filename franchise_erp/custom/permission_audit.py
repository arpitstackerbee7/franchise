import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from frappe.core.page.permission_manager.permission_manager import (
    add as original_add,
    update as original_update,
    remove as original_remove,
    reset as original_reset,
)


PERMISSION_FIELDS = [
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "print",
    "email",
    "report",
    "import",
    "export",
    "share",
    "if_owner",
]


def _as_int(value):
    return 1 if str(value) in ("1", "True", "true") else 0


def _get_permission_row(
    doctype,
    role,
    permlevel,
    if_owner=0,
):
    """
    Get the effective permission row.

    Prefer Custom DocPerm because Role Permission Manager modifies
    Custom DocPerm.
    """

    filters = {
        "parent": doctype,
        "role": role,
        "permlevel": permlevel,
        "if_owner": if_owner,
    }

    custom = frappe.get_all(
        "Custom DocPerm",
        filters=filters,
        fields="*",
        limit=1,
    )

    if custom:
        row = custom[0]
        row["_source"] = "Custom DocPerm"
        return row

    standard = frappe.get_all(
        "DocPerm",
        filters=filters,
        fields="*",
        limit=1,
    )

    if standard:
        row = standard[0]
        row["_source"] = "DocPerm"
        return row

    return None


def _create_audit_log(
    *,
    action,
    status,
    document_type,
    role,
    permlevel=0,
    permission_type=None,
    old_value=None,
    new_value=None,
    before_snapshot=None,
    after_snapshot=None,
):
    doc = frappe.get_doc(
        {
            "doctype": "Permission Audit Log",
            "log_id": frappe.generate_hash(length=12),
            "action": action,
            "status": status,
            "changed_by": frappe.session.user,
            "changed_at": now_datetime(),
            "document_type": document_type,
            "role": role,
            "permlevel": permlevel,
            "permission_type": permission_type,
            "old_value": (
                None if old_value is None else str(old_value)
            ),
            "new_value": (
                None if new_value is None else str(new_value)
            ),
            "permission_snapshot": (
                json.dumps(before_snapshot, indent=2, default=str)
                if before_snapshot
                else None
            ),
            "before_snapshot": (
                json.dumps(before_snapshot, indent=2, default=str)
                if before_snapshot
                else None
            ),
            "after_snapshot": (
                json.dumps(after_snapshot, indent=2, default=str)
                if after_snapshot
                else None
            ),
        }
    )

    doc.insert(ignore_permissions=True)

    return doc.name


@frappe.whitelist()
def add(parent: str, role: str, permlevel: int):
    """
    Audit Permission Manager -> Add New Rule.
    """

    frappe.only_for("System Manager")

    # Execute original Frappe operation first.
    result = original_add(
        parent=parent,
        role=role,
        permlevel=permlevel,
    )

    after = _get_permission_row(
        parent,
        role,
        permlevel,
        0,
    )

    _create_audit_log(
        action="ADD",
        status="Changed",
        document_type=parent,
        role=role,
        permlevel=permlevel,
        before_snapshot=None,
        after_snapshot=after,
    )

    return result


@frappe.whitelist()
def update(
    doctype: str,
    role: str,
    permlevel: int,
    ptype: str,
    value=None,
    if_owner=0,
):
    """
    Audit Permission Manager checkbox changes.
    """

    frappe.only_for("System Manager")

    before = _get_permission_row(
        doctype,
        role,
        permlevel,
        _as_int(if_owner),
    )

    old_value = None

    if before:
        old_value = before.get(ptype)

    # Execute original Frappe permission update.
    result = original_update(
        doctype=doctype,
        role=role,
        permlevel=permlevel,
        ptype=ptype,
        value=value,
        if_owner=if_owner,
    )

    after = _get_permission_row(
        doctype,
        role,
        permlevel,
        _as_int(if_owner),
    )

    new_value = None

    if after:
        new_value = after.get(ptype)

    # Only log an actual change.
    if str(old_value) != str(new_value):

        _create_audit_log(
            action="UPDATE",
            status="Changed",
            document_type=doctype,
            role=role,
            permlevel=permlevel,
            permission_type=ptype,
            old_value=old_value,
            new_value=new_value,
            before_snapshot=before,
            after_snapshot=after,
        )

    return result


@frappe.whitelist()
def remove(
    doctype: str,
    role: str,
    permlevel: int,
    if_owner=0,
):
    """
    Audit complete permission rule deletion.
    """

    frappe.only_for("System Manager")

    if_owner = _as_int(if_owner)

    # IMPORTANT:
    # Capture complete permission row BEFORE deletion.
    before = _get_permission_row(
        doctype,
        role,
        permlevel,
        if_owner,
    )

    # Execute original Frappe remove.
    result = original_remove(
        doctype=doctype,
        role=role,
        permlevel=permlevel,
        if_owner=if_owner,
    )

    # Log deletion.
    _create_audit_log(
        action="DELETE",
        status="Deleted",
        document_type=doctype,
        role=role,
        permlevel=permlevel,
        before_snapshot=before,
        after_snapshot=None,
    )

    return result


@frappe.whitelist()
def reset(doctype: str):
    """
    Audit Restore Original Permissions.

    Captures all Custom DocPerm rows before reset,
    executes the original Frappe reset,
    captures standard DocPerm rows after reset,
    and creates a RESET audit log.
    """

    frappe.only_for("System Manager")

    # ---------------------------------------------------------
    # CAPTURE CUSTOM PERMISSIONS BEFORE RESET
    # ---------------------------------------------------------
    before_rows = frappe.get_all(
        "Custom DocPerm",
        filters={
            "parent": doctype,
        },
        fields="*",
        order_by="permlevel",
    )

    # ---------------------------------------------------------
    # EXECUTE ORIGINAL FRAPPE RESET
    # ---------------------------------------------------------
    result = original_reset(doctype)

    # ---------------------------------------------------------
    # CAPTURE STANDARD PERMISSIONS AFTER RESET
    # ---------------------------------------------------------
    after_rows = frappe.get_all(
        "DocPerm",
        filters={
            "parent": doctype,
        },
        fields="*",
        order_by="permlevel",
    )

    # ---------------------------------------------------------
    # GET A VALID ROLE FOR AUDIT LOG
    # ---------------------------------------------------------
    user_roles = frappe.get_roles(frappe.session.user)

    audit_role = "System Manager"

    if "System Manager" not in user_roles:
        valid_roles = [
            role
            for role in user_roles
            if frappe.db.exists("Role", role)
        ]

        if valid_roles:
            audit_role = valid_roles[0]

    # ---------------------------------------------------------
    # CREATE RESET AUDIT LOG
    # ---------------------------------------------------------
    _create_audit_log(
        action="RESET",
        status="Reset",
        document_type=doctype,
        role=audit_role,
        permlevel=0,
        before_snapshot={
            "custom_permissions": before_rows,
        },
        after_snapshot={
            "standard_permissions": after_rows,
        },
    )

    frappe.clear_cache(doctype=doctype)

    return result



@frappe.whitelist()
def restore_permission(log_name):
    """
    Restore a deleted permission rule from Permission Audit Log.
    """

    frappe.only_for("System Manager")

    audit = frappe.get_doc(
        "Permission Audit Log",
        log_name,
    )

    if audit.action != "DELETE":
        frappe.throw(
            _("Only deleted permission rules can be restored.")
        )

    if audit.status != "Deleted":
        frappe.throw(
            _("This permission has already been restored.")
        )

    if not audit.permission_snapshot:
        frappe.throw(
            _("Permission snapshot is missing.")
        )

    snapshot = frappe.parse_json(
        audit.permission_snapshot
    )

    doctype = snapshot.get("parent")
    role = snapshot.get("role")
    permlevel = int(snapshot.get("permlevel") or 0)
    if_owner = int(snapshot.get("if_owner") or 0)

    # Check if same permission rule already exists.
    existing = frappe.get_all(
        "Custom DocPerm",
        filters={
            "parent": doctype,
            "role": role,
            "permlevel": permlevel,
            "if_owner": if_owner,
        },
        limit=1,
    )

    if existing:
        frappe.throw(
            _(
                "Permission rule already exists for "
                "{0} / {1} / Level {2}."
            ).format(
                doctype,
                role,
                permlevel,
            )
        )

    # Only fields belonging to Custom DocPerm.
    allowed_fields = {
        "parent",
        "role",
        "permlevel",
        "if_owner",
        "read",
        "write",
        "create",
        "delete",
        "submit",
        "cancel",
        "amend",
        "print",
        "email",
        "report",
        "import",
        "export",
        "share",
    }

    values = {
        key: value
        for key, value in snapshot.items()
        if key in allowed_fields
    }

    values["doctype"] = "Custom DocPerm"

    restored = frappe.get_doc(values)

    restored.insert(
        ignore_permissions=True
    )

    # Mark original audit record as restored.
    audit.status = "Restored"
    audit.restored_at = now_datetime()
    audit.restored_by = frappe.session.user
    audit.restore_result = (
        f"Restored {doctype} / {role} / "
        f"Permission Level {permlevel}"
    )

    audit.save(
        ignore_permissions=True
    )

    # Create a separate RESTORE audit record.
    _create_audit_log(
        action="RESTORE",
        status="Restored",
        document_type=doctype,
        role=role,
        permlevel=permlevel,
        before_snapshot=None,
        after_snapshot=values,
    )

    frappe.clear_cache(doctype=doctype)

    return {
        "success": True,
        "message": _(
            "Permission restored successfully."
        ),
    }