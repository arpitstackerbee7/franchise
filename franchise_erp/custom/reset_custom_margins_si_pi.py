import frappe
from frappe.utils import flt, rounded

def reset_custom_margins(doc, method=None):
    """
    Remove margin from Branch → End Customer invoice
    and recalculate totals properly.
    """

    # Get user's company
    user_company = frappe.db.get_value("User", frappe.session.user, "company")
    if not user_company:
        return

    # Check SIS Config for user's company
    if not frappe.db.exists("SIS Configuration", {"company": user_company}):
        return

    # Reset margins item-wise
    for item in doc.items:

        # IMPORTANT: Correct field names here ⬇⬇⬇
        item.custom_margins = 0
        item.custom_margin_amount = 0

        # Reset invoice amount to base amount without margin
        item.custom_total_invoice_amount = flt(item.amount or 0)

    # Recalculate total WITHOUT margin
    total_amount = sum([flt(i.custom_total_invoice_amount) for i in doc.items])

    # Add tax
    total_with_tax = total_amount + flt(doc.total_taxes_and_charges or 0)

    # Update document totals
    doc.grand_total = rounded(total_with_tax)
    doc.rounded_total = rounded(total_with_tax)
    doc.outstanding_amount = rounded(total_with_tax)
    doc.custom_total_purchase_invoice = rounded(total_with_tax)
    doc.custom_total_invoice_amount = rounded(total_with_tax)

