import frappe

def apply_sales_term(doc, method):
    if not doc.custom_sales_term:
        return

    term = frappe.get_doc("Sales Term Template", doc.custom_sales_term)

    total_flat_discount = 0.0
    header_discount_percent = 0.0


    # -----------------------------------
    # 2️⃣ DOCUMENT LEVEL : DISCOUNT ONLY
    # -----------------------------------
    for row in term.sales_term_charges:
        if row.charge_type == "Discount":

            # Percentage discount on Net Total / Grand Total
            if row.value_type == "Percentage":
                header_discount_percent = row.value

            # Flat amount discount
            elif row.value_type == "Amount":
                total_flat_discount += row.value

            else:
                return


    # -----------------------------------
    # 3️⃣ PUSH TO ERPNext STANDARD FIELDS
    # -----------------------------------
    if header_discount_percent:
        doc.apply_discount_on = "Net Total"
        doc.additional_discount_percentage = header_discount_percent


    elif total_flat_discount:
        doc.apply_discount_on = "Net Total"
        doc.discount_amount = total_flat_discount



# import frappe


# @frappe.whitelist()
# def validate_scanned_serial(serial_no):

#     invoice = frappe.db.sql("""
#         SELECT
#             si.name,
#             si.docstatus
#         FROM `tabSales Invoice Item` sii
#         INNER JOIN `tabSales Invoice` si
#             ON si.name = sii.parent
#         WHERE IFNULL(sii.serial_no,'') LIKE %(serial)s
#         LIMIT 1
#     """, {
#         "serial": f"%{serial_no}%"
#     }, as_dict=True)

#     if not invoice:
#         return {
#             "block": False
#         }

#     status_map = {
#         0: "Draft",
#         1: "Submitted",
#         2: "Cancelled"
#     }

#     return {
#         "block": True,
#         "serial_no": serial_no,
#         "invoice": invoice[0].name,
#         "status": status_map.get(invoice[0].docstatus)
#     }

# @frappe.whitelist()
# def validate_scanned_serial(serial_no, customer):

#     item_code = frappe.db.get_value(
#         "Serial No",
#         serial_no,
#         "item_code"
#     )

#     if not item_code:
#         return {
#             "valid": False,
#             "message": "Invalid Serial No"
#         }

#     # invoice = frappe.db.sql("""
#     #     SELECT
#     #         si.name,
#     #         si.docstatus
#     #     FROM `tabSales Invoice Item` sii
#     #     INNER JOIN `tabSales Invoice` si
#     #         ON si.name = sii.parent
#     #     WHERE sii.serial_no LIKE %(serial)s
#     #     LIMIT 1
#     # """, {
#     #     "serial": f"%{serial_no}%"
#     # }, as_dict=True)
#     invoice = frappe.db.sql("""
#         SELECT
#             si.name,
#             si.docstatus,
#             si.customer
#         FROM `tabSales Invoice Item` sii
#         INNER JOIN `tabSales Invoice` si
#             ON si.name = sii.parent
#         WHERE
#             sii.serial_no LIKE %(serial)s
#             AND si.docstatus != 2
#         LIMIT 1
#     """, {
#         "serial": f"%{serial_no}%"
#     }, as_dict=True)

#     active_serials = frappe.get_all(
#         "Serial No",
#         filters={
#             "item_code": item_code,
#             "status": "Active"
#         },
#         fields=["name"],
#         limit_page_length=20
#     )

#     active_serials = [d.name for d in active_serials if d.name != serial_no]

#     if invoice:
#         return {
#             "used": True,
#             "invoice": invoice[0].name,
#             "status": {
#                 0: "Draft",
#                 1: "Submitted",
#                 2: "Cancelled"
#             }.get(invoice[0].docstatus),
#             "item_code": item_code,
#             "active_serials": active_serials
#         }

#     return {
#         "used": False,
#         "item_code": item_code,
#         "active_serials": active_serials
#     }

# @frappe.whitelist()
# def validate_scanned_serial(serial_no, customer=None):

#     # Get Item Code from Serial No
#     item_code = frappe.db.get_value(
#         "Serial No",
#         serial_no,
#         "item_code"
#     )

#     if not item_code:
#         return {
#             "valid": False,
#             "message": "Invalid Serial No"
#         }

#     # Check whether this serial is already used in any Sales Invoice
#     invoice = frappe.db.sql("""
#         SELECT
#             si.name,
#             si.docstatus,
#             si.customer
#         FROM `tabSales Invoice Item` sii
#         INNER JOIN `tabSales Invoice` si
#             ON si.name = sii.parent
#         WHERE
#             (
#                 sii.serial_no = %(serial)s
#                 OR sii.serial_no LIKE %(serial_start)s
#                 OR sii.serial_no LIKE %(serial_end)s
#                 OR sii.serial_no LIKE %(serial_middle)s
#             )
#             AND si.docstatus != 2
#         LIMIT 1
#     """, {
#         "serial": serial_no,
#         "serial_start": serial_no + "\n%",
#         "serial_end": "%\n" + serial_no,
#         "serial_middle": "%\n" + serial_no + "\n%"
#     }, as_dict=True)

#     # Get Active Serials of same Item
#     active_serials = frappe.get_all(
#         "Serial No",
#         filters={
#             "item_code": item_code,
#             "status": "Active"
#         },
#         pluck="name",
#         limit_page_length=20
#     )

#     active_serials = [d for d in active_serials if d != serial_no]

#     if invoice:
#         return {
#             "used": True,
#             "invoice": invoice[0].name,
#             "customer": invoice[0].customer,
#             "status": {
#                 0: "Draft",
#                 1: "Submitted",
#                 2: "Cancelled"
#             }.get(invoice[0].docstatus),
#             "item_code": item_code,
#             "active_serials": active_serials
#         }

#     return {
#         "used": False,
#         "item_code": item_code,
#         "active_serials": active_serials
#     }

import frappe


@frappe.whitelist()
def validate_scanned_serial(serial_no, customer=None):

    # Get Item Code
    item_code = frappe.db.get_value(
        "Serial No",
        serial_no,
        "item_code"
    )

    if not item_code:
        return {
            "valid": False,
            "message": "Invalid Serial No"
        }

    # ---------------------------------------------------
    # Check if scanned serial is already used
    # ---------------------------------------------------
    invoice = frappe.db.sql("""
        SELECT
            si.name,
            si.docstatus,
            si.customer
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE
            (
                sii.serial_no = %(serial)s
                OR sii.serial_no LIKE %(serial_start)s
                OR sii.serial_no LIKE %(serial_end)s
                OR sii.serial_no LIKE %(serial_middle)s
            )
            AND si.docstatus != 2
        LIMIT 1
    """, {
        "serial": serial_no,
        "serial_start": serial_no + "\n%",
        "serial_end": "%\n" + serial_no,
        "serial_middle": "%\n" + serial_no + "\n%"
    }, as_dict=True)

    # ---------------------------------------------------
    # Get all active serials of same item
    # ---------------------------------------------------
    all_active_serials = frappe.get_all(
        "Serial No",
        filters={
            "item_code": item_code,
            "status": "Active"
        },
        pluck="name"
    )

    active_serials = []

    for sr in all_active_serials:

        if sr == serial_no:
            continue

        # Check if this serial is already used
        already_used = frappe.db.sql("""
            SELECT si.name
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE
                (
                    sii.serial_no = %(serial)s
                    OR sii.serial_no LIKE %(serial_start)s
                    OR sii.serial_no LIKE %(serial_end)s
                    OR sii.serial_no LIKE %(serial_middle)s
                )
                AND si.docstatus != 2
            LIMIT 1
        """, {
            "serial": sr,
            "serial_start": sr + "\n%",
            "serial_end": "%\n" + sr,
            "serial_middle": "%\n" + sr + "\n%"
        })

        # Only show serials not used in Sales Invoice
        if not already_used:
            active_serials.append(sr)

        # Limit popup size
        if len(active_serials) >= 20:
            break

    # ---------------------------------------------------
    # If scanned serial already used
    # ---------------------------------------------------
    if invoice:
        return {
            "used": True,
            "invoice": invoice[0].name,
            "customer": invoice[0].customer,
            "status": {
                0: "Draft",
                1: "Submitted",
                2: "Cancelled"
            }.get(invoice[0].docstatus),
            "item_code": item_code,
            "active_serials": active_serials
        }

    # ---------------------------------------------------
    # If scanned serial is available
    # ---------------------------------------------------
    return {
        "used": False,
        "item_code": item_code,
        "active_serials": active_serials
    }