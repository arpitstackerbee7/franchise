

# /franchise_erp/custom/purchase_invoice_hooks.py

import frappe
from frappe.utils import flt

def apply_item_gst(doc, method=None):
    if not doc.is_internal_supplier:
        return

    for item in doc.items:
        if not item.custom_total_invoice_amount:
            continue

        taxable = flt(item.custom_total_invoice_amount)
        gst_rate = 5 if taxable <= 2500 else 18

        template = get_item_tax_template(doc.company, gst_rate)
        if not template:
            frappe.throw(f"GST {gst_rate}% Item Tax Template not found")

        item.item_tax_template = template
        item.rate = taxable

    # VERY IMPORTANT
    doc.calculate_taxes_and_totals()

def get_item_tax_template(company, gst_rate):
    templates = frappe.get_all(
        "Item Tax Template",
        filters={"company": company},
        pluck="name"
    )

    for name in templates:
        rates = frappe.get_all(
            "Item Tax Template Detail",
            filters={"parent": name},
            pluck="tax_rate"
        )

        rates = [flt(r) for r in rates]
        if gst_rate in rates or sum(rates) == gst_rate:
            return name

    return None

# def update_purchase_invoice_totals(doc, method=None):
#     """
#     FINAL REAL WORKING LOGIC — NO OVERRIDE OF ERPNext DEFAULT TOTAL FIELDS
#     """
    
#     # --------------------------
#     # 1️⃣ BASE TOTAL (CUSTOM)
#     # --------------------------
#     base_total = sum(flt(i.custom_total_invoice_amount) for i in doc.items)
    
#     # DO NOT TOUCH: doc.total, doc.net_total, doc.base_total
#     # Reason: ERPNext recalc on submit

#     total_tax = 0.0

#     # --------------------------
#     # 2️⃣ TAX CALCULATION
#     # --------------------------
#     for tax in doc.taxes:
#         if tax.charge_type == "On Net Total":

#             tax.net_amount = base_total
#             tax.tax_amount = flt(base_total * (flt(tax.rate) / 100))

#             # Display only
#             tax.total = tax.net_amount - tax.tax_amount

#             total_tax += tax.tax_amount


#     # --------------------------
#     # 3️⃣ FINAL GRAND TOTAL (CUSTOM FIELDS ONLY)
#     # --------------------------
#     grand_total = base_total + total_tax

#     doc.custom_total_purchase_invoice = base_total
#     doc.custom_total_gst = total_tax
#     doc.custom_purchase_grand_total = grand_total

#     doc.grand_total = rounded(grand_total)
#     doc.rounded_total = rounded(grand_total)
#     doc.outstanding_amount = rounded(grand_total)

#     doc.taxes_and_charges_added = total_tax
#     doc.taxes_and_charges_deducted = 0
#     doc.total_taxes_and_charges = total_tax


# def before_submit(doc, method=None):
#     # Disable GL auto entries
#     update_purchase_invoice_totals(doc, method)


# def on_submit(doc, method=None):
#     # Again disable GL auto posting
#     update_purchase_invoice_totals(doc, method)

import frappe
from frappe.utils import flt


def apply_hsn_based_gst(doc, method=None):

    if not doc.items:
        return

    # 🔹 Clear existing taxes
    doc.taxes = []

    total_taxable = 0

    for item in doc.items:
        if not item.custom_total_invoice_amount:
            continue

        taxable = flt(item.custom_total_invoice_amount)
        total_taxable += taxable

        # 🔹 Decide GST rate based on amount
        if taxable <= 2500:
            gst_rate = 5
        else:
            gst_rate = 18

        # 🔹 Override taxable base (IMPORTANT)
        item.net_amount = taxable
        item.base_net_amount = taxable
        item.taxable_value = taxable

        item.custom_applied_gst_rate = gst_rate  # optional custom field

    # -------------------------
    # APPLY GST (Company based)
    # -------------------------
    company = doc.company

    # Example account mapping (adjust if needed)
    cgst_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": ["like", "%CGST%"], "is_group": 0},
        "name"
    )

    sgst_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": ["like", "%SGST%"], "is_group": 0},
        "name"
    )

    for item in doc.items:
        taxable = flt(item.custom_total_invoice_amount)
        gst_rate = item.custom_applied_gst_rate

        cgst_rate = sgst_rate = gst_rate / 2

        cgst_amount = taxable * cgst_rate / 100
        sgst_amount = taxable * sgst_rate / 100

        # 🔹 Append CGST
        doc.append("taxes", {
            "charge_type": "On Net Total",
            "account_head": cgst_account,
            "description": "CGST",
            "rate": cgst_rate,
            "tax_amount": cgst_amount
        })

        # 🔹 Append SGST
        doc.append("taxes", {
            "charge_type": "On Net Total",
            "account_head": sgst_account,
            "description": "SGST",
            "rate": sgst_rate,
            "tax_amount": sgst_amount
        })

    # 🔹 Let ERPNext calculate totals
    doc.calculate_taxes_and_totals()


#input gst value save in serial no


import frappe
from frappe.utils import flt

# def update_serial_input_gst(doc, method):

#     # 1️⃣ Total GST taken from invoice
#     total_gst = flt(doc.total_taxes_and_charges)

#     # 2️⃣ Total quantity of all items
#     total_qty = sum([flt(d.qty) for d in doc.items]) or 1

#     # 3️⃣ Per-item GST value
#     per_item_gst = total_gst / total_qty

#     # -----------------------------------
#     # LOOP THROUGH ALL ITEMS
#     # -----------------------------------
#     for row in doc.items:

#         # Per-item price (single quantity value)
#         single_qty_price = flt(row.rate)   # <-- NEW (this is what you wanted)

#         # Multiple serial numbers support
#         serial_nos = (row.serial_no or "").split("\n")

#         for sn in serial_nos:
#             sn = sn.strip()
#             if not sn:
#                 continue

#             # 4️⃣ Save GST per quantity to Serial No
#             frappe.db.set_value(
#                 "Serial No",
#                 sn,
#                 "custom_input_gst",
#                 per_item_gst
#             )

#             # 5️⃣ Save single quantity invoice price to Serial No
#             frappe.db.set_value(
#                 "Serial No",
#                 sn,
#                 "custom_invoice_amount",   # <-- Your custom field
#                 single_qty_price           # <-- Value saved
#             )

#     frappe.db.commit()
def update_serial_input_gst(doc, method):

    # 1️⃣ Find GST Rate from Purchase Taxes & Charges Template
    gst_rate = 0

    if doc.taxes_and_charges:
        # Get template doc
        template = frappe.get_doc("Purchase Taxes and Charges Template", doc.taxes_and_charges)

        for tax in template.taxes:
            gst_rate += flt(tax.rate)  # Example: 2.5 + 2.5 = 5%

    # -----------------------------------
    # 2️⃣ LOOP THROUGH ITEMS
    # -----------------------------------
    for row in doc.items:

        # Single quantity price
        item_rate = flt(row.rate)

        # GST for this item qty
        item_gst = (item_rate * gst_rate) / 100

        # Serial No list
        serial_nos = (row.serial_no or "").split("\n")

        for sn in serial_nos:
            sn = sn.strip()
            if not sn:
                continue

            # Save GST
            frappe.db.set_value("Serial No", sn, "custom_input_gst", item_gst)

            # Save rate
            frappe.db.set_value("Serial No", sn, "custom_invoice_amount", item_rate)

    frappe.db.commit()



# add single item rate and single item input gst
import frappe
from decimal import Decimal

def calculate_single_item_gst(doc, method):
    frappe.log_error("on_submit triggered", "PI GST DEBUG")

    for item in doc.items:
        qty = Decimal(str(item.qty or 1))
        total_amount = Decimal(str(item.custom_total_invoice_amount or 0))

        # 1. Single Item Rate
        single_item_rate = total_amount / qty if qty else total_amount

        # 2. GST %
        gst_percent = Decimal("0")
        if item.item_tax_template:
            tax = frappe.db.get_value(
                "Item Tax Template Detail",
                {"parent": item.item_tax_template},
                "tax_rate"
            )
            gst_percent = Decimal(str(tax or 0))

        # 3. GST Amount
        single_item_gst_amount = (single_item_rate * gst_percent) / 100

        # 🔥 DEBUG LOG
        frappe.log_error(
            f"""
            ITEM: {item.item_code}
            QTY: {qty}
            TOTAL: {total_amount}
            RATE: {single_item_rate}
            GST%: {gst_percent}
            GST AMT: {single_item_gst_amount}
            """,
            "PI GST CALCULATION"
        )

        # 🔥 DB UPDATE (MANDATORY)
        frappe.db.set_value(
            "Purchase Invoice Item",
            item.name,
            {
                "custom_single_item_rate": single_item_rate,
                "custom_single_item_input_gst_amount": single_item_gst_amount
            }
        )
