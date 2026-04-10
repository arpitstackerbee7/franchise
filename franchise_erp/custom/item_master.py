# import frappe
# import random
# import re
# from frappe import _

# # ------------------------------------------------------------------
# # MASTER DATA HELPERS
# # ------------------------------------------------------------------

# @frappe.whitelist()
# def get_next_item_no():
#     count = frappe.db.count("Item")
#     return count + 1

# def get_item_group_code(value, label):
#     if not value:
#         frappe.throw(f"{label} is empty")
#     code = frappe.db.get_value("Item Group", value, "custom_code")
#     return code if code else value

# def get_uoms_from_tzu(parentfield):
#     tzu = frappe.get_single("TZU Setting")
#     rows = frappe.db.get_all("UOM Detail",
#         filters={"parent": tzu.name, "parentfield": parentfield},
#         pluck="uom"
#     )
#     return [u.strip() for u in rows if u]

# # ------------------------------------------------------------------
# # ITEM PRICE LOGIC (MERGE & PROTECTION)
# # ------------------------------------------------------------------

# def validate_and_merge_prices(doc, method):
#     # 1. Skip for new items (nothing to protect yet)
#     if doc.is_new():
#         return

#     table_fieldname = "custom_item_prices"
#     child_doctype = "Item Price Row"

#     # 2. Get the "Ground Truth" directly from the Database
#     # We fetch only the fields we need to avoid internal key conflicts
#     db_rows = frappe.db.get_all(child_doctype,
#         filters={'parent': doc.name, 'parentfield': table_fieldname},
#         fields=['price_list', 'rate', 'item_code'],
#         order_by="idx asc"
#     )
    
#     # Map of saved rates for protection: { 'MRP': 100.0 }
#     db_rates = {d.price_list: d.rate for d in db_rows if d.price_list}

#     # 3. Process the rows currently in the form (from Upload or Manual Edit)
#     incoming_rows = doc.get(table_fieldname) or []
#     seen_pl = set()
#     cleaned_rows = []

#     for row in incoming_rows:
#         if not row.price_list:
#             continue

#         # --- CONDITION 1: ITEM CODE VALIDATION ---
#         # Only validate if an item_code was actually provided (prevents manual save issues)
#         if row.item_code and str(row.item_code).strip() != str(doc.name).strip():
#             # RESCUE: Restore original rows before throwing error to fix visual blanking
#             doc.set(table_fieldname, [])
#             for d in db_rows:
#                 doc.append(table_fieldname, {
#                     "price_list": d.price_list,
#                     "rate": d.rate,
#                     "item_code": d.item_code
#                 })
            
#             frappe.throw(
#                 _("Row {0}: Item Code <b>{1}</b> does not match <b>{2}</b>. Upload rejected and data restored.")
#                 .format(row.idx or "", row.item_code, doc.name),
#                 title=_("Item Code Mismatch")
#             )

#         # --- CONDITION 2: REMOVE DUPLICATES ---
#         if row.price_list in seen_pl:
#             continue
        
#         # --- CONDITION 3: OVERWRITE PROTECTION ---
#         # If Price List exists in DB, ignore the upload rate and keep the OLD rate.
#         if row.price_list in db_rates:
#             if row.rate != db_rates[row.price_list]:
#                 row.rate = db_rates[row.price_list]

#         # Sync item_code to parent
#         row.item_code = doc.name

#         cleaned_rows.append(row)
#         seen_pl.add(row.price_list)

#     # 4. Final step: Set the merged and cleaned list
#     doc.set(table_fieldname, cleaned_rows)

# # ------------------------------------------------------------------
# # CORE ITEM LOGIC (BARCODES, SERIES, TAXES)
# # ------------------------------------------------------------------

# def generate_item_code(doc, method):
#     if doc.custom_bypass_serialbatch or not doc.is_stock_item or not doc.is_new():
#         return

#     # Master Codes
#     collection_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
#     department_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
#     silvet_code = get_item_group_code(doc.custom_silvet, "SILVET")
#     colour_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code")
#     size_code = frappe.db.get_value("Size", doc.custom_size, "size_code")

#     if not all([colour_code, size_code]):
#         frappe.throw("Colour or Size code missing")

#     base_code = f"{collection_code}{department_code}{silvet_code}"
#     next_series = get_next_series(base_code)
#     base_item_code = f"{base_code}{next_series}"
    
#     while frappe.db.exists("Item", {"item_code": ["like", f"{base_item_code}%"]}):
#         next_series += 1
#         base_item_code = f"{base_code}{next_series}"

#     final_item_code = f"{base_item_code}{colour_code}{size_code}"
#     doc.item_code = final_item_code
#     doc.item_name = final_item_code

#     existing_style = frappe.db.get_value("Item", {"custom_sup_design_no": doc.custom_sup_design_no}, "custom_barcode_code")
#     doc.custom_barcode_code = existing_style or base_item_code

#     doc.set("barcodes", [])
#     doc.append("barcodes", {
#         "barcode": final_item_code,
#         "barcode_type": "UPC-A",
#         "uom": doc.stock_uom or "Nos"
#     })

# def apply_tzu_setting(doc, method):
#     if not doc.is_stock_item or not doc.is_new() or doc.custom_bypass_serialbatch:
#         return
    
#     if doc.item_group in ["All Item Groups-Raw Material", "All Item Groups-Non-Trading"]:
#         doc.has_serial_no = 0
#         doc.has_batch_no = 0
#         return

#     tzu = frappe.get_single("TZU Setting")
#     serial_uom_list = get_uoms_from_tzu("serial_no_uom")
#     batch_uom_list = get_uoms_from_tzu("batch_uom")
#     stock_uom = (doc.stock_uom or "").strip()

#     prefix = tzu.serialno_series or "T"
#     random_series = random.randint(100000, 999999)

#     if stock_uom in serial_uom_list:
#         doc.has_serial_no = 1
#         doc.serial_no_series = f"{prefix}{random_series}.#####"
#     elif stock_uom in batch_uom_list:
#         doc.has_batch_no = 1
#         doc.create_new_batch = 1
#         doc.batch_number_series = f"{prefix}{random_series}.#####"
#     else:
#         frappe.throw(f"UOM {stock_uom} not configured in TZU Setting.")

# def get_next_series(base_code):
#     last_item = frappe.db.sql("""
#         SELECT item_code FROM `tabItem` 
#         WHERE item_code LIKE %s 
#         ORDER BY CAST(SUBSTRING_INDEX(item_code, '-', -1) AS UNSIGNED) DESC LIMIT 1
#     """, (base_code + "-%",), as_dict=1)
#     return int(re.search(r'-(\d+)$', last_item[0].item_code).group(1)) + 1 if last_item else 1

# def existing_item_price_update(doc, method):
#     for row in doc.get("custom_item_prices") or []:
#         if not row.price_list or not row.rate: continue
        
#         name = frappe.db.get_value("Item Price", {"item_code": doc.item_code, "price_list": row.price_list, "uom": doc.stock_uom}, "name")
#         if name:
#             frappe.db.set_value("Item Price", name, "price_list_rate", row.rate)
#         else:
#             frappe.get_doc({"doctype": "Item Price", "item_code": doc.item_code, "price_list": row.price_list, "uom": doc.stock_uom, "price_list_rate": row.rate}).insert(ignore_permissions=True)
#     frappe.clear_cache()


# import frappe
# import random
# import re
# from frappe import _
# from frappe.utils.csvutils import read_csv_content_from_uploaded_file

# # ------------------------------------------------------------------
# # 1. THE SMART UPLOAD (Button Function)
# # ------------------------------------------------------------------
# @frappe.whitelist()
# def smart_bulk_upload(item_code, file_url):
#     # Read CSV
#     rows = read_csv_content_from_uploaded_file(file_url)
#     if not rows or len(rows) <= 1:
#         frappe.throw("CSV file is empty or missing headers.")

#     doc = frappe.get_doc("Item", item_code)
#     # Track existing lists to prevent duplicates during upload
#     existing_pl = {str(d.price_list).strip() for d in doc.get("custom_item_prices") or []}
    
#     # Flexible Header Search
#     headers = [str(h).strip().lower() for h in rows[0]]
#     try:
#         idx_code = headers.index("item code")
#         idx_list = headers.index("price list")
#         idx_rate = headers.index("rate")
#     except ValueError:
#         frappe.throw("CSV Headers must contain: 'Item Code', 'Price List', and 'Rate'")

#     added = 0
#     for row in rows[1:]:
#         if len(row) < 3: continue
#         f_code = str(row[idx_code]).strip()
#         f_list = str(row[idx_list]).strip()
#         f_rate = row[idx_rate]

#         # Stop if item code mismatch
#         if f_code != item_code:
#             frappe.throw(f"File contains Item Code {f_code}, but you are on {item_code}.")
        
#         # PROTECTION: Skip if already exists in table
#         if f_list in existing_pl:
#             continue 

#         doc.append("custom_item_prices", {
#             "price_list": f_list,
#             "rate": f_rate,
#             "item_code": item_code
#         })
#         existing_pl.add(f_list)
#         added += 1

#     if added > 0:
#         doc.save()
#         return f"Successfully added {added} new rows."
#     return "All data already exists in the table."

# # ------------------------------------------------------------------
# # 2. THE SAVE GUARD (Deduplication & Overwrite Protection)
# # ------------------------------------------------------------------
# def validate_and_merge_prices(doc, method):
#     if doc.is_new(): return

#     table_field = "custom_item_prices"
#     child_dt = "Item Price Row"

#     # Fetch "Master Copy" from DB to protect existing rates
#     db_rows = frappe.db.get_all(child_dt,
#         filters={'parent': doc.name, 'parentfield': table_field},
#         fields=['price_list', 'rate', 'item_code']
#     )
#     db_rates = {str(d.price_list).strip(): d.rate for d in db_rows if d.price_list}

#     seen_pl = set()
#     cleaned_rows = []

#     for row in doc.get(table_field) or []:
#         p_list = str(row.price_list or "").strip()
#         if not p_list: continue

#         # --- CONDITION 1: ITEM CODE VALIDATION ---
#         if row.item_code and str(row.item_code).strip() != str(doc.name).strip():
#             # RESCUE UI: Restore original rows before error
#             doc.set(table_field, db_rows)
#             frappe.throw(_("Item Code mismatch. Upload rejected and data restored."))

#         # --- CONDITION 2: DEDUPLICATION (Removes the 2nd WSP row) ---
#         if p_list in seen_pl:
#             continue
        
#         # --- CONDITION 3: OVERWRITE PROTECTION ---
#         if p_list in db_rates:
#             row.rate = db_rates[p_list]

#         row.item_code = doc.name
#         cleaned_rows.append(row)
#         seen_pl.add(p_list)

#     doc.set(table_field, cleaned_rows)

# # ------------------------------------------------------------------
# # 3. MASTER DATA HELPERS & CORE LOGIC
# # ------------------------------------------------------------------
# @frappe.whitelist()
# def get_next_item_no():
#     return frappe.db.count("Item") + 1

# def get_item_group_code(value, label):
#     if not value: frappe.throw(f"{label} is empty")
#     code = frappe.db.get_value("Item Group", value, "custom_code")
#     return code if code else value

# def get_uoms_from_tzu(parentfield):
#     tzu = frappe.get_single("TZU Setting")
#     rows = frappe.db.get_all("UOM Detail", filters={"parent": tzu.name, "parentfield": parentfield}, pluck="uom")
#     return [u.strip() for u in rows if u]

# def generate_item_code(doc, method):
#     if doc.custom_bypass_serialbatch or not doc.is_stock_item or not doc.is_new(): return
#     c_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
#     d_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
#     s_code = get_item_group_code(doc.custom_silvet, "SILVET")
#     cl_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code")
#     sz_code = frappe.db.get_value("Size", doc.custom_size, "size_code")
#     if not all([cl_code, sz_code]): frappe.throw("Colour or Size code missing")
    
#     base = f"{c_code}{d_code}{s_code}"
#     next_s = get_next_series(base)
#     item_c = f"{base}{next_s}{cl_code}{sz_code}"
#     doc.item_code = doc.item_name = item_c
#     doc.custom_barcode_code = base + str(next_s)
#     doc.set("barcodes", [])
#     doc.append("barcodes", {"barcode": item_c, "barcode_type": "UPC-A", "uom": doc.stock_uom or "Nos"})

# def apply_tzu_setting(doc, method):
#     if not doc.is_stock_item or not doc.is_new() or doc.custom_bypass_serialbatch: return
#     if doc.item_group in ["All Item Groups-Raw Material", "All Item Groups-Non-Trading"]:
#         doc.has_serial_no, doc.has_batch_no = 0, 0
#         return
#     tzu = frappe.get_single("TZU Setting")
#     stock_uom = (doc.stock_uom or "").strip()
#     if stock_uom in get_uoms_from_tzu("serial_no_uom"):
#         doc.has_serial_no = 1
#         doc.serial_no_series = f"{tzu.serialno_series or 'T'}{random.randint(100000, 999999)}.#####"
#     elif stock_uom in get_uoms_from_tzu("batch_uom"):
#         doc.has_batch_no, doc.create_new_batch = 1, 1
#         doc.batch_number_series = f"{tzu.serialno_series or 'T'}{random.randint(100000, 999999)}.#####"

# def get_next_series(base_code):
#     res = frappe.db.sql("SELECT item_code FROM `tabItem` WHERE item_code LIKE %s ORDER BY creation DESC LIMIT 1", (base_code + "%",), as_dict=1)
#     if res:
#         match = re.search(r'(\d+)', res[0].item_code.replace(base_code, ""))
#         if match: return int(match.group(1)) + 1
#     return 1

# def existing_item_price_update(doc, method):
#     for r in doc.get("custom_item_prices") or []:
#         if not r.price_list or not r.rate: continue
#         args = {"item_code": doc.item_code, "price_list": r.price_list, "uom": doc.stock_uom}
#         name = frappe.db.get_value("Item Price", args, "name")
#         if name: frappe.db.set_value("Item Price", name, "price_list_rate", r.rate)
#         else: frappe.get_doc({"doctype": "Item Price", **args, "price_list_rate": r.rate}).insert(ignore_permissions=True)
#     frappe.clear_cache()












import frappe
import random
import re
from frappe import _
from frappe.utils.file_manager import get_file_path


@frappe.whitelist()
def smart_bulk_upload(item_code, file_url):
    import csv, io, os
    from urllib.parse import unquote

    file_url = unquote(file_url)
    file_path = get_file_path(file_url)

    if not os.path.exists(file_path):
        frappe.throw(f"File not found at: {file_path}. Please re-upload.")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    reader = csv.reader(io.StringIO(content))
    all_rows = list(reader)

    # ── SMART HEADER DETECTION ──────────────────────────────────────
    # Find the row that contains all 3 required headers (case-insensitive)
    # This skips any junk/instruction rows at the top
    # ── SMART HEADER DETECTION ──────────────────────────────────────
    required = {"item code", "price list", "rate"}
    header_row_idx = None

    for idx, row in enumerate(all_rows):
        cleaned = {str(c).strip().lower() for c in row}
        if required.issubset(cleaned):
            header_row_idx = idx
            break

    if header_row_idx is not None:
        headers = [str(h).strip().lower() for h in all_rows[header_row_idx]]
        data_rows = all_rows[header_row_idx + 1:]
        idx_code = headers.index("item code")
        idx_list = headers.index("price list")
        idx_rate = headers.index("rate")
    else:
        data_rows = all_rows
        idx_code, idx_list, idx_rate = 0, 1, 2

    # ── REST OF LOGIC (unchanged) ───────────────────────────────────
    doc = frappe.get_doc("Item", item_code)

    existing_pl = {
        str(d.price_list).strip().upper()
        for d in (doc.get("custom_item_prices") or [])
        if d.price_list
    }

    added = 0
    skipped = 0
    errors = []

    for i, row in enumerate(data_rows, start=1):
        if len(row) < 3:
            continue

        f_code = str(row[idx_code]).strip()
        f_list = str(row[idx_list]).strip()
        f_rate_raw = str(row[idx_rate]).strip()

        # Skip junk/instruction/empty rows
        if not f_code and not f_list:
            continue
        junk_phrases = {
            "price list", "price_list", "------", "do not edit",
            "the csv format is case sensitive", "do not edit headers",
            "item code", "item_code"
        }
        if f_code.lower() in junk_phrases or f_list.lower() in junk_phrases:
            continue

        # Skip rows where item code looks like an instruction sentence (contains spaces AND is long)
        if " " in f_code and len(f_code) > 20:
            continue
        

        # PROTECTION 1: Item Code mismatch
        if f_code and f_code != item_code:
            frappe.throw(
                _(f"Row {i}: Item Code '{f_code}' does not match '{item_code}'. "
                  "Upload blocked.")
            )

        # Validate rate
        try:
            f_rate = float(f_rate_raw)
            if f_rate <= 0:
                raise ValueError("Rate must be greater than 0")
        except (ValueError, TypeError):
            errors.append(
                f"Row {i}: '{f_list}' has invalid or empty rate '{f_rate_raw}' — skipped."
            )
            skipped += 1
            continue

        # PROTECTION 2: Skip duplicates
        if f_list.upper() in existing_pl:
            skipped += 1
            continue

        doc.append("custom_item_prices", {
            "item_code": item_code,
            "price_list": f_list,
            "rate": f_rate,
        })
        existing_pl.add(f_list.upper())
        added += 1

    if added > 0:
        doc.save(ignore_permissions=True)

    parts = []
    if added:
        parts.append(f"✅ {added} new row(s) added.")
    if skipped:
        parts.append(f"⚠️ {skipped} row(s) skipped (already exist or invalid rate).")
    if errors:
        parts.append("⚠️ Errors: " + " | ".join(errors))

    return " ".join(parts) if parts else "No new rows were added."

# ------------------------------------------------------------------
# 2. THE SAVE GUARD (Deduplication + Overwrite Protection)
# ------------------------------------------------------------------
def validate_and_merge_prices(doc, method=None):
    """
    Runs on every Item save (validate hook).
    Rules enforced:
      A. Deduplication   — if two rows have the same Price List, keep only the first.
      B. Overwrite guard — if a Price List already exists in DB, restore its saved rate.
      C. Item Code fix   — always force item_code on each row to match the parent Item.
      D. Rescue logic    — if Item Code mismatch found, restore DB rows before throwing.
    New documents skip the DB-fetch (no saved rows yet) but still get deduplicated.
    """
    table_field = "custom_item_prices"
    child_dt = "Item Price Row"

    # Fetch saved rates from DB (empty dict for brand-new items)
    db_rates = {}
    db_rows_for_rescue = []

    if not doc.is_new():
        db_rows_for_rescue = frappe.db.get_all(
            child_dt,
            filters={"parent": doc.name, "parentfield": table_field},
            fields=["name", "price_list", "rate", "item_code"],
            order_by="idx asc",
        )
        db_rates = {
            str(r.price_list).strip().upper(): r.rate
            for r in db_rows_for_rescue
            if r.price_list
        }

    seen_pl = set()       # for deduplication within current rows
    cleaned_rows = []

    for row in doc.get(table_field) or []:
        p_list = str(row.price_list or "").strip()

        # Skip rows with no price list set
        if not p_list:
            continue

        p_list_key = p_list.upper()

        # ── CONDITION A: Item Code mismatch check ──────────────────
        # Only check if the row carries an item_code that contradicts the parent
        if row.item_code and str(row.item_code).strip() != str(doc.name).strip():
            # Rescue: restore DB rows so the table doesn't go blank
            if db_rows_for_rescue:
                doc.set(table_field, db_rows_for_rescue)
            frappe.throw(
                _(
                    f"Item Code mismatch on Price List '{p_list}': "
                    f"row has '{row.item_code}' but this item is '{doc.name}'. "
                    "Upload rejected and original data has been restored."
                )
            )

        # ── CONDITION B: Deduplication ─────────────────────────────
        # If we've already seen this price list in the current save, drop this row
        if p_list_key in seen_pl:
            continue

        # ── CONDITION C: Overwrite protection ─────────────────────
        # If this price list already existed in DB, keep the original rate
        if p_list_key in db_rates:
            row.rate = db_rates[p_list_key]

        # ── CONDITION D: Always fix item_code on the row ───────────
        row.item_code = doc.name

        cleaned_rows.append(row)
        seen_pl.add(p_list_key)

    doc.set(table_field, cleaned_rows)


# ------------------------------------------------------------------
# 3. SYNC TO ITEM PRICE DOCTYPE (on_update hook)
# ------------------------------------------------------------------
def existing_item_price_update(doc, method=None):
    """
    After Item is saved, keep the standard Item Price doctype in sync
    with whatever is in custom_item_prices table.
    - If an Item Price record exists → update the rate.
    - If it does not exist → create a new one.
    """
    for row in doc.get("custom_item_prices") or []:
        if not row.price_list or not row.rate:
            continue

        filters = {
            "item_code": doc.item_code or doc.name,
            "price_list": row.price_list,
            "uom": doc.stock_uom,
        }
        existing_name = frappe.db.get_value("Item Price", filters, "name")

        if existing_name:
            frappe.db.set_value("Item Price", existing_name, "price_list_rate", row.rate)
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                **filters,
                "price_list_rate": row.rate,
            }).insert(ignore_permissions=True)

    frappe.clear_cache()


# ------------------------------------------------------------------
# 4. MASTER DATA HELPERS & ITEM CODE GENERATION
# ------------------------------------------------------------------
@frappe.whitelist()
def get_next_item_no():
    return frappe.db.count("Item") + 1


def get_item_group_code(value, label):
    if not value:
        frappe.throw(_(f"{label} is empty"))
    code = frappe.db.get_value("Item Group", value, "custom_code")
    return code if code else value


def get_uoms_from_tzu(parentfield):
    tzu = frappe.get_single("TZU Setting")
    rows = frappe.db.get_all(
        "UOM Detail",
        filters={"parent": tzu.name, "parentfield": parentfield},
        pluck="uom",
    )
    return [u.strip() for u in rows if u]


def get_next_series(base_code):
    res = frappe.db.sql(
        "SELECT item_code FROM `tabItem` WHERE item_code LIKE %s ORDER BY creation DESC LIMIT 1",
        (base_code + "%",),
        as_dict=True,
    )
    if res:
        match = re.search(r"(\d+)", res[0].item_code.replace(base_code, ""))
        if match:
            return int(match.group(1)) + 1
    return 1


def generate_item_code(doc, method=None):
    """
    Runs on before_insert.
    Auto-generates item_code from collection/department/silvet/colour/size codes.
    Skipped for non-stock items or items with bypass flag set.
    """
    if doc.custom_bypass_serialbatch or not doc.is_stock_item or not doc.is_new():
        return

    c_code = get_item_group_code(doc.custom_group_collection, "COLLECTION")
    d_code = get_item_group_code(doc.custom_departments, "DEPARTMENT")
    s_code = get_item_group_code(doc.custom_silvet, "SILVET")

    cl_code = frappe.db.get_value("Color", doc.custom_colour_name, "custom_color_code")
    sz_code = frappe.db.get_value("Size", doc.custom_size, "size_code")

    if not cl_code or not sz_code:
        frappe.throw(_("Colour or Size code is missing. Cannot generate Item Code."))

    base = f"{c_code}{d_code}{s_code}"
    next_s = get_next_series(base)
    item_c = f"{base}{next_s}{cl_code}{sz_code}"

    doc.item_code = item_c
    doc.item_name = item_c
    doc.custom_barcode_code = base + str(next_s)

    doc.set("barcodes", [])
    doc.append("barcodes", {
        "barcode": item_c,
        "barcode_type": "UPC-A",
        "uom": doc.stock_uom or "Nos",
    })


def apply_tzu_setting(doc, method=None):
    """
    Runs on validate (for new items only).
    Sets serial/batch number configuration based on TZU Setting rules.
    """
    if not doc.is_stock_item or not doc.is_new() or doc.custom_bypass_serialbatch:
        return

    if doc.item_group in ["All Item Groups-Raw Material", "All Item Groups-Non-Trading"]:
        doc.has_serial_no = 0
        doc.has_batch_no = 0
        return

    tzu = frappe.get_single("TZU Setting")
    stock_uom = (doc.stock_uom or "").strip()

    if stock_uom in get_uoms_from_tzu("serial_no_uom"):
        doc.has_serial_no = 1
        doc.serial_no_series = (
            f"{tzu.serialno_series or 'T'}{random.randint(100000, 999999)}.#####"
        )
    elif stock_uom in get_uoms_from_tzu("batch_uom"):
        doc.has_batch_no = 1
        doc.create_new_batch = 1
        doc.batch_number_series = (
            f"{tzu.serialno_series or 'T'}{random.randint(100000, 999999)}.#####"
        )