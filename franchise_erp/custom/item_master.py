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


import frappe
import re
import random


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

    # ---------------- REQUIRED FIELDS ----------------
    collection = doc.custom_group_collection
    department = doc.custom_departments
    silvet = doc.custom_silvet
    colour = doc.custom_colour_code
    size = doc.custom_size

    if not collection or not department or not silvet or not colour:
        frappe.throw("Please select Collection, Department, Silvet and Colour")

    # ---------------- PREFIX BUILD ----------------
    col_prefix = collection[0].upper()
    silvet_code = get_silvet_code(silvet)
    dept_short = get_department_code(department)

    base_code = f"{col_prefix}-{department.upper()}-{silvet_code}-{colour}"

    # ---------------- NEXT SERIES (SAFE) ----------------
    next_series = get_next_series(base_code)

    # ---------------- ITEM CODE ----------------
    doc.flags.ignore_validate_update_after_submit = True
    doc.flags.ignore_mandatory = True

    doc.item_code = f"{base_code}-{next_series}"

    # 🔒 FINAL DUPLICATE SAFETY (NO ERROR EVER)
    while frappe.db.exists("Item", doc.item_code):
        next_series += 1
        doc.item_code = f"{base_code}-{next_series}"

    # ---------------- BARCODE (SAME AS ITEM CODE) ----------------
    doc.barcodes = []
    doc.append("barcodes", {
        "barcode": doc.item_code,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })

    # ---------------- SERIAL NO SERIES ----------------
    # TZU Setting is NOT Single → get any one record
    first_letter = frappe.db.get_value(
        "TZU Setting",
        {},
        "serialno_series"
    ) or "T"

    random_series = random.randint(10000, 99999)

    doc.has_serial_no = 1
    doc.serial_no_series = f"{first_letter}{random_series}.#####"

    frappe.logger().info(
        f"Item Code: {doc.item_code} | Serial Series: {doc.serial_no_series}"
    )


# ------------------------------------------------------------------


def get_next_series(base_code):
    """
    Always returns NEXT AVAILABLE INTEGER series
    Example:
    S-KURTA-AK-BL-17 exists → returns 18
    """

    last_item = frappe.db.sql("""
        SELECT item_code
        FROM `tabItem`
        WHERE item_code LIKE %s
        ORDER BY CAST(SUBSTRING_INDEX(item_code, '-', -1) AS UNSIGNED) DESC
        LIMIT 1
    """, (base_code + "-%",), as_dict=True)

    if last_item:
        match = re.search(r'-(\d+)$', last_item[0]["item_code"])
        if match:
            return int(match.group(1)) + 1

    return 1


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

# for tree
# import frappe
# from frappe import _

# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def item_group_query(doctype, txt, searchfield, start, page_len, filters=None):
#     """
#     Returns leaf item groups (is_group=0) with full hierarchy in the name for display.
#     Format: Child > Parent > Parent
#     """
#     filters = filters or {}

#     # Only leaf nodes
#     conditions = ["is_group=0"]

#     if filters.get("is_group") is not None:
#         conditions.append(f"is_group = {int(filters.get('is_group'))}")

#     # Get leaf nodes
#     leaf_groups = frappe.db.sql(
#         f"""
#         SELECT name, parent_item_group
#         FROM `tabItem Group`
#         WHERE {searchfield} LIKE %(txt)s
#         AND {" AND ".join(conditions)}
#         ORDER BY name
#         LIMIT %(page_len)s OFFSET %(start)s
#         """,
#         {
#             "txt": "%%%s%%" % txt,
#             "_txt": txt,
#             "start": start,
#             "page_len": page_len,
#         },
#         as_dict=1
#     )

#     result = []
#     for group in leaf_groups:
#         hierarchy = [group.name]
#         parent = group.parent_item_group

#         # Build parent chain
#         while parent:
#             hierarchy.append(parent)
#             parent = frappe.db.get_value("Item Group", parent, "parent_item_group")

#         # Reverse so that child > parent > parent
#         display_name = " > ".join(hierarchy)
#         result.append((group.name, display_name))  # first value used as actual Link

#     return result
