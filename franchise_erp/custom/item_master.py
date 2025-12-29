import frappe

@frappe.whitelist()
def get_next_item_no():
    # Total Item count
    count = frappe.db.count("Item")
    return count + 1

import frappe
import random

def get_item_group_code(value, label):

    if not value:
        frappe.throw(f"{label} is empty")

    # 1️⃣ Try direct name match (BEST case)
    code = frappe.db.get_value(
        "Item Group",
        value,
        "custom_code"
    )
    if code:
        return code

import re

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
    if not doc.is_stock_item:
        return 
    # ---------------- REQUIRED ----------------
    collection = doc.custom_group_collection
    department = doc.custom_departments
    silvet = doc.custom_silvet
    colour = doc.custom_colour_code

    if not collection or not department or not silvet or not colour:
        frappe.throw("Please select Collection, Department, Silhouette and Colour")

    # ---------------- FETCH CODES (WITH DEBUG) ----------------
    collection_code = get_item_group_code(collection, "COLLECTION")
    department_code = get_item_group_code(department, "DEPARTMENT")
    silvet_code = get_item_group_code(silvet, "SILVET")         

    # ---------------- DEBUG LOG ----------------
    frappe.log_error(
        f"""
        COLLECTION : {collection} → {collection_code}
        DEPARTMENT : {department} → {department_code}
        SILVET     : {silvet} → {silvet_code}
        COLOUR     : {colour}
        """,
        "ITEM CODE BUILD DEBUG"
    )

    # ---------------- VALIDATION ----------------
    if not collection_code:
        frappe.throw(f"Custom Code missing in Collection Item Group: {collection}")

    if not department_code:
        frappe.throw(f"Custom Code missing in Department Item Group: {department}")

    if not silvet_code:
        frappe.throw(f"Custom Code missing in Silvet Item Group: {silvet}")

    # ---------------- PREFIX BUILD ----------------
    base_code = f"{collection_code}-{department_code}-{silvet_code}-{colour}"

    # ---------------- NEXT SERIES ----------------
    next_series = get_next_series(base_code)

    # ---------------- ITEM CODE ----------------
    doc.flags.ignore_validate_update_after_submit = True
    doc.flags.ignore_mandatory = True

    doc.item_code = f"{base_code}-{next_series}"

    while frappe.db.exists("Item", doc.item_code):
        next_series += 1
        doc.item_code = f"{base_code}-{next_series}"

    # ---------------- BARCODE ----------------
    doc.barcodes = []
    doc.append("barcodes", {
        "barcode": doc.item_code,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })

    # ---------------- SERIAL NO SERIES ----------------
    # Get first (or only) record from TZU Setting
    tzu_record = frappe.db.get_value(
        "TZU Setting",
        filters={},  # empty filter gets first record (if any)
        fieldname=["serialno_series", "serial_no_uom", "batch_uom"],
        as_dict=True
    )

    if not tzu_record:
        frappe.throw("No TZU Setting record found.")

    first_letter = tzu_record.serialno_series or "T"
    serial_uom = tzu_record.serial_no_uom
    batch_uom = tzu_record.batch_uom

    random_series = random.randint(100000, 999999)

    # doc.has_serial_no = 1
    # doc.serial_no_series = f"{first_letter}{random_series}.#####"
    # Apply Serial No / Batch No logic
    if doc.stock_uom == serial_uom:
        doc.has_serial_no = 1
        doc.serial_no_series = f"{first_letter}{random_series}.#####"

    elif doc.stock_uom == batch_uom:
        doc.has_batch_no = 1
        doc.create_new_batch = 1
        doc.batch_number_series = f"{first_letter}{random_series}.#####"

    else:
        # Fallback: always create serial no
        doc.has_serial_no = 1
        doc.serial_no_series = f"{first_letter}{random_series}.#####"

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


# silvet dropdown tree method
@frappe.whitelist()
def all_item_group_for_silvet(doctype, txt, searchfield, start, page_len, filters):
    # Fetch only child items (is_group=0) and skip 'All Item Groups'
    children = frappe.db.get_all(
        "Item Group",
        filters={"is_group": 0, "item_group_name": ["!=", "All Item Groups"]},
        fields=["item_group_name", "parent_item_group"],
        order_by="lft",
        limit_start=start,
        limit_page_length=page_len
    )

    # Preload all item groups to reduce DB hits
    all_groups = frappe.db.get_all(
        "Item Group",
        fields=["item_group_name", "parent_item_group"]
    )
    parent_map = {g["item_group_name"]: g for g in all_groups}

    def get_full_path(child_name):
        """Return full path from root to child using item_group_name"""
        path = []
        current = child_name
        max_levels = 10
        level = 0
        while current and level < max_levels:
            label = parent_map.get(current, {}).get("item_group_name") or current
            if label != "All Item Groups":
                path.insert(0, label)  # prepend to path
            parent = parent_map.get(current, {}).get("parent_item_group")
            current = parent
            level += 1
        return " > ".join(path)

    results = []
    for c in children:
        full_path = get_full_path(c["item_group_name"])
        if not txt or txt.lower() in full_path.lower():
            # value = item_group_name, label = full path
            results.append([c["item_group_name"], full_path])

    return results
