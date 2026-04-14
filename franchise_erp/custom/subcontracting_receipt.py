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


import frappe


@frappe.whitelist()
def get_po_item_qty(po_item):

    if not po_item:
        return 0

    # ignore permissions
    qty = frappe.db.get_value(
        "Purchase Order Item",
        po_item,
        "qty"
    )

    return qty or 0



import frappe

def assign_fifo_serials(doc, method):

    for row in doc.items:

        # -------------------------
        # CHECK SERIALIZED ITEM
        # -------------------------
        is_serialized = frappe.db.get_value("Item", row.item_code, "has_serial_no")

        if not is_serialized:
            continue

        if not row.purchase_order_item:
            frappe.throw(f"PO Item missing for {row.item_code}")

        # -------------------------
        # GET PO DATA
        # -------------------------
        values = frappe.db.get_value(
            "Purchase Order Item",
            row.purchase_order_item,
            [
                "custom_generated_serials",
                "custom_used_serials",
                "custom_unused_serials"
            ],
            as_dict=True
        )

        if not values or not values.custom_generated_serials:
            frappe.throw(f"No serials found in PO for Item {row.item_code}")

        generated = [
            s.strip() for s in values.custom_generated_serials.split("\n")
            if s.strip()
        ]

        used = [
            s.strip() for s in (values.custom_used_serials or "").split("\n")
            if s.strip()
        ]

        # -------------------------
        # AGAR USER NE SERIAL DIYA → USE SAME
        # -------------------------
        if row.serial_no:
            selected = [
                s.strip() for s in row.serial_no.split("\n") if s.strip()
            ]
        else:
            # -------------------------
            # FIFO AUTO PICK
            # -------------------------
            available = [s for s in generated if s not in used]

            required_qty = int(row.qty or 0)

            if len(available) < required_qty:
                frappe.throw(
                    f"Not enough serials available in PO for Item {row.item_code}"
                )

            selected = available[:required_qty]

            row.serial_no = "\n".join(selected)

        # -------------------------
        # UPDATE USED SERIALS
        # -------------------------
        updated_used = list(set(used + selected))

        # -------------------------
        # CALCULATE UNUSED SERIALS
        # -------------------------
        updated_unused = [s for s in generated if s not in updated_used]

        # -------------------------
        # SAVE BACK TO PO ITEM
        # -------------------------
        frappe.db.set_value(
            "Purchase Order Item",
            row.purchase_order_item,
            {
                "custom_used_serials": "\n".join(updated_used),
                "custom_unused_serials": "\n".join(updated_unused)
            }
        )

def restore_serials_on_cancel(doc, method):
    """
    Jab Subcontracting Receipt cancel hogi, toh usme use huye serials 
    wapas PO Item ke list mein free ho jayenge.
    """
    for row in doc.items:
        # Check karein ki PO link hai aur serial numbers hain
        if row.purchase_order_item and row.serial_no:
            
            # Purchase Order Item se purana data fetch karein
            po_data = frappe.db.get_value(
                "Purchase Order Item",
                row.purchase_order_item,
                ["custom_generated_serials", "custom_used_serials"],
                as_dict=True
            )

            if not po_data:
                continue

            # Serials ko sets mein convert karein logic easy karne ke liye
            generated = set(s.strip() for s in (po_data.custom_generated_serials or "").split("\n") if s.strip())
            used = set(s.strip() for s in (po_data.custom_used_serials or "").split("\n") if s.strip())
            
            # Current document (jo cancel ho raha hai) ke serials
            current_serials = set(s.strip() for s in row.serial_no.split("\n") if s.strip())

            # Used list se ye serials hata dein
            updated_used = used - current_serials
            
            # Jo used nahi hain wo sab Unused hain
            updated_unused = generated - updated_used

            # Database update karein
            frappe.db.set_value(
                "Purchase Order Item",
                row.purchase_order_item,
                {
                    "custom_used_serials": "\n".join(sorted(list(updated_used))),
                    "custom_unused_serials": "\n".join(sorted(list(updated_unused)))
                }
            )


import frappe
from frappe import _

def validate_gate_entry_qty_on_subcontracting(doc, method):
    if doc.is_return:
        return

    # ✅ Gate Entry Parent se lo
    gate_entry = doc.custom_gate_entry
    if not gate_entry:
        return

    # Total Invoice Qty
    invoice_qty = frappe.db.get_value(
        "Gate Entry",
        gate_entry,
        "quantity_as_per_invoice"
    ) or 0

    # Already Used Qty
    used_qty = frappe.db.sql("""
        SELECT IFNULL(SUM(sri.qty), 0)
        FROM `tabSubcontracting Receipt Item` sri
        JOIN `tabSubcontracting Receipt` sr ON sr.name = sri.parent
        WHERE sr.custom_gate_entry = %s
        AND sr.docstatus = 1
        AND sr.name != %s
    """, (gate_entry, doc.name))[0][0] or 0

    remaining_qty = invoice_qty - used_qty

    # 🚨 FULLY USED BLOCK
    if remaining_qty <= 0:
        frappe.throw(
            _("Gate Entry {0} already fully used. Remaining qty is 0.")
            .format(gate_entry)
        )

    # 🚨 Qty validation
    total_qty = sum([item.qty for item in doc.items])

    if total_qty > remaining_qty:
        frappe.throw(
            _("Only {0} total qty allowed for Gate Entry {1}")
            .format(remaining_qty, gate_entry)
        )
# ✅ DROPDOWN FILTER METHOD
@frappe.whitelist()
def get_available_gate_entries(doctype, txt, searchfield, start, page_len, filters):

    return frappe.db.sql("""
        SELECT ge.name
        FROM `tabGate Entry` ge
        LEFT JOIN (
            SELECT sri.custom_gate_entry, SUM(sri.qty) as used_qty
            FROM `tabSubcontracting Receipt Item` sri
            JOIN `tabSubcontracting Receipt` sr ON sr.name = sri.parent
            WHERE sr.docstatus = 1
            GROUP BY sri.custom_gate_entry
        ) used ON used.custom_gate_entry = ge.name

        WHERE ge.docstatus = 1
        AND (ge.quantity_as_per_invoice - IFNULL(used.used_qty, 0)) > 0
        AND ge.name LIKE %s

        LIMIT %s, %s
    """, ("%{}%".format(txt), start, page_len))





