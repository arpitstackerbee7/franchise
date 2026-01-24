import frappe

def round_to_nearest_9(rate):
    """
    Rule:
    - Agar last digit 9 hai → no change
    - Agar last digit <= 5 → pichla 9
    - Agar last digit > 5 → agla 9
    """

    if not rate:
        return rate

    rate = int(round(rate))
    last_digit = rate % 10

    # Already 9 hai, kuch change nahi
    if last_digit == 9:
        return rate

    # 5 ya kam → pichla 9
    if last_digit <= 5:
        return rate - last_digit - 1

    # 5 se zyada → agla 9
    return rate + (9 - last_digit)


def apply_rounding_on_doc(doc):
    """
    Ye function Sales documents ke items par rounding apply karega
    """
    for item in doc.items:
        old_rate = item.rate
        new_rate = round_to_nearest_9(item.rate)
        item.rate = new_rate

        frappe.logger().info(
            f"Pricing Round Utility | {item.item_code} : {old_rate} -> {new_rate}"
        )










def on_change(doc, method):


    apply_rounding_on_doc(doc)




import frappe

def apply_scheme_on_dn(doc, method):
   
    pass


import frappe

# def create_selling_price_from_po(doc, method):
#     SELLING_PRICE_LISTS = ["MRP", "RSP"]

#     for row in doc.items:
#         if not row.item_code or not row.rate:
#             continue

#         for price_list in SELLING_PRICE_LISTS:
#             item_price_name = frappe.db.get_value(
#                 "Item Price",
#                 {
#                     "item_code": row.item_code,
#                     "price_list": price_list
#                 },
#                 "name"
#             )

#             if item_price_name:
#                 # Update existing selling price
#                 frappe.db.set_value(
#                     "Item Price",
#                     item_price_name,
#                     {
#                         "price_list_rate": row.rate,
#                         "valid_from": doc.transaction_date
#                     }
#                 )
#             else:
#                 # Create new selling price
#                 frappe.get_doc({
#                     "doctype": "Item Price",
#                     "item_code": row.item_code,
#                     "price_list": price_list,
#                     "price_list_rate": row.rate,
#                     "valid_from": doc.transaction_date
#                 }).insert(ignore_permissions=True)

import frappe
from frappe.utils import flt


def create_selling_price_from_po(doc, method):
    """
    PO Submit par:
    - Cost calculate karega (Basic / Effective + Net/Gross of Tax)
    - WSP create karega
    - MRP ya RSP (jo rule me selected ho) create karega
    - Ek baar ban jaane ke baad overwrite nahi karega
    """

    try:
        # ---------------- GET ACTIVE PRICING RULE ----------------
        pricing_rule = frappe.db.get_value(
            "Pricing Rule",
            {"disable": 0},
            [
                "name",
                "custom_cost_will_be_taken_as",
                "custom_consider_tax_in_margin",

                # MRP / RSP
                "custom_mrp_will_be_taken_as",
                "custom_margin_typee",
                "custom_minimum_margin",

                # WSP
                "custom_wsp_margin_type",
                "custom_wsp_minimum_margin",
            ],
            as_dict=True
        )

        if not pricing_rule:
            frappe.throw("No active Pricing Rule found")

        # ---------------- BASIC CONFIG ----------------
        cost_type = pricing_rule.custom_cost_will_be_taken_as or "Basic Cost"
        tax_mode = pricing_rule.custom_consider_tax_in_margin or "Net Of Tax"

        # MRP / RSP Config
        selling_price_list = pricing_rule.custom_mrp_will_be_taken_as or "MRP"
        mrp_margin_type = pricing_rule.custom_margin_typee or "Percentage"
        mrp_margin_value = flt(pricing_rule.custom_minimum_margin or 0)

        # WSP Config
        wsp_margin_type = pricing_rule.custom_wsp_margin_type or "Percentage"
        wsp_margin_value = flt(pricing_rule.custom_wsp_minimum_margin or 0)

        # ---------------- VALIDATION ----------------
        if mrp_margin_value < 0 or wsp_margin_value < 0:
            frappe.throw("Negative margin is not allowed for MRP / RSP / WSP")

        for row in doc.items:
            try:
                if not row.item_code:
                    continue

                # ---------------- TAX AMOUNT ----------------
                item_tax = (
                    flt(row.igst_amount) +
                    flt(row.cgst_amount) +
                    flt(row.sgst_amount) +
                    flt(row.cess_amount) +
                    flt(row.cess_non_advol_amount)
                )

                # ---------------- BASE COST ----------------
                # Always vendor basic rate
                base_cost = flt(row.price_list_rate)
                if not base_cost:
                    continue

                # ---------------- COST CALCULATION ----------------
                if cost_type == "Basic Cost":
                    if tax_mode == "Net Of Tax":
                        cost = base_cost
                    else:  # Gross Of Tax
                        cost = base_cost + item_tax

                elif cost_type == "Effective Cost":
                    if tax_mode == "Net Of Tax":
                        cost = base_cost
                    else:  # Gross Of Tax
                        cost = base_cost + item_tax
                else:
                    cost = base_cost

                cost = flt(cost)

                # ---------------- CREATE WSP ----------------
                create_item_price(
                    item_code=row.item_code,
                    price_list="WSP",
                    cost=cost,
                    margin_type=wsp_margin_type,
                    margin_value=wsp_margin_value,
                    valid_from=doc.transaction_date
                )

                # ---------------- CREATE MRP / RSP ----------------
                create_item_price(
                    item_code=row.item_code,
                    price_list=selling_price_list,
                    cost=cost,
                    margin_type=mrp_margin_type,
                    margin_value=mrp_margin_value,
                    valid_from=doc.transaction_date
                )

            except Exception as item_error:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Error while creating price for Item {row.item_code}"
                )
                frappe.throw(f"Price creation failed for item {row.item_code}. Check error logs.")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in create_selling_price_from_po")
        frappe.throw("Selling price creation failed. Please check Error Logs.")


def create_item_price(item_code, price_list, cost, margin_type, margin_value, valid_from):
    """
    Generic function to create Item Price.
    One-time creation only (no overwrite).
    """

    try:
        # Already exists? then skip
        if frappe.db.exists("Item Price", {
            "item_code": item_code,
            "price_list": price_list
        }):
            return

        # Margin calculation
        if margin_type == "Percentage":
            margin_amount = cost * margin_value / 100
        else:  # Amount
            margin_amount = margin_value

        final_price = flt(cost + margin_amount)

        doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": price_list,
            "price_list_rate": round(final_price, 2),
            "valid_from": valid_from
        })
        doc.insert(ignore_permissions=True)

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed to create Item Price for {item_code} in {price_list}"
        )
        raise



def get_item_tax_amount(row):
    return (
        (row.igst_amount or 0) +
        (row.cgst_amount or 0) +
        (row.sgst_amount or 0) +
        (row.cess_amount or 0) +
        (row.cess_non_advol_amount or 0)
    )
