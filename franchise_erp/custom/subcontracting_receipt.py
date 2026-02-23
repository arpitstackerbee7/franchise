import frappe

@frappe.whitelist()
def create_incoming_logistics_from_scr(subcontracting_receipt):
    scr = frappe.get_doc("Subcontracting Receipt", subcontracting_receipt)

    il = frappe.new_doc("Incoming Logistics")

    # --- Reference ---
    il.reference_doctype = "Subcontracting Receipt"
    il.invoice_no = scr.name
    il.type = "Job Receipt"
    # --- Dates & Mode ---
    il.mode = scr.mode_of_transport or "Road"
    il.lr_date = scr.lr_date
    il.invoice_date = scr.posting_date
    il.date = scr.posting_date

    # --- Parties ---
    il.consignor = scr.supplier
    il.owner_site = scr.company

    # 🔥 Supplier → custom_transporter → Incoming Logistics.transporter
    if scr.supplier:
        supplier = frappe.get_doc("Supplier", scr.supplier)
        il.transporter = supplier.custom_transporter

    # --- Items mapping ---
    for item in scr.items:
        row = il.append("purchase_ids", {})
        row.purchase_doctype = "Subcontracting Receipt"
        row.purchase_docname = scr.name
        row.item_code = item.item_code
        row.qty = item.qty
        row.warehouse = item.warehouse

    return il.as_dict()
