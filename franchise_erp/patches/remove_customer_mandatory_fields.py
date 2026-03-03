import frappe

def execute():
    frappe.db.delete("Property Setter", {
        "doc_type": "Customer",
        "field_name": ["in", ["default_price_list", "credit_limits"]],
        "property": "reqd"
    })