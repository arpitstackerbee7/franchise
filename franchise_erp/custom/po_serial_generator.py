import frappe
import random
import string


def generate_random_numeric(length=12):
    """
    Generate numeric string which is NOT all zeros
    """
    while True:
        num = ''.join(random.choices(string.digits, k=length))
        if int(num) != 0:
            return num


def generate_po_serials(item_code, qty):
    item_doc = frappe.get_doc("Item", item_code)

    # ✔ Only if item has serial no enabled
    if not item_doc.has_serial_no:
        return ""

    prefix = (item_doc.brand or "T")[0].upper()
    serials = []

    for _ in range(int(qty)):
        while True:
            numeric = generate_random_numeric(12)
            serial = f"{prefix}{numeric}"

            # 🔒 duplicate check
            if not frappe.db.exists("Serial No", serial):
                break

        frappe.get_doc({
            "doctype": "Serial No",
            "serial_no": serial,
            "item_code": item_code
        }).insert(ignore_permissions=True)

        serials.append(serial)

    return "\n".join(serials)

def apply_po_serials(doc, method):
    for row in doc.items:
        if not row.serial_no:  # PO item field
            serials = generate_po_serials(
                row.item_code,
                int(row.qty)
            )
            if serials:
                row.serial_no = serials
