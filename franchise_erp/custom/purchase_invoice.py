import frappe
from frappe.utils import flt

def apply_intercompany_gst(doc, method=None):

    if not doc.is_internal_supplier:
        return

    # -----------------------------
    # 1️⃣ GST % FROM ITEMS
    # -----------------------------
    gst_percent = 0
    for item in doc.items:
        if item.item_tax_template:
            if "5%" in item.item_tax_template:
                gst_percent = 5
            elif "12%" in item.item_tax_template:
                gst_percent = 12
            elif "18%" in item.item_tax_template:
                gst_percent = 18
        if gst_percent:
            break

    if not gst_percent:
        return

    # -----------------------------
    # 2️⃣ IN / OUT STATE
    # -----------------------------
    company_state = frappe.db.get_value(
        "Address", doc.billing_address, "state"
    )
    supplier_state = frappe.db.get_value(
        "Address", doc.supplier_address, "state"
    )

    is_in_state = company_state == supplier_state

    # -----------------------------
    # 3️⃣ COMPANY ABBR
    # -----------------------------
    abbr = frappe.db.get_value("Company", doc.company, "abbr")

    # -----------------------------
    # 4️⃣ SET PURCHASE TAX TEMPLATE
    # -----------------------------
    if is_in_state:
        doc.taxes_and_charges = f"Input GST In-state - {abbr}"
    else:
        doc.taxes_and_charges = f"Input GST Out-state - {abbr}"

    # -----------------------------
    # 5️⃣ FORCE TAX TABLE REBUILD
    # -----------------------------
    doc.set_taxes()
    doc.calculate_taxes_and_totals()
