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



import frappe


@frappe.whitelist()
def validate_scanned_serial(serial_no):

    invoice = frappe.db.sql("""
        SELECT
            si.name,
            si.docstatus
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE IFNULL(sii.serial_no,'') LIKE %(serial)s
        LIMIT 1
    """, {
        "serial": f"%{serial_no}%"
    }, as_dict=True)

    if not invoice:
        return {
            "block": False
        }

    status_map = {
        0: "Draft",
        1: "Submitted",
        2: "Cancelled"
    }

    return {
        "block": True,
        "serial_no": serial_no,
        "invoice": invoice[0].name,
        "status": status_map.get(invoice[0].docstatus)
    }