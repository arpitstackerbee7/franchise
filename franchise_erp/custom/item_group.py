
import frappe
from frappe import _

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
        parent = frappe.db.get_value("Item Group", group, "parent_item_group")
        if not parent:
            return None
        # return readable name
        return frappe.db.get_value("Item Group", parent, "name")

    # Level 1
    result["department"] = get_parent_name(child_group)

    # Level 2
    parent_1 = frappe.db.get_value("Item Group", child_group, "parent_item_group")
    result["collection"] = get_parent_name(parent_1)

    # Level 3
    parent_2 = frappe.db.get_value("Item Group", parent_1, "parent_item_group") if parent_1 else None
    result["main_group"] = get_parent_name(parent_2)

    frappe.logger().info(f"Item Group Parents (Names): {result}")
    return result

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
#         # Get parent ID
#         parent = frappe.db.get_value("Item Group", group, "parent_item_group")
#         if not parent:
#             return None
#         # Get human-readable item_group_name like tree
#         return frappe.db.get_value("Item Group", parent, "item_group_name")

#     # Level 1 (direct parent)
#     result["department"] = get_parent_name(child_group)

#     # Level 2 (grandparent)
#     parent_1 = frappe.db.get_value("Item Group", child_group, "parent_item_group")
#     result["collection"] = get_parent_name(parent_1)

#     # Level 3 (great-grandparent)
#     parent_2 = frappe.db.get_value("Item Group", parent_1, "parent_item_group") if parent_1 else None
#     result["main_group"] = get_parent_name(parent_2)

#     frappe.logger().info(f"Item Group Parents (Names): {result}")
#     return result

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
def get_item_group_tree(doctype, parent=None):
    parent = parent or ""

    data = frappe.get_all(
        "Item Group",
        filters={
            "parent_item_group": parent or ""
        },
        fields=[
            "name",
            "parent_item_group as parent",
            "item_group_name",
            "is_group"
        ],
        order_by="lft"
    )

    tree = []
    for d in data:
        tree.append({
            "name": d.name,
            "parent": d.parent,
            "label": d.item_group_name,
            "is_group": d.is_group,
            "expandable": d.is_group
        })

    return tree




def autoname(doc, method=None):
    if doc.parent_item_group:
        doc.name = f"{doc.parent_item_group}-{doc.item_group_name}"
    else:
        # Root node or system-created group
        doc.name = doc.item_group_name


def validate_multiple_category_checks(doc,method):
    # Normalize checkbox values (TreeView / API safe)
    is_group = int(doc.is_group or 0)
    is_silhouette = int(doc.custom_is_silhouette or 0)

    is_department = int(doc.custom_is_departmnent or 0)
    is_collection = int(doc.custom_is_collection or 0)
    is_division = int(doc.custom_is_division or 0)

    # 1️⃣ Only ONE category checkbox allowed
    category_flags = [
        is_silhouette,
        is_department,
        is_collection,
        is_division,
    ]

    if sum(category_flags) > 1:
        frappe.throw(
            _("Only one Item Group Category can be selected"),
            title=_("Validation Error")
        )

    # 2️⃣ is_group and is_silhouette cannot be enabled together
    if is_group and is_silhouette:
        frappe.throw(
            _("Item Group(Silhoutte) cannot have 'Is Group' enabled"),
            title=_("Validation Error")
        )
