
import frappe
from frappe.utils import flt, rounded

def update_purchase_invoice_totals(doc, method=None):
    """
    FINAL REAL WORKING LOGIC — NO OVERRIDE OF ERPNext DEFAULT TOTAL FIELDS
    """
    
    # --------------------------
    # 1️⃣ BASE TOTAL (CUSTOM)
    # --------------------------
    base_total = sum(flt(i.custom_total_invoice_amount) for i in doc.items)
    
    # DO NOT TOUCH: doc.total, doc.net_total, doc.base_total
    # Reason: ERPNext recalc on submit

    total_tax = 0.0

    # --------------------------
    # 2️⃣ TAX CALCULATION
    # --------------------------
    for tax in doc.taxes:
        if tax.charge_type == "On Net Total":

            tax.net_amount = base_total
            tax.tax_amount = flt(base_total * (flt(tax.rate) / 100))

            # Display only
            tax.total = tax.net_amount - tax.tax_amount

            total_tax += tax.tax_amount


    # --------------------------
    # 3️⃣ FINAL GRAND TOTAL (CUSTOM FIELDS ONLY)
    # --------------------------
    grand_total = base_total + total_tax

    doc.custom_total_purchase_invoice = base_total
    doc.custom_total_gst = total_tax
    doc.custom_purchase_grand_total = grand_total

    doc.grand_total = rounded(grand_total)
    doc.rounded_total = rounded(grand_total)
    doc.outstanding_amount = rounded(grand_total)

    doc.taxes_and_charges_added = total_tax
    doc.taxes_and_charges_deducted = 0
    doc.total_taxes_and_charges = total_tax


def before_submit(doc, method=None):
    # Disable GL auto entries
    update_purchase_invoice_totals(doc, method)


def on_submit(doc, method=None):
    # Again disable GL auto posting
    update_purchase_invoice_totals(doc, method)



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
