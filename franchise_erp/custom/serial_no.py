import frappe


def update_serial_custom_style():

    serials = frappe.db.sql("""
        SELECT
            sn.name,
            sn.item_code,
            i.custom_barcode_code
        FROM `tabSerial No` sn
        LEFT JOIN `tabItem` i
            ON i.name = sn.item_code
        WHERE IFNULL(sn.custom_style, '') = ''
        AND IFNULL(i.custom_barcode_code, '') != ''
        ORDER BY sn.creation DESC
        LIMIT 500
    """, as_dict=1)

    for d in serials:

        frappe.db.set_value(
            "Serial No",
            d.name,
            "custom_style",
            d.custom_barcode_code,
            update_modified=False
        )

    frappe.db.commit()