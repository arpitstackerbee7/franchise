import frappe

def create_sidebar_items():
    # Example sidebar item
    sidebar_items = [
        {
            "name": "grd6056sig",
            "label": "Franchise Dashboard",
            "module": "Franchise ERP",
            "parent_workspace": "Franchise Workspace"
        },
        # Add more items here if needed
    ]

    for item in sidebar_items:
        if not frappe.db.exists("Workspace Sidebar Item", item["name"]):
            doc = frappe.get_doc({
                "doctype": "Workspace Sidebar Item",
                "name": item["name"],
                "label": item["label"],
                "module": item["module"],
                "parent_workspace": item["parent_workspace"]
            })
            doc.insert()
