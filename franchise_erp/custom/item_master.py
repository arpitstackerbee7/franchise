import frappe
import random
import re

@frappe.whitelist()
def get_next_item_no():
    # Total Item count
    count = frappe.db.count("Item")
    return count + 1



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
            uom = frappe.db.get_value("UOM Detail", rowname, "uom")
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
        pluck="uom"  # make sure this is the correct fieldname in UOM Detail
    )
    return [u.strip() for u in rows if u]


def generate_item_code(doc, method):

    if not doc.is_stock_item:
        return

    # 🔒 RUN ONLY ON CREATE
    if not doc.is_new():
        return

    if not all([
        doc.custom_group_collection,
        doc.custom_departments,
        doc.custom_silvet,
        doc.custom_colour_code
    ]):
        frappe.throw(
            "Please select Collection, Department, Silhouette and Colour"
        )

    collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
    department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
    silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

    base_code = f"{collection_code}-{department_code}-{silvet_code}-{doc.custom_colour_code}"
    next_series = get_next_series(base_code)

    item_code = f"{base_code}-{next_series}"
    while frappe.db.exists("Item", item_code):
        next_series += 1
        item_code = f"{base_code}-{next_series}"

    doc.item_code = item_code
    doc.item_name = item_code


def create_item_barcode(doc, method):

    if not doc.is_stock_item:
        return

    # Already exists → skip
    if frappe.db.exists("Item Barcode", {
        "parent": doc.name,
        "barcode": doc.item_code
    }):
        return

    doc.append("barcodes", {
        "barcode": doc.item_code,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })

    doc.save(ignore_permissions=True)

def apply_tzu_setting(doc, method):

    if not doc.is_stock_item:
        return

    if not doc.stock_uom:
        frappe.throw("Stock UOM is mandatory for Stock Item")

    tzu = frappe.get_single("TZU Setting")

    serial_uom_list = get_uoms_from_tzu("serial_no_uom")
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

    # ✅ SERIAL MATCH
    if stock_uom in serial_uom_list:
        doc.has_serial_no = 1
        doc.serial_no_series = f"{prefix}{random_series}.#####"

    # ✅ BATCH MATCH
    elif stock_uom in batch_uom_list:
        doc.has_batch_no = 1
        doc.create_new_batch = 1
        doc.batch_number_series = f"{prefix}{random_series}.#####"

    #NOT CONFIGURED → BLOCK SAVE
    else:
        frappe.throw(
            f"""
            Stock UOM <b>{stock_uom}</b> is not configured.<br><br>
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
