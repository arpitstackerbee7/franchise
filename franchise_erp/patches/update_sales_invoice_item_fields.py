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
            (
                SELECT ip.price_list_rate
                FROM `tabItem Price` ip
                WHERE ip.item_code = sii.item_code
                  AND ip.price_list = 'MRP'
                ORDER BY ip.modified DESC
                LIMIT 1
            ) AS mrp
        FROM `tabSales Invoice Item` sii
        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code
    """, as_dict=True)

    updated = 0
    skipped = 0
    failed = 0

    for row in items:
        try:
            if not row.item_code:
                skipped += 1
                continue

            frappe.db.set_value(
                "Sales Invoice Item",
                row.name,
                {
                    "custom_count_of_pcs": row.custom_count_of_pcs,
                    "custom_top_fabric": row.custom_top_fabrics,
                    "custom_bottom_fabric": row.custom_bottom_fabric,
                    "custom_dupatta_fabric": row.custom_dupatta_fabric,
                    "custom_mrp": row.mrp or 0,
                },
                update_modified=False,
            )

            updated += 1

        except Exception:
            failed += 1
            frappe.log_error(
                frappe.get_traceback(),
                f"Sales Invoice Item Patch Failed: {row.name}"
            )

    frappe.db.commit()

    print(f"Updated : {updated}")
    print(f"Skipped : {skipped}")
    print(f"Failed  : {failed}")