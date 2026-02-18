import frappe

@frappe.whitelist()
def get_outgoing_logistics_data(subcontracting_order):
    sc = frappe.get_doc("Subcontracting Order", subcontracting_order)

    # Prevent duplicate
    existing = frappe.db.exists(
        "Outgoing Logistics",
        {"document_no": sc.name}
    )
    if existing:
        frappe.throw(f"Outgoing Logistics already exists: {existing}")

    return {
        "owner_site": sc.company,
        "company_abbreviation": frappe.db.get_value("Company", sc.company, "abbr"),
        "consignee_supplier": sc.supplier,
        "transporter": sc.supplier,
        "date": frappe.utils.today(),
        "document_no": sc.name,
        # "document_date": sc.transaction_date,
        "quantity": sc.total_qty,
        "unit": "Nos",
        # "type": "S&D: Sales Invoice/Transfer In",
        "type": "Job Order",
        "mode": "Land"
    }
