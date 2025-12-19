import frappe


@frappe.whitelist()
def get_item_group_parents(child_group):
    result = {
        "department": None,
        "collection": None,
        "main_group": None
    }

    if not child_group:
        frappe.logger().info(result)
        return result

    # Level 1 → Kurta
    parent_1 = frappe.db.get_value("Item Group", child_group, "parent_item_group")
    result["department"] = parent_1

    # Level 2 → Summer
    parent_2 = frappe.db.get_value("Item Group", parent_1, "parent_item_group") if parent_1 else None
    result["collection"] = parent_2

    # Level 3 → Womens Ethnic
    parent_3 = frappe.db.get_value("Item Group", parent_2, "parent_item_group") if parent_2 else None
    result["main_group"] = parent_3

    frappe.logger().info(f"Item Group Parents: {result}")
    return result

@frappe.whitelist()
def all_item_group_for_silvet(doctype, txt, searchfield, start, page_len, filters):
    ItemGroup = frappe.qb.DocType("Item Group")

    base_groups = (
        frappe.qb.from_(ItemGroup)
        .select(
            ItemGroup.name,
            ItemGroup.parent_item_group,
            ItemGroup.lft
        )
        .where(ItemGroup.name.like(f"%{txt}%"))
        .orderby(ItemGroup.lft)
        .limit(page_len)
        .offset(start)
    ).run(as_dict=True)

    def get_full_path(name):
        path = []
        while name:
            parent = frappe.db.get_value(
                "Item Group",
                name,
                "parent_item_group"
            )
            path.insert(0, name)
            name = parent
        del path[0]
        return " -> ".join(path)

    results = []
    for g in base_groups:
        label = get_full_path(g["name"])

        if txt.lower() in label.lower():
            results.append((g["name"], label))

    return results
