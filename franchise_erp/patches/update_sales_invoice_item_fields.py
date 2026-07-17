import frappe


def execute():

    items = frappe.db.sql("""
        SELECT
            sii.name,
            sii.item_code,
            i.custom_count_of_pcs,
            i.custom_top_fabrics,
            i.custom_bottom_fabric,
            i.custom_dupatta_fabric,
            ip.price_list_rate AS mrp
        FROM `tabSales Invoice Item` sii
        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code
        LEFT JOIN `tabItem Price` ip
            ON ip.item_code = sii.item_code
            AND ip.price_list = 'MRP'
    """, as_dict=True)

    updated = 0

    for row in items:

        frappe.db.sql("""
            UPDATE `tabSales Invoice Item`
            SET
                custom_count_of_pcs = %s,
                custom_top_fabric = %s,
                custom_bottom_fabric = %s,
                custom_dupatta_fabric = %s,
                custom_mrp = %s
            WHERE name = %s
        """, (
            row.custom_count_of_pcs,
            row.custom_top_fabrics,
            row.custom_bottom_fabric,
            row.custom_dupatta_fabric,
            row.mrp or 0,
            row.name
        ))

        updated += 1

    frappe.db.commit()

    print(f"{updated} Sales Invoice Items updated")