


import frappe
from frappe.utils import flt


# ------------------------------------------------
# ROUNDING (Sirf WSP ke liye use hoga)
# ------------------------------------------------
def round_to_nearest_9(rate):
    rate = int(round(rate))
    last = rate % 10

    if last == 9:
        return rate
    if last <= 5:
        return rate - last - 1
    return rate + (9 - last)


# ------------------------------------------------
# TAX CALCULATION
# ------------------------------------------------
def get_item_tax_amount(row):
    return (
        (row.igst_amount or 0) +
        (row.cgst_amount or 0) +
        (row.sgst_amount or 0) +
        (row.cess_amount or 0) +
        (row.cess_non_advol_amount or 0)
    )


# ------------------------------------------------
# COST CALCULATION
# ------------------------------------------------
# def calculate_cost(row, cost_type, tax_mode):
#     """
#     cost_type : Basic Cost / Effective Cost
#     tax_mode  : Inclusive / Exclusive

#     Effective Cost:
#         Net Rate + Tax
#     Basic Cost:
#         Basic Purchase Rate
#     """

#     item_tax = get_item_tax_amount(row)

#     # Effective Cost
#     if cost_type == "Effective Cost":
#         base_cost = flt(row.net_rate)
#         if tax_mode == "Exclusive":
#             return base_cost + item_tax
#         return base_cost

#     # Basic Cost
#     base_cost = flt(row.price_list_rate)
#     if tax_mode == "Exclusive":
#         return base_cost + item_tax
#     return base_cost

# def calculate_cost(row, cost_type, tax_mode):
#     """
#     cost_type : Basic Cost / Effective Cost
#     tax_mode  : Inclusive / Exclusive

#     Exclusive → Tax INCLUDED
#     Inclusive   → Tax EXCLUDED
#     """

#     # ---- Per Unit Tax (SAFE) ----
#     total_tax = flt(row.item_tax_amount or 0)
#     qty = flt(row.qty or 1)
#     per_unit_tax = total_tax / qty if qty else 0

#     # ---------------- Effective Cost ----------------
#     if cost_type == "Effective Cost":
#         # net_rate is ALWAYS tax exclusive
#         base_cost = flt(row.net_rate or 0)

#         if tax_mode == "Exclusive":
#             # include tax
#             return base_cost + per_unit_tax

#         # Inclusive
#         return base_cost

#     # ---------------- Basic Cost ----------------
#     # price_list_rate / basic_rate is also tax exclusive
#     base_cost = flt(row.price_list_rate or 0)

#     if tax_mode == "Exclusive":
#         return base_cost + per_unit_tax

#     # Inclusive
#     return base_cost
from frappe.utils import flt

def calculate_cost(row, cost_type, tax_mode):
    """
    cost_type : Basic Cost / Effective Cost
    tax_mode  : Inclusive / Exclusive

    Exclusive → ADD tax
    Inclusive → DO NOT add tax
    """

    # ---- Per Unit Tax (SAFE) ----
    total_tax = flt(row.item_tax_amount or 0)
    qty = flt(row.qty or 1)
    per_unit_tax = total_tax / qty if qty else 0

    # ---------------- Effective Cost ----------------
    if cost_type == "Effective Cost":
        # net_rate is ALWAYS tax exclusive
        base_cost = flt(row.net_rate or 0)

        if tax_mode == "Exclusive":
            return base_cost + per_unit_tax

        return base_cost  # Inclusive

    # ---------------- Basic Cost ----------------
    # price_list_rate / basic_rate is ALSO tax exclusive
    base_cost = flt(row.price_list_rate or 0)

    if tax_mode == "Exclusive":
        return base_cost + per_unit_tax

    return base_cost  # Inclusive

# ------------------------------------------------
# CREATE ITEM PRICE (Generic)
# ------------------------------------------------
def create_item_price(
    item_code,
    price_list,
    cost,
    margin_type,
    margin_value,
    valid_from,
    apply_rounding=False
):
    """
    - Item Price ek baar banega (overwrite nahi hoga)
    - apply_rounding=True  → WSP
    - apply_rounding=False → MRP / RSP
    """

    if frappe.db.exists("Item Price", {
        "item_code": item_code,
        "price_list": price_list
    }):
        return

    # Margin calculation
    if margin_type == "Percentage":
        margin_amount = cost * margin_value / 100
    else:
        margin_amount = margin_value

    final_price = flt(cost + margin_amount)

    # Sirf WSP me rounding
    if apply_rounding:
        final_price = round_to_nearest_9(final_price)

    doc = frappe.get_doc({
        "doctype": "Item Price",
        "item_code": item_code,
        "price_list": price_list,
        "price_list_rate": round(final_price, 2),
        "valid_from": valid_from,
        "selling": 1
    })
    doc.insert(ignore_permissions=True)


# ------------------------------------------------
# MAIN FUNCTION (PO SUBMIT HOOK)
# ------------------------------------------------
# def create_selling_price_from_po(doc, method):
#     """
#     MRP / RSP aur WSP dono ke liye alag-alag config chalegi.

#     MRP / RSP:
#         - Apni cost base
#         - Apna tax mode
#         - Apna margin
#         - Exact value (jaise 109.72)

#     WSP:
#         - Alag cost base
#         - Alag tax mode
#         - Alag margin
#         - Rounding to nearest 9
#     """

#     pricing_rule = frappe.db.get_value(
#         "Pricing Rule",
#         {"disable": 0},
#         [
#             # ---------- MRP / RSP ----------
#             "custom_cost_will_be_taken_as",
#             "custom_consider_tax_in_margin",
#             "custom_mrp_will_be_taken_as",
#             "custom_margin_typee",
#             "custom_minimum_margin",

#             # ---------- WSP (double underscore fields) ----------
#             "custom_cost__will_be_taken_as",
#             "custom_consider__tax_in_margin",
#             "custom_wsp_margin_type",
#             "custom_wsp_minimum_margin"
#         ],
#         as_dict=True
#     )

#     if not pricing_rule:
#         frappe.throw("No active Pricing Rule found")

#     # ---------------- MRP / RSP CONFIG ----------------
#     mrp_cost_type = pricing_rule.custom_cost_will_be_taken_as or "Effective Cost"
#     mrp_tax_mode = pricing_rule.custom_consider_tax_in_margin or "Exclusive"
#     selling_price_list = pricing_rule.custom_mrp_will_be_taken_as or "MRP"
#     mrp_margin_type = pricing_rule.custom_margin_typee or "Percentage"
#     mrp_margin_value = flt(pricing_rule.custom_minimum_margin or 0)

#     # ---------------- WSP CONFIG (Double underscore) ----------------
#     wsp_cost_type = pricing_rule.custom_cost__will_be_taken_as or "Effective Cost"
#     wsp_tax_mode = pricing_rule.custom_consider__tax_in_margin or "Inclusive"
#     wsp_margin_type = pricing_rule.custom_wsp_margin_type or "Percentage"
#     wsp_margin_value = flt(pricing_rule.custom_wsp_minimum_margin or 0)

#     # ---------------- PROCESS ITEMS ----------------
#     for row in doc.items:
#         if not row.item_code:
#             continue

#         # ===== MRP / RSP PRICE =====
#         cost_mrp = calculate_cost(row, mrp_cost_type, mrp_tax_mode)

#         create_item_price(
#             item_code=row.item_code,
#             price_list=selling_price_list,   # MRP or RSP
#             cost=cost_mrp,
#             margin_type=mrp_margin_type,
#             margin_value=mrp_margin_value,
#             valid_from=doc.transaction_date,
#             apply_rounding=False              # MRP/RSP exact price
#         )

#         # ===== WSP PRICE =====
#         cost_wsp = calculate_cost(row, wsp_cost_type, wsp_tax_mode)

#         create_item_price(
#             item_code=row.item_code,
#             price_list="WSP",
#             cost=cost_wsp,
#             margin_type=wsp_margin_type,
#             margin_value=wsp_margin_value,
#             valid_from=doc.transaction_date,
#             apply_rounding=False               # WSP rounding to 9
#         )



#     frappe.db.commit()
#     return "success"




import frappe
from frappe.utils import flt, cint


def create_selling_price_from_po(doc, method):

    pricing_rule = frappe.db.get_value(
        "Pricing Rule",
        {"disable": 0},
        [
            # -------- COMMON --------
            "supplier",

            # -------- MRP --------
            "custom_cost_will_be_taken_as",
            "custom_consider_tax_in_margin",
            "custom_margin_typee",
            "custom_minimum_margin",

            # -------- RSP --------
            "custom_cost___will_be_taken_as",
            "custom_consider___tax_in_margin",
            "custom_rsp_margin_type",
            "custom_rsp_minimum_margin",

            # -------- WSP --------
            "custom_cost__will_be_taken_as",
            "custom_consider__tax_in_margin",
            "custom_wsp_margin_type",
            "custom_wsp_minimum_margin",
        ],
        as_dict=True
    )

    # ------------------------------------------------
    # 1️⃣ NO PRICING RULE → ERP DEFAULT
    # ------------------------------------------------
    if not pricing_rule:
        return  # 👈 silently exit, no error

    # ------------------------------------------------
    # 2️⃣ SUPPLIER CHECK
    # ------------------------------------------------
    if pricing_rule.supplier:
        if doc.supplier != pricing_rule.supplier:
            return  # 👈 supplier mismatch → ERP default

    # ---------------- MRP CONFIG ----------------
    mrp_cost_type   = pricing_rule.custom_cost_will_be_taken_as or "Effective Cost"
    mrp_tax_mode    = pricing_rule.custom_consider_tax_in_margin or "Exclusive"
    mrp_margin_type = pricing_rule.custom_margin_typee or "Percentage"
    mrp_margin_val  = flt(pricing_rule.custom_minimum_margin or 0)

    # ---------------- RSP CONFIG ----------------
    rsp_cost_type   = pricing_rule.custom_cost___will_be_taken_as or "Effective Cost"
    rsp_tax_mode    = pricing_rule.custom_consider___tax_in_margin or "Exclusive"
    rsp_margin_type = pricing_rule.custom_rsp_margin_type or "Percentage"
    rsp_margin_val  = flt(pricing_rule.custom_rsp_minimum_margin or 0)

    # ---------------- WSP CONFIG ----------------
    wsp_cost_type   = pricing_rule.custom_cost__will_be_taken_as or "Effective Cost"
    wsp_tax_mode    = pricing_rule.custom_consider__tax_in_margin or "Exclusive"
    wsp_margin_type = pricing_rule.custom_wsp_margin_type or "Percentage"
    wsp_margin_val  = flt(pricing_rule.custom_wsp_minimum_margin or 0)

    # ---------------- PROCESS ITEMS ----------------
    for row in doc.items:
        if not row.item_code:
            continue

        # ===== MRP =====
        mrp_cost = calculate_cost(row, mrp_cost_type, mrp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list="MRP",
            cost=mrp_cost,
            margin_type=mrp_margin_type,
            margin_value=mrp_margin_val,
            valid_from=doc.transaction_date,
            apply_rounding=False
        )

        # ===== RSP =====
        rsp_cost = calculate_cost(row, rsp_cost_type, rsp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list="RSP",
            cost=rsp_cost,
            margin_type=rsp_margin_type,
            margin_value=rsp_margin_val,
            valid_from=doc.transaction_date,
            apply_rounding=False
        )

        # ===== WSP =====
        wsp_cost = calculate_cost(row, wsp_cost_type, wsp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list="WSP",
            cost=wsp_cost,
            margin_type=wsp_margin_type,
            margin_value=wsp_margin_val,
            valid_from=doc.transaction_date,
            apply_rounding=False
        )

    frappe.db.commit()










import frappe
import io
import base64
import barcode
from barcode.writer import ImageWriter
import frappe

@frappe.whitelist()
def generate_custom_barcode(data):
    writer = ImageWriter()
    writer.set_options({
        "module_width": 0.6,     
        "module_height": 30,      
        "font_size": 14,         
        "text_distance": 5,
        "quiet_zone": 10,     
        "dpi": 800,          
        "write_text": True,
        "anti_alias": False 
    })

    code128 = barcode.get_barcode_class("code128")
    code = code128(data, writer=writer)

    buffer = io.BytesIO()
    code.write(buffer, {"format": "PNG"})

    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return "data:image/png;base64," + img_str






import frappe
from frappe import _
from datetime import date

@frappe.whitelist()
def get_item_price(item_code, price_list):
    price = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": price_list
        },
        fields=["price_list_rate", "valid_from", "valid_upto"],
        order_by="valid_from desc",
        limit=1
    )

    if price:
        return {
            "rate": price[0]["price_list_rate"],
            "valid_from": price[0]["valid_from"],
            "valid_upto": price[0]["valid_upto"]
        }

    return None







# import frappe
# from frappe.utils.background_jobs import enqueue

# def fix_gstin(doc, method=None):

#     if not doc.gstin:
#         return

#     gst = doc.gstin
#     company = doc.name

#     # run AFTER all gst validations complete
#     enqueue(
#         _update_gstin,
#         queue="short",
#         company=company,
#         gst=gst,
#         delay=2
#     )


# def _update_gstin(company, gst):

#     frappe.db.set_value(
#         "Company",
#         company,
#         "gstin",
#         gst,
#         update_modified=False
#     )

#     frappe.db.commit()








#     # custom_app/api.py

# import frappe

# @frappe.whitelist()
# def scan_barcode_custom(barcode):
    
#     item = frappe.db.sql("""
#         SELECT parent
#         FROM `tabItem Barcode`
#         WHERE barcode = %s
#         LIMIT 1
#     """, (barcode,), as_dict=1)

#     if not item:
#         return None

#     item_code = item[0].parent

#     # get available serial
#     serial = frappe.db.sql("""
#         SELECT name
#         FROM `tabSerial No`
#         WHERE item_code = %s
#         AND status = 'Active'
#         LIMIT 1
#     """, (item_code,), as_dict=1)

#     return {
#         "item_code": item_code,
#         "serial_no": serial[0].name if serial else None
#     }





# import frappe
# import pandas as pd


# @frappe.whitelist()
# def upload_serial_excel(file_url, supplier):

#     file_doc = frappe.get_doc("File", {"file_url": file_url})
#     file_path = file_doc.get_full_path()

#     df = pd.read_excel(file_path)

#     serial_list = (
#         df.iloc[:, 0]
#         .dropna()
#         .astype(str)
#         .str.strip()
#         .tolist()
#     )

#     final_items = []
#     errors = []

#     for serial in serial_list:

#         found = False

#         # -------------------------
#         # STEP 1 → check Unused Serials table
#         # -------------------------
#         unused = frappe.db.get_value(
#             "Unused Serials",
#             {"serial_no": serial},
#             ["serial_no", "item_code", "purchase_order"],
#             as_dict=1
#         )

#         if unused:

#             po_doc = frappe.get_doc("Purchase Order", unused.purchase_order)

#             if po_doc.supplier != supplier:
#                 errors.append(f"{serial} supplier mismatch")
#                 continue

#             for po_item in po_doc.items:

#                 if po_item.item_code == unused.item_code:

#                     pending = po_item.qty - po_item.received_qty

#                     if pending <= 0:
#                         errors.append(f"{serial} exceeds qty for {po_item.item_code}")
#                         break

#                     final_items.append({
#                         "item_code": po_item.item_code,
#                         "item_name": po_item.item_name,
#                         "description": po_item.description,

#                         "qty": 1,
#                         "received_qty": 1,

#                         "uom": po_item.uom,
#                         "stock_uom": po_item.uom,
#                         "conversion_factor": 1,

#                         "rate": po_item.rate,
#                         "base_rate": po_item.rate,
#                         "amount": po_item.rate,
#                         "base_amount": po_item.rate,

#                         "purchase_order": po_doc.name,
#                         "purchase_order_item": po_item.name,

#                         "serial_no": serial,

#                         "warehouse": po_item.warehouse,

#                         "use_serial_batch_fields": 1
#                     })

#                     found = True
#                     break


#         # -------------------------
#         # STEP 2 → if not found → check Generated Serials in PO
#         # -------------------------
#         if not found:

#             po_list = frappe.get_all(
#                 "Purchase Order",
#                 filters={"supplier": supplier, "docstatus": 1},
#                 pluck="name"
#             )

#             for po_name in po_list:

#                 po_doc = frappe.get_doc("Purchase Order", po_name)

#                 for po_item in po_doc.items:

#                     if not po_item.custom_generated_serials:
#                         continue

#                     generated_serials = [
#                         s.strip()
#                         for s in po_item.custom_generated_serials.split("\n")
#                         if s.strip()
#                     ]

#                     if serial in generated_serials:

#                         pending = po_item.qty - po_item.received_qty

#                         if pending <= 0:
#                             errors.append(
#                                 f"{serial} exceeds qty for {po_item.item_code}"
#                             )
#                             found = True
#                             break

#                         final_items.append({
#                             "item_code": po_item.item_code,
#                             "item_name": po_item.item_name,
#                             "description": po_item.description,

#                             "qty": 1,
#                             "received_qty": 1,

#                             "uom": po_item.uom,
#                             "stock_uom": po_item.uom,
#                             "conversion_factor": 1,

#                             "rate": po_item.rate,
#                             "base_rate": po_item.rate,
#                             "amount": po_item.rate,
#                             "base_amount": po_item.rate,

#                             "purchase_order": po_doc.name,
#                             "purchase_order_item": po_item.name,

#                             "serial_no": serial,

#                             "warehouse": po_item.warehouse,

#                             "use_serial_batch_fields": 1
#                         })

#                         found = True
#                         break

#                 if found:
#                     break


#         # -------------------------
#         # not found anywhere
#         # -------------------------
#         if not found:
#             errors.append(f"{serial} not found")


#     return {
#         "items": final_items,
#         "errors": errors
#     }



# import frappe
# import pandas as pd


# @frappe.whitelist()
# def upload_serial_excel(file_url, supplier):

#     file_doc = frappe.get_doc("File", {"file_url": file_url})
#     file_path = file_doc.get_full_path()

#     df = pd.read_excel(file_path)

#     serial_list = (
#         df.iloc[:, 0]
#         .dropna()
#         .astype(str)
#         .str.strip()
#         .tolist()
#     )


#     po_list = frappe.get_all(
#         "Purchase Order",
#         filters={"supplier": supplier, "docstatus": 1},
#         pluck="name"
#     )

#     po_docs = {po: frappe.get_doc("Purchase Order", po) for po in po_list}


#     # incoming logistic map
#     incoming_map = {}

#     for po in po_list:

#         il = frappe.db.get_value(
#             "Incoming Logistic",
#             {"purchase_order": po},
#             ["name", "gate_entry_no"],
#             as_dict=1
#         )

#         if il:
#             incoming_map[po] = il


#     final_items = []
#     errors = []


#     for serial in serial_list:

#         found = False


#         for po in po_docs.values():

#             for item in po.items:


#                 # -----------------------
#                 # unused serial check
#                 # -----------------------
#                 if item.custom_unused_serials:

#                     unused_list = [
#                         s.strip()
#                         for s in item.custom_unused_serials.split("\n")
#                         if s.strip()
#                     ]

#                     if serial in unused_list:

#                         pending = item.qty - item.received_qty

#                         if pending <= 0:

#                             errors.append(
#                                 f"{serial} over qty {item.item_code}"
#                             )

#                             found = True
#                             break


#                         il = incoming_map.get(po.name)


#                         final_items.append({

#                             "item_code": item.item_code,

#                             "qty": 1,

#                             "uom": item.uom,

#                             "stock_uom": item.uom,

#                             "rate": item.rate,

#                             "purchase_order": po.name,

#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic":
#                                 il.name if il else None,

#                             "custom_bulk_gate_entry":
#                                 il.gate_entry_no if il else None,

#                             "use_serial_batch_fields": 1
#                         })


#                         # move serial unused -> used

#                         unused_list.remove(serial)

#                         used_list = []

#                         if item.custom_used_serials:

#                             used_list = [
#                                 s.strip()
#                                 for s in item.custom_used_serials.split("\n")
#                                 if s.strip()
#                             ]


#                         used_list.append(serial)


#                         item.custom_unused_serials = "\n".join(unused_list)

#                         item.custom_used_serials = "\n".join(used_list)


#                         found = True

#                         break



#                 # -----------------------
#                 # generated serial check
#                 # -----------------------
#                 if item.custom_generated_serials:

#                     gen_list = [
#                         s.strip()
#                         for s in item.custom_generated_serials.split("\n")
#                         if s.strip()
#                     ]


#                     if serial in gen_list:

#                         pending = item.qty - item.received_qty

#                         if pending <= 0:

#                             errors.append(
#                                 f"{serial} over qty {item.item_code}"
#                             )

#                             found = True
#                             break


#                         il = incoming_map.get(po.name)


#                         final_items.append({

#                             "item_code": item.item_code,

#                             "qty": 1,

#                             "uom": item.uom,

#                             "stock_uom": item.uom,

#                             "rate": item.rate,

#                             "purchase_order": po.name,

#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic":
#                                 il.name if il else None,

#                             "custom_bulk_gate_entry":
#                                 il.gate_entry_no if il else None,

#                             "use_serial_batch_fields": 1
#                         })


#                         found = True

#                         break


#             if found:

#                 po.save(ignore_permissions=True)

#                 break


#         if not found:

#             errors.append(f"{serial} not found")



#     return {

#         "items": final_items,

#         "errors": errors

#     }






# import frappe
# import pandas as pd


# @frappe.whitelist()
# def upload_serial_excel(file_url, supplier):

#     # read excel
#     file_doc = frappe.get_doc("File", {"file_url": file_url})
#     file_path = file_doc.get_full_path()

#     df = pd.read_excel(file_path)

#     serial_list = (
#         df.iloc[:, 0]
#         .dropna()
#         .astype(str)
#         .str.strip()
#         .tolist()
#     )

#     if not serial_list:
#         return {
#             "items": [],
#             "errors": ["Excel file empty"]
#         }


#     # -----------------------------
#     # get Purchase Orders
#     # -----------------------------
#     po_list = frappe.get_all(
#         "Purchase Order",
#         filters={
#             "supplier": supplier,
#             "docstatus": 1
#         },
#         pluck="name"
#     )

#     po_docs = {
#         po: frappe.get_doc("Purchase Order", po)
#         for po in po_list
#     }


#     # -----------------------------
#     # incoming logistic map
#     # -----------------------------
#     incoming_map = {}

#     for po in po_list:

#         il = frappe.db.get_value(
#             "Incoming Logistic",
#             {"purchase_order": po},
#             ["name", "gate_entry_no"],
#             as_dict=1
#         )

#         if il:
#             incoming_map[po] = il


#     # -----------------------------
#     # process serials
#     # -----------------------------
#     final_items = []
#     errors = []

#     for serial in serial_list:

#         found = False


#         for po in po_docs.values():

#             for item in po.items:


#                 # ==================================================
#                 # 1. UNUSED SERIAL
#                 # ==================================================
#                 if item.custom_unused_serials:

#                     unused_list = [
#                         s.strip()
#                         for s in item.custom_unused_serials.split("\n")
#                         if s.strip()
#                     ]

#                     if serial in unused_list:

#                         pending_qty = item.qty - item.received_qty

#                         if pending_qty <= 0:

#                             errors.append(
#                                 f"{serial} over qty for {item.item_code}"
#                             )

#                             found = True
#                             break


#                         il = incoming_map.get(po.name)


#                         final_items.append({

#                             "item_code": item.item_code,
#                             "item_name": item.item_name,
#                             "description": item.description,

#                             "qty": 1,
#                             "received_qty": 1,

#                             "uom": item.uom,
#                             "stock_uom": item.uom,

#                             "conversion_factor": 1,

#                             "rate": item.rate,
#                             "base_rate": item.rate,

#                             "purchase_order": po.name,
#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic":
#                                 il.name if il else None,

#                             "custom_bulk_gate_entry":
#                                 il.gate_entry_no if il else None,

#                             "use_serial_batch_fields": 1
#                         })


#                         # move serial unused -> used
#                         unused_list.remove(serial)

#                         used_list = []

#                         if item.custom_used_serials:

#                             used_list = [
#                                 s.strip()
#                                 for s in item.custom_used_serials.split("\n")
#                                 if s.strip()
#                             ]


#                         used_list.append(serial)


#                         item.custom_unused_serials = "\n".join(unused_list)

#                         item.custom_used_serials = "\n".join(used_list)


#                         found = True
#                         break



#                 # ==================================================
#                 # 2. GENERATED SERIAL
#                 # ==================================================
#                 if item.custom_generated_serials:

#                     generated_list = [
#                         s.strip()
#                         for s in item.custom_generated_serials.split("\n")
#                         if s.strip()
#                     ]


#                     if serial in generated_list:

#                         pending_qty = item.qty - item.received_qty

#                         if pending_qty <= 0:

#                             errors.append(
#                                 f"{serial} over qty for {item.item_code}"
#                             )

#                             found = True
#                             break


#                         il = incoming_map.get(po.name)


#                         final_items.append({

#                             "item_code": item.item_code,
#                             "item_name": item.item_name,
#                             "description": item.description,

#                             "qty": 1,
#                             "received_qty": 1,

#                             "uom": item.uom,
#                             "stock_uom": item.uom,

#                             "conversion_factor": 1,

#                             "rate": item.rate,
#                             "base_rate": item.rate,

#                             "purchase_order": po.name,
#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic":
#                                 il.name if il else None,

#                             "custom_bulk_gate_entry":
#                                 il.gate_entry_no if il else None,

#                             "use_serial_batch_fields": 1
#                         })


#                         found = True
#                         break



#             # save PO if serial moved unused -> used
#             if found:

#                 po.save(ignore_permissions=True)

#                 break


#         if not found:

#             errors.append(f"{serial} not found")


#     # -----------------------------
#     # return data to JS
#     # -----------------------------
#     return {

#         "items": final_items,

#         "errors": errors

#     }



# import frappe
# import pandas as pd


# @frappe.whitelist()
# def upload_serial_excel(file_url, supplier):

#     frappe.errprint("========== START SERIAL UPLOAD ==========")

#     # ------------------------------------------------
#     # READ EXCEL
#     # ------------------------------------------------

#     file_doc = frappe.get_doc("File", {"file_url": file_url})
#     file_path = file_doc.get_full_path()

#     df = pd.read_excel(file_path)

#     serial_list = (
#         df.iloc[:, 0]
#         .dropna()
#         .astype(str)
#         .str.strip()
#         .tolist()
#     )

#     serial_list = list(dict.fromkeys(serial_list))

#     frappe.errprint({
#         "TOTAL SERIAL FROM EXCEL": len(serial_list),
#         "SERIAL SAMPLE": serial_list[:10]
#     })

#     if not serial_list:

#         return {
#             "items": [],
#             "errors": ["Excel file empty"],
#             "gate_entry_list": []
#         }

#     # ------------------------------------------------
#     # GET PURCHASE ORDERS
#     # ------------------------------------------------

#     po_list = frappe.get_all(
#         "Purchase Order",
#         filters={
#             "supplier": supplier,
#             "docstatus": 1
#         },
#         pluck="name"
#     )

#     frappe.errprint({
#         "SUPPLIER": supplier,
#         "PO FOUND": po_list
#     })

#     po_docs = {
#         po: frappe.get_doc("Purchase Order", po)
#         for po in po_list
#     }

#     # ------------------------------------------------
#     # PROCESS SERIALS
#     # ------------------------------------------------

#     final_items = []
#     errors = []
#     gate_entries = set()

#     for serial in serial_list:

#         found = False

#         frappe.errprint(" ")
#         frappe.errprint("---- CHECK SERIAL ----")
#         frappe.errprint(serial)

#         for po in po_docs.values():

#             frappe.errprint({
#                 "CHECK PO": po.name
#             })

#             for item in po.items:

#                 frappe.errprint({
#                     "ITEM": item.item_code,
#                     "PO ITEM ROW": item.name,
#                     "IL LINK": item.custom_incoming_logistic
#                 })

#                 pending_qty = item.qty - item.received_qty

#                 # ------------------------------------------------
#                 # FETCH INCOMING LOGISTIC FROM PO ITEM
#                 # ------------------------------------------------

#                 il_name = item.custom_incoming_logistic

#                 il_doc = None
#                 gate_no = None

#                 if il_name:

#                     il_doc = frappe.db.get_value(

#                         "Incoming Logistic",

#                         il_name,

#                         ["name", "gate_entry_no"],

#                         as_dict=1

#                     )

#                     frappe.errprint({
#                         "IL DOC": il_doc
#                     })

#                     if il_doc:

#                         gate_no = il_doc.get("gate_entry_no")

#                         frappe.errprint({
#                             "GATE ENTRY FOUND": gate_no
#                         })

#                 else:

#                     frappe.errprint({
#                         "IL STATUS": "NOT LINKED"
#                     })


#                 # =====================================================
#                 # 1️⃣ UNUSED SERIAL
#                 # =====================================================

#                 if item.custom_unused_serials:

#                     unused_list = [

#                         x.strip()

#                         for x in item.custom_unused_serials.split("\n")

#                         if x.strip()

#                     ]

#                     if serial in unused_list:

#                         frappe.errprint({
#                             "MATCH TYPE": "UNUSED",
#                             "SERIAL": serial,
#                             "ITEM": item.item_code,
#                             "PENDING": pending_qty
#                         })

#                         if pending_qty <= 0:

#                             errors.append(
#                                 f"{serial} over qty for {item.item_code}"
#                             )

#                             found = True
#                             break


#                         final_items.append({

#                             "item_code": item.item_code,

#                             "item_name": item.item_name,

#                             "description": item.description,

#                             "qty": 1,

#                             "received_qty": 1,

#                             "uom": item.uom,

#                             "stock_uom": item.uom,

#                             "conversion_factor": 1,

#                             "rate": item.rate,

#                             "base_rate": item.rate,

#                             "purchase_order": po.name,

#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic": il_name,

#                             "custom_bulk_gate_entry": gate_no,

#                             "use_serial_batch_fields": 1

#                         })

#                         # move serial unused → used

#                         unused_list.remove(serial)

#                         used_list = []

#                         if item.custom_used_serials:

#                             used_list = [

#                                 x.strip()

#                                 for x in item.custom_used_serials.split("\n")

#                                 if x.strip()

#                             ]

#                         used_list.append(serial)

#                         item.custom_unused_serials = "\n".join(unused_list)

#                         item.custom_used_serials = "\n".join(used_list)

#                         if gate_no:
#                             gate_entries.add(gate_no)

#                         frappe.errprint({
#                             "SERIAL MOVED UNUSED → USED": serial
#                         })

#                         found = True
#                         break


#                 # =====================================================
#                 # 2️⃣ GENERATED SERIAL
#                 # =====================================================

#                 if item.custom_generated_serials:

#                     gen_list = [

#                         x.strip()

#                         for x in item.custom_generated_serials.split("\n")

#                         if x.strip()

#                     ]

#                     if serial in gen_list:

#                         frappe.errprint({
#                             "MATCH TYPE": "GENERATED",
#                             "SERIAL": serial,
#                             "ITEM": item.item_code,
#                             "PENDING": pending_qty
#                         })

#                         if pending_qty <= 0:

#                             errors.append(
#                                 f"{serial} over qty for {item.item_code}"
#                             )

#                             found = True
#                             break


#                         final_items.append({

#                             "item_code": item.item_code,

#                             "item_name": item.item_name,

#                             "description": item.description,

#                             "qty": 1,

#                             "received_qty": 1,

#                             "uom": item.uom,

#                             "stock_uom": item.uom,

#                             "conversion_factor": 1,

#                             "rate": item.rate,

#                             "base_rate": item.rate,

#                             "purchase_order": po.name,

#                             "purchase_order_item": item.name,

#                             "serial_no": serial,

#                             "warehouse": item.warehouse,

#                             "custom_incoming_logistic": il_name,

#                             "custom_bulk_gate_entry": gate_no,

#                             "use_serial_batch_fields": 1

#                         })

#                         if gate_no:
#                             gate_entries.add(gate_no)

#                         frappe.errprint({
#                             "SERIAL USED FROM GENERATED": serial
#                         })

#                         found = True
#                         break


#             if found:

#                 po.save(ignore_permissions=True)
#                 break


#         if not found:

#             errors.append(f"{serial} not found")

#             frappe.errprint({
#                 "NOT FOUND": serial
#             })


#     # ------------------------------------------------
#     # FINAL DEBUG
#     # ------------------------------------------------

#     frappe.errprint(" ")
#     frappe.errprint("===== FINAL RESULT =====")

#     frappe.errprint({

#         "TOTAL ITEMS": len(final_items),

#         "TOTAL ERRORS": len(errors),

#         "GATE ENTRY LIST": list(gate_entries)

#     })

#     frappe.errprint("========== END SERIAL UPLOAD ==========")


#     return {

#         "items": final_items,

#         "errors": errors,

#         "gate_entry_list": list(gate_entries)

#     }







import frappe
import pandas as pd


@frappe.whitelist()
def upload_serial_excel(file_url, supplier):

    frappe.errprint("===== START SERIAL UPLOAD =====")

    # -----------------------------
    # READ EXCEL
    # -----------------------------

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    df = pd.read_excel(file_path)

    serial_list = (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    serial_list = list(dict.fromkeys(serial_list))

    frappe.errprint({
        "TOTAL SERIAL": len(serial_list),
        "SERIAL SAMPLE": serial_list[:5]
    })


    # -----------------------------
    # GET PURCHASE ORDERS
    # -----------------------------

    po_list = frappe.get_all(

        "Purchase Order",

        filters={

            "supplier": supplier,

            "docstatus": 1

        },

        pluck="name"

    )

    frappe.errprint({

        "SUPPLIER": supplier,

        "PO LIST": po_list

    })


    po_docs = {

        po: frappe.get_doc("Purchase Order", po)

        for po in po_list

    }


    final_items = []
    errors = []
    gate_entries = set()


    # ==========================================================
    # MAIN LOOP
    # ==========================================================

    for serial in serial_list:

        found = False

        frappe.errprint(" ")
        frappe.errprint("CHECK SERIAL -> " + serial)


        for po in po_docs.values():

            for item in po.items:

                pending_qty = item.qty - item.received_qty


                # ----------------------------------------
                # FETCH INCOMING LOGISTICS
                # ----------------------------------------

                il_name = item.custom_incoming_logistic

                gate_no = None

                frappe.errprint({

                    "PO": po.name,

                    "ITEM": item.item_code,

                    "IL LINK": il_name

                })


                if il_name:

                    il_doc = frappe.db.get_value(

                        "Incoming Logistics",

                        il_name,

                        ["name", "gate_entry_no"],

                        as_dict=1

                    )

                    frappe.errprint({

                        "IL DOC": il_doc

                    })


                    if il_doc:

                        gate_no = il_doc.get("gate_entry_no")

                        frappe.errprint({

                            "GATE ENTRY NO": gate_no

                        })

                        if gate_no:
                            gate_entries.add(gate_no)


                # =====================================================
                # UNUSED SERIAL CHECK
                # =====================================================

                if item.custom_unused_serials:

                    unused_list = [

                        x.strip()

                        for x in item.custom_unused_serials.split("\n")

                        if x.strip()

                    ]

                    if serial in unused_list:

                        frappe.errprint({

                            "MATCH TYPE": "UNUSED",

                            "SERIAL": serial,

                            "ITEM": item.item_code

                        })


                        if pending_qty <= 0:

                            errors.append(

                                f"{serial} qty exceeded for {item.item_code}"

                            )

                            found = True
                            break


                        final_items.append({

                            "item_code": item.item_code,

                            "item_name": item.item_name,

                            "description": item.description,

                            "qty": 1,

                            "received_qty": 1,

                            "uom": item.uom,

                            "stock_uom": item.uom,

                            "conversion_factor": 1,

                            "rate": item.rate,

                            "base_rate": item.rate,

                            "purchase_order": po.name,

                            "purchase_order_item": item.name,

                            "serial_no": serial,

                            "warehouse": item.warehouse,

                            "custom_bulk_gate_entry": gate_no,

                            "use_serial_batch_fields": 1

                        })


                        # move serial unused → used

                        unused_list.remove(serial)

                        used_list = []

                        if item.custom_used_serials:

                            used_list = [

                                x.strip()

                                for x in item.custom_used_serials.split("\n")

                                if x.strip()

                            ]

                        used_list.append(serial)


                        item.custom_unused_serials = "\n".join(unused_list)

                        item.custom_used_serials = "\n".join(used_list)


                        frappe.errprint({

                            "SERIAL MOVED UNUSED → USED": serial

                        })


                        found = True
                        break


                # =====================================================
                # GENERATED SERIAL CHECK
                # =====================================================

                if item.custom_generated_serials:

                    gen_list = [

                        x.strip()

                        for x in item.custom_generated_serials.split("\n")

                        if x.strip()

                    ]

                    if serial in gen_list:

                        frappe.errprint({

                            "MATCH TYPE": "GENERATED",

                            "SERIAL": serial,

                            "ITEM": item.item_code

                        })


                        if pending_qty <= 0:

                            errors.append(

                                f"{serial} qty exceeded for {item.item_code}"

                            )

                            found = True
                            break


                        final_items.append({

                            "item_code": item.item_code,

                            "item_name": item.item_name,

                            "description": item.description,

                            "qty": 1,

                            "received_qty": 1,

                            "uom": item.uom,

                            "stock_uom": item.uom,

                            "conversion_factor": 1,

                            "rate": item.rate,

                            "base_rate": item.rate,

                            "purchase_order": po.name,

                            "purchase_order_item": item.name,

                            "serial_no": serial,

                            "warehouse": item.warehouse,

                            "custom_bulk_gate_entry": gate_no,

                            "use_serial_batch_fields": 1

                        })


                        frappe.errprint({

                            "SERIAL USED FROM GENERATED": serial

                        })


                        found = True
                        break


            if found:

                po.save(ignore_permissions=True)

                break


        if not found:

            errors.append(serial + " not found")

            frappe.errprint({

                "NOT FOUND": serial

            })


    # ==========================================================
    # FINAL DEBUG
    # ==========================================================

    frappe.errprint(" ")
    frappe.errprint("===== FINAL RESULT =====")

    frappe.errprint({

        "TOTAL ITEMS": len(final_items),

        "TOTAL ERRORS": len(errors),

        "GATE ENTRY LIST": list(gate_entries)

    })


    frappe.errprint("===== END SERIAL UPLOAD =====")


    return {

        "items": final_items,

        "errors": errors,

        "gate_entry_list": list(gate_entries)

    }