import frappe

@frappe.whitelist()
def get_next_item_no():
    # Total Item count
    count = frappe.db.count("Item")
    return count + 1

import frappe
import re


def get_silvet_code(silvet):
    """
    Silvet short code: first letter + middle letter
    """
    if not silvet or len(silvet) < 2:
        return silvet.upper() if silvet else "XX"
    mid_index = len(silvet) // 2
    return (silvet[0] + silvet[mid_index]).upper()

def get_department_code(department):
    """
    Simple department code:
    - Take first letter
    - If starts with number, include that
    """
    if not department:
        return "X"
    code = department[0].upper()
    match = re.search(r'\d+', department)
    if match:
        code += match.group(0)
    return code

# def get_department_code(department):
#     """
#     Department short code:
#     - First letter
#     - Agar number ho to include
#     Example:
#     KURTA → K
#     KURTA-2 → K2
#     """
#     if not department:
#         return "X"

#     first = department[0].upper()
#     match = re.search(r'\d+', department)
#     number = match.group(0) if match else ""

#     return f"{first}{number}"


def generate_item_code(doc, method):

    watched_fields = [
        "custom_group_collection",
        "custom_departments",
        "custom_silvet",
        "custom_colour_code",
        "custom_size"
    ]

    is_new = doc.is_new()
    changed = is_new

    if not is_new:
        prev = frappe.get_doc("Item", doc.name)
        for f in watched_fields:
            if getattr(prev, f, None) != getattr(doc, f, None):
                changed = True
                break

    if not changed:
        return

    collection = doc.custom_group_collection
    department = doc.custom_departments          # FULL VALUE
    silvet = doc.custom_silvet
    colour = doc.custom_colour_code or "XX"
    size = doc.custom_size or "M"

    if not collection or not department or not silvet:
        frappe.throw("Please select Collection, Department and Silvet")

    col_prefix = collection[0].upper()
    silvet_code = get_silvet_code(silvet)

    # 🔥 SHORT CODE ONLY FOR BARCODE
    dept_short = get_department_code(department)

    # ✅ FULL DEPARTMENT FOR ITEM CODE
    base_code = f"{col_prefix}-{department.upper()}-{silvet_code}-{colour}"

    # 🔥 BARCODE PREFIX (unchanged logic)
    barcode_prefix = f"{size}-{silvet_code}{dept_short}-{colour}"

    # 🔥 GET SAFE SERIES (Item + Barcode both checked)
    new_series = get_next_series(base_code, barcode_prefix, doc.name)

    # ---------------- ITEM CODE ----------------
    doc.flags.ignore_validate_update_after_submit = True
    doc.flags.ignore_mandatory = True

    doc.item_code = f"{base_code}-{new_series}"

    # ---------------- BARCODE ----------------
    doc.barcodes = []

    barcode_value = f"{barcode_prefix}-{new_series}"

    doc.append("barcodes", {
        "barcode": barcode_value,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })

def get_next_series(base_code, barcode_prefix, doc_name):
    """
    Find next available series considering:
    - Item Code
    - Barcode
    """

    # 1️⃣ From Item Code
    last_item = frappe.db.sql("""
        SELECT item_code FROM `tabItem`
        WHERE item_code LIKE %s
        AND name != %s
        ORDER BY item_code DESC
        LIMIT 1
    """, (base_code + "-%", doc_name))

    item_series = 0
    if last_item:
        match = re.search(r'(\d+)$', last_item[0][0])
        if match:
            item_series = int(match.group(1))

    # 2️⃣ From Barcode
    last_barcode = frappe.db.sql("""
        SELECT barcode FROM `tabItem Barcode`
        WHERE barcode LIKE %s
        ORDER BY barcode DESC
        LIMIT 1
    """, (barcode_prefix + "-%",))

    barcode_series = 0
    if last_barcode:
        match = re.search(r'(\d+)$', last_barcode[0][0])
        if match:
            barcode_series = int(match.group(1))

    # 3️⃣ Take max
    next_series = max(item_series, barcode_series) + 1

    return f"{next_series:02d}"
