import frappe


def execute():
    existing = frappe.get_all(
        "Custom DocPerm",
        filters={
            "parent": "Module Profile",
            "role": "All",
            "permlevel": 0,
        },
        fields=["name"],
    )

    if not existing:
        perm = frappe.new_doc("Custom DocPerm")
        perm.parent = "Module Profile"
        perm.parenttype = "DocType"
        perm.parentfield = "permissions"
        perm.role = "All"
        perm.permlevel = 0
        perm.read = 1
        perm.write = 1
        perm.create = 1
        perm.delete = 0
        perm.save(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()