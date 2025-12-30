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
def extract_uom_list(value):
    """
    Handles Table MultiSelect where Options = UOM Detail
    Value contains UOM Detail DOCNAMES
    """

    if not value:
        return []

    uoms = []

    # Table MultiSelect always returns list
    if isinstance(value, list):
        for rowname in value:
            if not rowname:
                continue

            # Fetch actual UOM from UOM Detail
            uom = frappe.db.get_value("UOM Detail", rowname, "uom_name")
            if uom:
                uoms.append(uom.strip())

    return uoms

def get_uoms_from_tzu(parentfield):
    """
    Fetch UOMs from TZU Setting child table
    """
    tzu = frappe.get_single("TZU Setting")
    rows = frappe.get_all(
        "UOM Detail",
        filters={
            "parent": tzu.name,
            "parentfield": parentfield
        },
        pluck="uom_name"  # make sure this is the correct fieldname in UOM Detail
    )
    return [u.strip() for u in rows if u]




def generate_item_code(doc, method):

    # --------------------------------------------------
    # Trigger fields
    # --------------------------------------------------
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

    if not changed or not doc.is_stock_item:
        return

    # --------------------------------------------------
    # Required validations
    # --------------------------------------------------
    collection = doc.custom_group_collection
    department = doc.custom_departments
    silvet = doc.custom_silvet
    colour = doc.custom_colour_code

    if not all([collection, department, silvet, colour]):
        frappe.throw(
            "Please select Collection, Department, Silhouette and Colour"
        )

    # --------------------------------------------------
    # Fetch Item Group Codes
    # --------------------------------------------------
    collection_code = get_item_group_code(collection, "COLLECTION")
    department_code = get_item_group_code(department, "DEPARTMENT")
    silvet_code = get_item_group_code(silvet, "SILVET")

    if not collection_code:
        frappe.throw(f"Custom Code missing in Collection Item Group: {collection}")

    if not department_code:
        frappe.throw(f"Custom Code missing in Department Item Group: {department}")

    if not silvet_code:
        frappe.throw(f"Custom Code missing in Silvet Item Group: {silvet}")

    # --------------------------------------------------
    # Item Code Build
    # --------------------------------------------------
    base_code = f"{collection_code}-{department_code}-{silvet_code}-{colour}"
    next_series = get_next_series(base_code)

    doc.flags.ignore_validate_update_after_submit = True
    doc.flags.ignore_mandatory = True

    item_code = f"{base_code}-{next_series}"
    while frappe.db.exists("Item", item_code):
        next_series += 1
        item_code = f"{base_code}-{next_series}"

    doc.item_code = item_code

    # --------------------------------------------------
    # Barcode Auto Create
    # --------------------------------------------------
    doc.barcodes = []
    doc.append("barcodes", {
        "barcode": doc.item_code,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })

   # --------------------------------------------------
    # TZU SETTING (FIXED)
    # --------------------------------------------------
    tzu = frappe.get_single("TZU Setting")

    # Usage
    serial_uom_list = get_uoms_from_tzu("serial_no_uom")  # child table fieldname in TZU Setting
    batch_uom_list = get_uoms_from_tzu("batch_uom")

    stock_uom = (doc.stock_uom or "").strip()

    # RESET FLAGS
    doc.has_serial_no = 0
    doc.has_batch_no = 0
    doc.create_new_batch = 0
    doc.serial_no_series = ""
    doc.batch_number_series = ""

    prefix = tzu.serialno_series or "T"
    random_series = random.randint(100000, 999999)

    # --------------------------------------------------
    # FINAL MATCHING LOGIC (AS YOU WANT)
    # --------------------------------------------------
    if stock_uom in serial_uom_list:
        doc.has_serial_no = 1
        doc.serial_no_series = f"{prefix}{random_series}.#####"

    elif stock_uom in batch_uom_list:
        doc.has_batch_no = 1
        doc.create_new_batch = 1
        doc.batch_number_series = f"{prefix}{random_series}.#####"

    else:
        frappe.throw(
        f"""
        Stock UOM <b>{stock_uom}</b> is not configured in TZU Setting.<br><br>
        <b>Serial No UOMs:</b> {", ".join(serial_uom_list) or "None"}<br>
        <b>Batch UOMs:</b> {", ".join(batch_uom_list) or "None"}
        """
    )



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
