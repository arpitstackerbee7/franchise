import frappe

def fix_address_issue(doc, method):

    # ❌ ALWAYS clear wrong field
    doc.delivery_address = None

    # ✅ ensure correct address link
    if not doc.delivery_address_name:
        frappe.throw("Please select Delivery Address (Address Link)")