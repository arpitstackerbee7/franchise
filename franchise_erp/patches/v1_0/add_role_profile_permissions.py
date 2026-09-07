import frappe


def execute():
    # Check if permissions already exist
    existing = frappe.get_all(
        "Custom DocPerm",
        filters={
            "parent": "Role Profile",
            "role": "All",
        },
        fields=["name", "permlevel"],
    )

    existing_levels = {row.permlevel for row in existing}

    # Level 0
    if 0 not in existing_levels:
        perm = frappe.new_doc("Custom DocPerm")
        perm.parent = "Role Profile"
        perm.parenttype = "DocType"
        perm.parentfield = "permissions"
        perm.role = "All"
        perm.permlevel = 0
        perm.read = 1
        perm.write = 1
        perm.create = 1
        perm.delete = 0
        perm.save(ignore_permissions=True)

    # Level 1
    if 1 not in existing_levels:
        perm = frappe.new_doc("Custom DocPerm")
        perm.parent = "Role Profile"
        perm.parenttype = "DocType"
        perm.parentfield = "permissions"
        perm.role = "All"
        perm.permlevel = 1
        perm.read = 1
        perm.write = 1
        perm.create = 0
        perm.delete = 0
        perm.save(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()