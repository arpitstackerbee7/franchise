
import frappe

# @frappe.whitelist()
# def get_item_group_parents(child_group):
#     result = {
#         "department": None,
#         "collection": None,
#         "main_group": None
#     }

#     if not child_group:
#         return result

#     def get_parent_name(group):
#         if not group:
#             return None
#         parent = frappe.db.get_value("Item Group", group, "parent_item_group")
#         if not parent:
#             return None
#         # return readable name
#         return frappe.db.get_value("Item Group", parent, "name")

#     # Level 1
#     result["department"] = get_parent_name(child_group)

#     # Level 2
#     parent_1 = frappe.db.get_value("Item Group", child_group, "parent_item_group")
#     result["collection"] = get_parent_name(parent_1)

#     # Level 3
#     parent_2 = frappe.db.get_value("Item Group", parent_1, "parent_item_group") if parent_1 else None
#     result["main_group"] = get_parent_name(parent_2)

#     frappe.logger().info(f"Item Group Parents (Names): {result}")
#     return result

@frappe.whitelist()
def get_item_group_parents(child_group):
    result = {
        "department": None,
        "collection": None,
        "main_group": None
    }

    if not child_group:
        return result

    def get_parent_name(group):
        if not group:
            return None
        # Get parent ID
        parent = frappe.db.get_value("Item Group", group, "parent_item_group")
        if not parent:
            return None
        # Get human-readable item_group_name like tree
        return frappe.db.get_value("Item Group", parent, "item_group_name")

    # Level 1 (direct parent)
    result["department"] = get_parent_name(child_group)

    # Level 2 (grandparent)
    parent_1 = frappe.db.get_value("Item Group", child_group, "parent_item_group")
    result["collection"] = get_parent_name(parent_1)

    # Level 3 (great-grandparent)
    parent_2 = frappe.db.get_value("Item Group", parent_1, "parent_item_group") if parent_1 else None
    result["main_group"] = get_parent_name(parent_2)

    frappe.logger().info(f"Item Group Parents (Names): {result}")
    return result

# def validate_same_parent(doc, method=None):
#     """
#     Block same item_group_name OR same custom_code under same parent
#     Allow duplicates under different parent
#     """

#     parent = doc.parent_item_group or "All Item Groups"

#     # ---- CUSTOM CODE DUPLICATE CHECK ----
#     if doc.custom_code:
#         code_exists = frappe.db.exists(
#             "Item Group",
#             {
#                 "parent_item_group": parent,
#                 "custom_code": doc.custom_code,
#                 "name": ["!=", doc.name]
#             }
#         )

#         if code_exists:
#             frappe.throw(
#                 f"Item Group Code '{doc.custom_code}' already exists under '{parent}'"
#             )
def validate_same_parent(doc, method=None):
    """
    Block same item_group_name OR same custom_code under same parent
    Allow duplicates under different parent
    """

    parent = doc.parent_item_group or "All Item Groups"

    # -------------------------------
    # 1️⃣ ITEM GROUP NAME DUPLICATE CHECK
    # -------------------------------
    name_exists = frappe.db.exists(
        "Item Group",
        {
            "parent_item_group": parent,
            "item_group_name": doc.item_group_name,
            "name": ["!=", doc.name]
        }
    )

    if name_exists:
        frappe.throw(
            f"Item Group '{doc.item_group_name}' already exists under '{parent}'"
        )

    # -------------------------------
    # 2️⃣ CUSTOM CODE DUPLICATE CHECK
    # -------------------------------
    if doc.custom_code:
        code_exists = frappe.db.exists(
            "Item Group",
            {
                "parent_item_group": parent,
                "custom_code": doc.custom_code,
                "name": ["!=", doc.name]
            }
        )

        if code_exists:
            frappe.throw(
                f"Item Group Code '{doc.custom_code}' already exists under '{parent}'"
            )


@frappe.whitelist()
def get_child_item_groups(doctype, txt, searchfield, start, page_len, filters):

    item_groups = frappe.db.get_all(
        "Item Group",
        filters={
            "is_group": 0,
            "name": ["!=", "All Item Groups"],
            "item_group_name": ["!=", "All Item Groups"]
        },
        fields=["name", "lft", "rgt", "item_group_name"],
        order_by="lft"
    )

    result = []

    for ig in item_groups:
        label = get_item_group_path_limited(ig.name, max_parents=3)

        if not txt or txt.lower() in label.lower():
            # 👇 THIS FORMAT IS REQUIRED
            result.append([
                ig.name,   # value (saved)
                label      # description (tree shown)
            ])

    return result[start:start + page_len]

def get_item_group_path_limited(item_group, max_parents=3):

    rows = frappe.db.sql("""
        SELECT parent.item_group_name
        FROM `tabItem Group` child
        JOIN `tabItem Group` parent
          ON parent.lft <= child.lft
         AND parent.rgt >= child.rgt
        WHERE child.name = %s
        ORDER BY parent.lft
    """, item_group, as_dict=True)

    if not rows:
        return ""

    child = rows[-1]["item_group_name"]
    parents = [r["item_group_name"] for r in rows[:-1]][-max_parents:]

    return " > ".join(parents + [child])

#for item group tree showing item group name only
@frappe.whitelist()
def get_item_group_tree(doctype, parent):
    parent = parent or "All Item Groups"

    # Agar parent "All Item Groups" hai, to manually root node bana do
    if parent == "All Item Groups":
        tree = [{
            "name": "All Item Groups",
            "label": "All Item Groups",  # 👈 Manual label
            "is_group": 1
        }]
    else:
        tree = []

    data = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": parent},
        fields=["name", "item_group_name", "is_group"],
        order_by="name"
    )

    for d in data:
        label = d.item_group_name if d.item_group_name else d.name
        node = {
            "name": d.name,
            "label": label,
            "is_group": d.is_group
        }
        tree.append(node)

    return tree


    data = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": parent},
        fields=["name", "item_group_name", "is_group"],
        order_by="name"
    )

    # Return tree nodes
    return [
        {
            "name": d.name,
            "label": d.item_group_name or d.name,  # 👈 label fallback
            "is_group": d.is_group
        } for d in data
    ]

