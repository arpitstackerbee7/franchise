import frappe
def set_naming_series(doc, method):
    all_service = True

    for d in doc.items:
        item_group = frappe.db.get_value(
            "Item",
            d.item_code,
            "item_group"
        )

        if item_group != "All Item Groups-Services":
            all_service = False
            break

    if all_service:
        doc.naming_series = "SPI/.FY./."
    else:
        doc.naming_series = "PI/.FY./."


    