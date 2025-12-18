import frappe

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
        return " -> ".join(path)

    results = []
    for g in base_groups:
        label = get_full_path(g["name"])

        if txt.lower() in label.lower():
            results.append((g["name"], label))

    return results
