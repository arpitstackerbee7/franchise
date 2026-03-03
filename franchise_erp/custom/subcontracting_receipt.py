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



@frappe.whitelist()
def get_item_by_barcode(barcode):
    """Return item_code for a barcode"""
    if not barcode:
        return None

    item = frappe.db.get_value(
        "Item Barcode",
        {"barcode": barcode},
        "parent"
    )

    if not item:
        return None

    return {"item_code": item}

 

@frappe.whitelist()
def validate_po_serial(scanned_serial, po_items):
    """
    Validate scanned serial:
    1. Must exist in custom_generated_serials
    2. Must NOT exist in custom_used_serials
    """

    if isinstance(po_items, str):
        po_items = frappe.parse_json(po_items)

    for poi in po_items:
        values = frappe.db.get_value(
            "Purchase Order Item",
            poi,
            ["custom_generated_serials", "custom_used_serials"],
            as_dict=True
        )

        if not values or not values.custom_generated_serials:
            continue

        generated_serials = [
            s.strip() for s in values.custom_generated_serials.split("\n")
            if s.strip()
        ]

        used_serials = [
            s.strip() for s in (values.custom_used_serials or "").split("\n")
            if s.strip()
        ]

        # ❌ Already used serial validation
        if scanned_serial in used_serials:
            frappe.throw(
                f"Duplicate scan detected. Serial No <b>{scanned_serial}</b> is already used"
            )

        # ✅ Valid serial
        if scanned_serial in generated_serials:
            return {
                "purchase_order_item": poi
            }

    # ❌ Serial not found in PO
    frappe.throw(
        f"Serial No <b>{scanned_serial}</b> does not exist in linked Purchase Order"
    )
