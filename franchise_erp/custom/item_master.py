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


# def generate_item_code(doc, method):

#     if not doc.is_stock_item:
#         return

#     # 🔒 RUN ONLY ON CREATE
#     if not doc.is_new():
#         return

#     if not all([
#         doc.custom_group_collection,
#         doc.custom_departments,
#         doc.custom_silvet,
#         doc.custom_colour_code
#     ]):
#         frappe.throw(
#             "Please select Collection, Department, Silhouette and Colour"
#         )

#     collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
#     department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
#     silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

#     # base_code = f"{collection_code}-{department_code}-{silvet_code}-{doc.custom_colour_code}"
#     # next_series = get_next_series(base_code)
#     # item_code = f"{base_code}-{next_series}"
#     #--------------------------------------------------------------------------------------------

#     #Colour code intentionally removed
#     base_code = f"{collection_code}{department_code}{silvet_code}"
#     next_series = get_next_series(base_code)
#     #No dashes at all
#     item_code = f"{base_code}{next_series}"

#     while frappe.db.exists("Item", item_code):
#         next_series += 1
#         item_code = f"{base_code}{next_series}"

#     doc.item_code = item_code
#     doc.item_name = item_code

# def generate_item_code(doc, method):

#     # IMPORT TIME VALIDATION SKIP
#     # if frappe.flags.in_import:
#     #     return
    
#     if not doc.is_stock_item:
#         return

#     # 🔒 ONLY ON CREATE
#     if not doc.is_new():
#         return

#     if not all([
#         doc.custom_group_collection,
#         doc.custom_departments,
#         doc.custom_silvet,
#         doc.custom_colour_code,
#         doc.custom_sup_design_no
#     ]):
#         frappe.throw(
#             "Please select Collection, Department, Silhouette, Colour and Supplier Design No"
#         )

#     collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
#     department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
#     silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

#     # --------------------------------------------------
#     # ITEM CODE (always unique)
#     # --------------------------------------------------
#     base_code = f"{collection_code}{department_code}{silvet_code}"
#     next_series = get_next_series(base_code)

#     item_code = f"{base_code}{next_series}"
#     while frappe.db.exists("Item", item_code):
#         next_series += 1
#         item_code = f"{base_code}{next_series}"

#     doc.item_code = item_code
#     doc.item_name = item_code

# # --------------------------------------------------
# # BARCODE LOGIC (supplier design based)
# # --------------------------------------------------
#     existing_barcode = frappe.db.get_value(
#         "Item",
#         {
#             "custom_sup_design_no": doc.custom_sup_design_no,
#         },
#         "custom_barcode_code",   # 👈 IMPORTANT FIX
#         order_by="creation asc"
#     )

#     if existing_barcode:
#         # ✅ SAME supplier design → SAME BARCODE (previous item ka)
#         doc.custom_barcode_code = existing_barcode
#     else:
#         # ✅ NEW supplier design → CURRENT ITEM CODE
#         # ERPNext me item code = name
#         doc.custom_barcode_code = doc.item_code

# def generate_item_code(doc, method):

#     # IMPORT TIME VALIDATION SKIP
#     # if frappe.flags.in_import:
#     #     return

#     # ✅ BYPASS CHECK
#     if doc.custom_bypass_serialbatch:
#         return
    
#     if not doc.is_stock_item:
#         return

#     # 🔒 ONLY ON CREATE
#     if not doc.is_new():
#         return

#     required_fields = {
#         "Collection": doc.custom_group_collection,
#         "Department": doc.custom_departments,
#         "Silhouette": doc.custom_silvet,
#         # "Colour": doc.custom_colour_code,
#         "Supplier Design No": doc.custom_sup_design_no
#     }

#     missing = [label for label, value in required_fields.items() if not value]

#     if missing:
#         frappe.throw(
#             "Missing required fields: " + ", ".join(missing)
#         )

#     collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
#     department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
#     silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

#     # --------------------------------------------------
#     # ITEM CODE (always unique)
#     # --------------------------------------------------
#     base_code = f"{collection_code}{department_code}{silvet_code}"
#     next_series = get_next_series(base_code)

#     item_code = f"{base_code}{next_series}"
#     while frappe.db.exists("Item", item_code):
#         next_series += 1
#         item_code = f"{base_code}{next_series}"

#     doc.item_code = item_code
#     doc.item_name = item_code

# # --------------------------------------------------
# # BARCODE LOGIC (supplier design based)
# # --------------------------------------------------
#     existing_barcode = frappe.db.get_value(
#         "Item",
#         {
#             "custom_sup_design_no": doc.custom_sup_design_no,
#         },
#         "custom_barcode_code",   # 👈 IMPORTANT FIX
#         order_by="creation asc"
#     )

#     if existing_barcode:
#         # ✅ SAME supplier design → SAME BARCODE (previous item ka)
#         doc.custom_barcode_code = existing_barcode
#     else:
#         # ✅ NEW supplier design → CURRENT ITEM CODE
#         # ERPNext me item code = name
#         doc.custom_barcode_code = doc.item_code

def generate_item_code(doc, method):

    if doc.custom_bypass_serialbatch:
        return

    if not doc.is_stock_item:
        return

    # 🔒 ONLY NEW ITEM
    if not doc.is_new():
        return

    # ---------------- REQUIRED FIELDS ----------------
    required_fields = {
        "Collection": doc.custom_group_collection,
        "Department": doc.custom_departments,
        "Silhouette": doc.custom_silvet,
        "Supplier Design No": doc.custom_sup_design_no,
        "Colour": doc.custom_colour_name,
        "Size": doc.custom_size
    }

    missing = [k for k, v in required_fields.items() if not v]
    if missing:
        frappe.throw("Missing required fields: " + ", ".join(missing))

    # ---------------- MASTER CODES ----------------
    collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
    department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
    silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

    colour_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code")
    if not colour_code:
        frappe.throw("Colour Code not found")

    size_code = frappe.db.get_value("Size", doc.custom_size, "size_code")
    if not size_code:
        frappe.throw("Size Code not found")

    # ---------------- BASE STYLE ----------------
    base_code = f"{collection_code}{department_code}{silvet_code}"
    next_series = get_next_series(base_code)

    base_item_code = f"{base_code}{next_series}"
    while frappe.db.exists("Item", {"item_code": ["like", f"{base_item_code}%"]}):
        next_series += 1
        base_item_code = f"{base_code}{next_series}"

    # ---------------- FINAL ITEM CODE ----------------
    final_item_code = f"{base_item_code}{colour_code}{size_code}"

    doc.item_code = final_item_code
    doc.item_name = final_item_code

    # ---------------- BARCODE / STYLE ----------------
    existing_style = frappe.db.get_value(
        "Item",
        {"custom_sup_design_no": doc.custom_sup_design_no},
        "custom_barcode_code",
        order_by="creation asc"
    )

    # NEW item me bhi style kabhi color/size ke saath nahi jayega
    doc.custom_barcode_code = existing_style or base_item_code
       # ---------------- BARCODE CHILD TABLE (CREATE TIME) ----------------
    # ensure only ONE row
    doc.set("barcodes", [])

    doc.append("barcodes", {
        "barcode": final_item_code,          # 👈 STYLE ONLY
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos"
    })
    
def update_style_on_supplier_design_change(doc, method):

    if doc.is_new():
        return

    old = doc.get_doc_before_save()
    if not old:
        return

    # supplier design change nahi hua
    if old.custom_sup_design_no == doc.custom_sup_design_no:
        return

    # ---------------- SAME DESIGN EXISTS ----------------
    existing_style = frappe.db.get_value(
        "Item",
        {
            "custom_sup_design_no": doc.custom_sup_design_no,
            "name": ["!=", doc.name]
        },
        "custom_barcode_code",
        order_by="creation asc"
    )

    if existing_style:
        doc.custom_barcode_code = existing_style
        return

    # ---------------- NEW SUP DESIGN ----------------
    # item_code se STYLE nikalo
    # Example: COLDEPSIL001RED06 → COLDEPSIL001
    item_code = doc.item_code

    # colour + size remove
    colour_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code") or ""
    size_code = frappe.db.get_value("Size", doc.custom_size, "size_code") or ""

    style_code = item_code.replace(colour_code + size_code, "")

    doc.custom_barcode_code = style_code

# def update_barcode_on_sup_design_change(doc, method):
#     # sirf existing item
#     if doc.is_new():
#         return

#     if not doc.custom_sup_design_no:
#         return

#     # 🔎 DB se purani value lao
#     old_sup_design = frappe.db.get_value(
#         "Item",
#         doc.name,
#         "custom_sup_design_no"
#     )

#     # agar change hi nahi hua → exit
#     if old_sup_design == doc.custom_sup_design_no:
#         return

#     current_item_code = doc.name

#     # kisi aur item me same design hai?
#     existing_item_code = frappe.db.get_value(
#         "Item",
#         {
#             "custom_sup_design_no": doc.custom_sup_design_no,
#             "name": ["!=", doc.name]
#         },
#         "name",
#         order_by="creation asc"
#     )

#     if existing_item_code:
#         # same design → same barcode
#         doc.custom_barcode_code = existing_item_code
#     else:
#         # new design → current item ka code
#         doc.custom_barcode_code = current_item_code

def update_item_code_on_change(doc, method):

    if doc.is_new() or doc.custom_bypass_serialbatch:
        return

    tracked_fields = [
        "custom_group_collection",
        "custom_departments",
        "custom_silvet",
        "custom_colour_name",
        "custom_size"
    ]

    old = doc.get_doc_before_save()
    if not old:
        return

    if not any(old.get(f) != doc.get(f) for f in tracked_fields):
        return

    # ---------------- MASTER CODES ----------------
    collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
    department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
    silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")

    colour_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code")
    size_code = frappe.db.get_value("Size", doc.custom_size, "size_code")

    if not colour_code or not size_code:
        frappe.throw("Colour / Size Code missing")

    base_code = f"{collection_code}{department_code}{silvet_code}"

    old_base = old.item_code[:-len(colour_code + size_code)]
    base_item_code = old_base if old_base.startswith(base_code) else f"{base_code}{get_next_series(base_code)}"

    new_item_code = f"{base_item_code}{colour_code}{size_code}"

    if new_item_code == doc.name:
        return

    if frappe.db.exists("Item", new_item_code):
        frappe.throw(f"Item Code {new_item_code} already exists")

    old_item_code = doc.name

    # ---------------- RENAME ITEM ----------------
    frappe.rename_doc("Item", old_item_code, new_item_code, force=True)

    # 🔥 CRITICAL PART: recreate barcode
    barcode_value = new_item_code
    uom = doc.stock_uom or "Nos"

    # delete old barcode rows (if any ghost)
    frappe.db.delete("Item Barcode", {"parent": new_item_code})

    # create fresh barcode row
    frappe.get_doc({
        "doctype": "Item Barcode",
        "parent": new_item_code,
        "parenttype": "Item",
        "parentfield": "barcodes",
        "barcode": barcode_value,
        "barcode_type": "UPC-A",
        "uom": uom
    }).insert(ignore_permissions=True)

    doc.item_code = new_item_code
    doc.item_name = new_item_code


# def create_item_barcode(doc, method):

#     if not doc.is_stock_item:
#         return

#     # Already exists → skip
#     if frappe.db.exists("Item Barcode", {
#         "parent": doc.name,
#         "barcode": doc.item_code
#     }):
#         return

#     doc.append("barcodes", {
#         "barcode": doc.item_code,
#         "barcode_type": "UPC-A",
#         "uom": doc.stock_uom or "Nos"
#     })

#     doc.save(ignore_permissions=True)

def apply_tzu_setting(doc, method):

    if not doc.is_stock_item:
        return

    # ✅ BYPASS SERIAL/BATCH
    if doc.custom_bypass_serialbatch:
        doc.has_serial_no = 0
        doc.has_batch_no = 0
        doc.create_new_batch = 0
        doc.serial_no_series = ""
        doc.batch_number_series = ""
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

#for existing item price validation error
# def existing_item_price_update(doc, method):

#     for row in doc.custom_item_prices or []:
#         if not row.price_list or not row.rate:
#             continue

#         # Check existing Item Price
#         item_price = frappe.db.exists(
#             "Item Price",
#             {
#                 "item_code": doc.item_code,
#                 "price_list": row.price_list
#             }
#         )

#         if item_price:
#             ip = frappe.get_doc("Item Price", item_price)
#             ip.price_list_rate = row.rate
#             ip.save(ignore_permissions=True)
#         else:
#             frappe.get_doc({
#                 "doctype": "Item Price",
#                 "item_code": doc.item_code,
#                 "price_list": row.price_list,
#                 "price_list_rate": row.rate
#             }).insert(ignore_permissions=True)

#for existing item price no validation
import frappe

def existing_item_price_update(doc, method):

    for row in doc.custom_item_prices or []:

        if not row.price_list or not row.rate:
            continue

        item_price_name = frappe.db.get_value(
            "Item Price",
            {
                "item_code": doc.item_code,
                "price_list": row.price_list,
                "uom": doc.stock_uom
            },
            "name"
        )

        if item_price_name:
            frappe.db.set_value(
                "Item Price",
                item_price_name,
                "price_list_rate",
                row.rate
            )
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": doc.item_code,
                "price_list": row.price_list,
                "uom": doc.stock_uom,
                "price_list_rate": row.rate
            }).insert(ignore_permissions=True)

    # Very important
    frappe.clear_document_cache("Item Price")
    frappe.clear_cache()
