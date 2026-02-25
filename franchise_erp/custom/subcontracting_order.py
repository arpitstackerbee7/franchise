import frappe

# @frappe.whitelist()
# def get_outgoing_logistics_data(subcontracting_order):
#     sc = frappe.get_doc("Subcontracting Order", subcontracting_order)

#     # Prevent duplicate
#     existing = frappe.db.exists(
#         "Outgoing Logistics",
#         {"document_no": sc.name}
#     )
#     if existing:
#         frappe.throw(f"Outgoing Logistics already exists: {existing}")

#     return {
#         "owner_site": sc.company,
#         "company_abbreviation": frappe.db.get_value("Company", sc.company, "abbr"),
#         "consignee_supplier": sc.supplier,
#         "transporter": sc.supplier,
#         "date": frappe.utils.today(),
#         "document_no": sc.name,
#         # "document_date": sc.transaction_date,
#         "quantity": sc.total_qty,
#         "unit": "Nos",
#         # "type": "S&D: Sales Invoice/Transfer In",
#         "type": "Job Order",
#         "mode": "Land",
#     }
import frappe
from frappe.utils import today

@frappe.whitelist()
def get_outgoing_logistics_data(subcontracting_order):

    if not subcontracting_order:
        frappe.throw("Subcontracting Order is required")

    # ✅ Safe doc fetch
    sc = frappe.get_doc("Subcontracting Order", subcontracting_order)

    return {
        "owner_site": sc.company,
        "company_abbreviation": frappe.db.get_value(
            "Company",
            sc.company,
            "abbr"
        ),
        "consignee_supplier": sc.supplier,
        "transporter": sc.supplier,
        "date": today(),
        "quantity": sc.total_qty,
        "unit": "Nos",
        "type": "Job Order",
        "mode": "Land",
        "references": [
            {
                "source_doctype": "Job Work Order",
                "source_name": sc.name
            }
        ]
    }





import frappe

@frappe.whitelist()
def get_subcontracting_order_city(subcontracting_order):
    so = frappe.get_doc("Subcontracting Order", subcontracting_order)

    # 1️⃣ Shipping Address (priority)
    if so.shipping_address:
        city = frappe.db.get_value(
            "Address",
            so.shipping_address,
            "custom_citytown"
        )
        if city:
            return city

    # 2️⃣ Billing Address (fallback)
    if so.billing_address:
        city = frappe.db.get_value(
            "Address",
            so.billing_address,
            "custom_citytown"
        )
        if city:
            return city

    return None