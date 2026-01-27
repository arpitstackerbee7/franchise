


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
def calculate_cost(row, cost_type, tax_mode):
    """
    cost_type : Basic Cost / Effective Cost
    tax_mode  : Net Of Tax / Gross Of Tax

    Effective Cost:
        Net Rate + Tax
    Basic Cost:
        Basic Purchase Rate
    """

    item_tax = get_item_tax_amount(row)

    # Effective Cost
    if cost_type == "Effective Cost":
        base_cost = flt(row.net_rate)
        if tax_mode == "Gross Of Tax":
            return base_cost + item_tax
        return base_cost

    # Basic Cost
    base_cost = flt(row.price_list_rate)
    if tax_mode == "Gross Of Tax":
        return base_cost + item_tax
    return base_cost


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
def create_selling_price_from_po(doc, method):
    """
    MRP / RSP aur WSP dono ke liye alag-alag config chalegi.

    MRP / RSP:
        - Apni cost base
        - Apna tax mode
        - Apna margin
        - Exact value (jaise 109.72)

    WSP:
        - Alag cost base
        - Alag tax mode
        - Alag margin
        - Rounding to nearest 9
    """

    pricing_rule = frappe.db.get_value(
        "Pricing Rule",
        {"disable": 0},
        [
            # ---------- MRP / RSP ----------
            "custom_cost_will_be_taken_as",
            "custom_consider_tax_in_margin",
            "custom_mrp_will_be_taken_as",
            "custom_margin_typee",
            "custom_minimum_margin",

            # ---------- WSP (double underscore fields) ----------
            "custom_cost__will_be_taken_as",
            "custom_consider__tax_in_margin",
            "custom_wsp_margin_type",
            "custom_wsp_minimum_margin"
        ],
        as_dict=True
    )

    if not pricing_rule:
        frappe.throw("No active Pricing Rule found")

    # ---------------- MRP / RSP CONFIG ----------------
    mrp_cost_type = pricing_rule.custom_cost_will_be_taken_as or "Effective Cost"
    mrp_tax_mode = pricing_rule.custom_consider_tax_in_margin or "Gross Of Tax"
    selling_price_list = pricing_rule.custom_mrp_will_be_taken_as or "MRP"
    mrp_margin_type = pricing_rule.custom_margin_typee or "Percentage"
    mrp_margin_value = flt(pricing_rule.custom_minimum_margin or 0)

    # ---------------- WSP CONFIG (Double underscore) ----------------
    wsp_cost_type = pricing_rule.custom_cost__will_be_taken_as or "Effective Cost"
    wsp_tax_mode = pricing_rule.custom_consider__tax_in_margin or "Net Of Tax"
    wsp_margin_type = pricing_rule.custom_wsp_margin_type or "Percentage"
    wsp_margin_value = flt(pricing_rule.custom_wsp_minimum_margin or 0)

    # ---------------- PROCESS ITEMS ----------------
    for row in doc.items:
        if not row.item_code:
            continue

        # ===== MRP / RSP PRICE =====
        cost_mrp = calculate_cost(row, mrp_cost_type, mrp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list=selling_price_list,   # MRP or RSP
            cost=cost_mrp,
            margin_type=mrp_margin_type,
            margin_value=mrp_margin_value,
            valid_from=doc.transaction_date,
            apply_rounding=False              # MRP/RSP exact price
        )

        # ===== WSP PRICE =====
        cost_wsp = calculate_cost(row, wsp_cost_type, wsp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list="WSP",
            cost=cost_wsp,
            margin_type=wsp_margin_type,
            margin_value=wsp_margin_value,
            valid_from=doc.transaction_date,
            apply_rounding=True               # WSP rounding to 9
        )





















