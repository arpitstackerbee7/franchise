import frappe
from frappe.utils import flt, round_based_on_smallest_currency_fraction

import frappe
from frappe.utils import flt, cint
# @frappe.whitelist()
# def calculate_sis_values(customer, rate):

#     if not customer:
#         frappe.throw("Customer is required")

#     company = frappe.db.get_value("Customer", customer, "represents_company")
#     if not company:
#         frappe.throw("Customer has no represents_company")

#     c = frappe.get_value(
#         "SIS Configuration",
#         {"company": company},
#         ["output_gst_min_net_rate", "output_gst_max_net_rate", "fresh_margin"],
#         as_dict=True
#     )

#     if not c:
#         frappe.throw("SIS Configuration missing")

#     rate = flt(rate)

#     # 1️⃣ OUTPUT GST SLAB
#     if rate <= flt(c.output_gst_min_net_rate):
#         gst_percent = 5
#     elif rate >= flt(c.output_gst_max_net_rate):
#         gst_percent = 18
#     else:
#         gst_percent = 12

#     # 2️⃣ GST INCLUSIVE SPLIT
#     net_sale_value = flt(rate * 100 / (100 + gst_percent), 2)
#     gst_value = flt(rate - net_sale_value, 2)

#     # 3️⃣ MARGIN (ON MRP)
#     margin_percent = flt(c.fresh_margin)
#     margin_amount = flt(rate * margin_percent / 100, 2)

#     # 4️⃣ FINAL TAXABLE VALUE
#     taxable_value = flt(net_sale_value - margin_amount, 2)

#     return {
#         "gst_percent": gst_percent,
#         "output_gst_value": gst_value,
#         "margin_percent": margin_percent,
#         "margin_amount": margin_amount,
#         "net_sale_value": net_sale_value,
#         "taxable_value": taxable_value
#     }

import frappe
from frappe.utils import flt


@frappe.whitelist()
def calculate_sis_values(customer, rate):

    # ---------------- BASIC CHECK ----------------
    if not customer or not rate:
        return None   # ❌ silently skip

    # ---------------- SKIP FOR CUSTOMER / BRANCH LOGIN ----------------
    user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
    if user_type == "Website User":
        return None

    # ---------------- CUSTOMER → COMPANY ----------------
    company = frappe.db.get_value("Customer", customer, "represents_company")
    if not company:
        return None   # ✅ Branch flow → skip logic

    # ---------------- SIS CONFIG ----------------
    c = frappe.get_value(
        "SIS Configuration",
        {"company": company},
        [
            "output_gst_min_net_rate",
            "output_gst_max_net_rate",
            "fresh_margin"
        ],
        as_dict=True
    )

    if not c:
        return None   # ❌ no config → skip

    rate = flt(rate)

    # ---------------- OUTPUT GST SLAB ----------------
    if rate <= flt(c.output_gst_min_net_rate):
        gst_percent = 5
    elif rate >= flt(c.output_gst_max_net_rate):
        gst_percent = 18
    else:
        gst_percent = 12

    # ---------------- GST INCLUSIVE SPLIT ----------------
    net_sale_value = flt(rate * 100 / (100 + gst_percent), 2)
    gst_value = flt(rate - net_sale_value, 2)

    # ---------------- MARGIN (ON MRP) ----------------
    margin_percent = flt(c.fresh_margin)
    margin_amount = flt(rate * margin_percent / 100, 2)

    # ---------------- FINAL TAXABLE VALUE ----------------
    taxable_value = flt(net_sale_value - margin_amount, 2)

    return {
        "gst_percent": gst_percent,
        "output_gst_value": gst_value,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "net_sale_value": net_sale_value,
        "taxable_value": taxable_value
    }

import frappe
from frappe.utils import flt

# def apply_sis_pricing(doc, method=None):

#     if not doc.customer:
#         return

#     for item in doc.items:

#         if not item.rate:
#             continue

#         # Call SIS calculation
#         d = calculate_sis_values(doc.customer, item.rate)

#         # 🔹 Custom fields (for display)
#         item.custom_output_gst_ = d["gst_percent"]
#         item.custom_output_gst_value = d["output_gst_value"]
#         item.custom_margins_ = d["margin_percent"]
#         item.custom_margin_amount = d["margin_amount"]
#         item.custom_net_sale_value = d["net_sale_value"]
#         item.custom_total_invoice_amount = d["taxable_value"]

#         # 🔥 OVERRIDE ERPNext BASE 🔥
#         item.rate = d["taxable_value"]
#         item.net_rate = d["taxable_value"]
#         item.amount = flt(d["taxable_value"] * item.qty)
#         item.net_amount = item.amount

#     # 🔁 Let ERPNext calculate GST & totals
#     doc.calculate_taxes_and_totals()

def apply_sis_pricing(doc, method=None):

    if not doc.customer:
        return

    for item in doc.items:

        if not item.rate:
            continue

       # Call SIS calculation
    d = calculate_sis_values(doc.customer, item.rate)

    if d:
        # ✅ Populate custom fields from SIS calculation
        item.custom_output_gst_ = d.get("gst_percent", 0)
        item.custom_output_gst_value = d.get("output_gst_value", 0)
        item.custom_margins_ = d.get("margin_percent", 0)
        item.custom_margin_amount = d.get("margin_amount", 0)
        item.custom_net_sale_value = d.get("net_sale_value", 0)
        item.custom_total_invoice_amount = d.get("taxable_value", 0)

        # 🔥 GST EXCLUSIVE RATE
        item.rate = d.get("taxable_value", 0)
        item.net_rate = d.get("taxable_value", 0)
        item.amount = flt(d.get("taxable_value", 0) * item.qty)
        item.net_amount = item.amount

        # 🔥 Correct GST slab
        item.item_tax_template = get_item_tax_template(d.get("gst_percent", 0))
    else:
        # ❌ SIS calculation skipped: fallback to defaults
        item.custom_output_gst_ = 0
        item.custom_output_gst_value = 0
        item.custom_margins_ = 0
        item.custom_margin_amount = 0
        item.custom_net_sale_value = item.rate
        item.custom_total_invoice_amount = item.rate

        # GST EXCLUSIVE RATE remains same as entered
        item.rate = item.rate
        item.net_rate = item.rate
        item.amount = flt(item.rate * item.qty)
        item.net_amount = item.amount

        # Keep original item tax template or fallback
        item.item_tax_template = item.item_tax_template or get_item_tax_template(0)


    # 🔥 VERY IMPORTANT
    for tax in doc.taxes:
        tax.included_in_print_rate = 0

    # Reset & recalc
    doc.taxes = []
    doc.calculate_taxes_and_totals()
    
def get_item_tax_template(gst_percent):
    if gst_percent == 5:
        return "GST 5%"
    elif gst_percent == 12:
        return "GST 12%"
    elif gst_percent == 18:
        return "GST 18%"
    return None
