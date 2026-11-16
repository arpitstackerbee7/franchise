import frappe


def execute():

    serials = frappe.get_all(
        "Serial No",
        filters={
            "custom_style": ["in", ["", None]]
        },
        fields=["name", "item_code"]
    )

    updated = 0

    for s in serials:

        if not s.item_code:
            continue

        # Item se style fetch
        style = frappe.db.get_value(
            "Item",
            s.item_code,
            "custom_barcode_code"
        )

        if style:

            # Direct DB update
            # modified time change nahi hoga
            frappe.db.sql("""
                UPDATE `tabSerial No`
                SET custom_style = %s
                WHERE name = %s
            """, (style, s.name))

            updated += 1

    frappe.db.commit()

    print(f"{updated} Serial No updated")