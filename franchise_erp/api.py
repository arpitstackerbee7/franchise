import frappe
from frappe.utils import flt


# ---------------- ROUNDING RULE ----------------
def round_to_nearest_9(rate):
    rate = int(round(rate))
    last = rate % 10

    if last == 9:
        return rate
    if last <= 5:
        return rate - last - 1
    return rate + (9 - last)


# ---------------- TAX AMOUNT ----------------
def get_item_tax_amount(row):
    return (
        (row.igst_amount or 0) +
        (row.cgst_amount or 0) +
        (row.sgst_amount or 0) +
        (row.cess_amount or 0) +
        (row.cess_non_advol_amount or 0)
    )


# ---------------- COST CALCULATION ----------------
def calculate_cost(row, cost_type, tax_mode):
    """
    cost_type  : Basic Cost / Effective Cost
    tax_mode   : Net Of Tax / Gross Of Tax
    """

    item_tax = get_item_tax_amount(row)

    # Base cost selection
    if cost_type == "Effective Cost":
        base_cost = flt(row.net_rate)
    else:  # Basic Cost
        base_cost = flt(row.price_list_rate)

    if tax_mode == "Gross Of Tax":
        return base_cost + item_tax

    return base_cost


# ---------------- CREATE ITEM PRICE ----------------
def create_item_price(item_code, price_list, cost, margin_type, margin_value, valid_from):
    """
    Creates Item Price only once (no overwrite).
    Applies rounding rule to end with 9.
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


# ---------------- MAIN FUNCTION (ON PO SUBMIT) ----------------
def create_selling_price_from_po(doc, method):
    """
    PO submit par:
    - MRP/RSP aur WSP dono alag logic se banenge
    - MRP/RSP same rule follow karega
    - WSP alag rule follow karega
    - Ek baar banne ke baad overwrite nahi hoga
    """

    pricing_rule = frappe.db.get_value(
        "Pricing Rule",
        {"disable": 0},
        [
            # MRP / RSP
            "custom_cost_will_be_taken_as",
            "custom_consider_tax_in_margin",
            "custom_mrp_will_be_taken_as",
            "custom_margin_typee",
            "custom_minimum_margin",

            # WSP
            "custom_cost__will_be_taken_as",
            "custom_consider__tax_in_margin",
            "custom_wsp_margin_type",
            "custom_wsp_minimum_margin"
        ],
        as_dict=True
    )

    if not pricing_rule:
        frappe.throw("No active Pricing Rule found")

    # ---------------- CONFIG ----------------
    # MRP / RSP
    mrp_cost_type = pricing_rule.custom_cost_will_be_taken_as or "Basic Cost"
    mrp_tax_mode = pricing_rule.custom_consider_tax_in_margin or "Net Of Tax"
    selling_price_list = pricing_rule.custom_mrp_will_be_taken_as or "MRP"
    mrp_margin_type = pricing_rule.custom_margin_typee or "Percentage"
    mrp_margin_value = flt(pricing_rule.custom_minimum_margin or 0)

    # WSP
    wsp_cost_type = pricing_rule.custom_cost__will_be_taken_as or "Effective Cost"
    wsp_tax_mode = pricing_rule.custom_consider__tax_in_margin or "Net Of Tax"
    wsp_margin_type = pricing_rule.custom_wsp_margin_type or "Percentage"
    wsp_margin_value = flt(pricing_rule.custom_wsp_minimum_margin or 0)

    # ---------------- LOOP ITEMS ----------------
    for row in doc.items:
        if not row.item_code:
            continue

        # ----- MRP / RSP COST -----
        cost_mrp = calculate_cost(row, mrp_cost_type, mrp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list=selling_price_list,   # MRP or RSP
            cost=cost_mrp,
            margin_type=mrp_margin_type,
            margin_value=mrp_margin_value,
            valid_from=doc.transaction_date
        )

        # ----- WSP COST -----
        cost_wsp = calculate_cost(row, wsp_cost_type, wsp_tax_mode)

        create_item_price(
            item_code=row.item_code,
            price_list="WSP",
            cost=cost_wsp,
            margin_type=wsp_margin_type,
            margin_value=wsp_margin_value,
            valid_from=doc.transaction_date
        )
