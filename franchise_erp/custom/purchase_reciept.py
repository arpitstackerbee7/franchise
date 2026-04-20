
import frappe
from frappe.utils import nowdate

def lock_serials_on_grn_submit(doc, method):
    for item in doc.items:
        if not item.purchase_order_item or not item.serial_no:
            continue

        # Fetch PO Item
        po_item = frappe.db.get_value("Purchase Order Item",item.purchase_order_item,
            ["custom_generated_serials","custom_used_serials"],as_dict=True)

        if not po_item or not po_item.custom_generated_serials:
            continue

        all_serials = set(s.strip()for s in po_item.custom_generated_serials.split("\n") if s.strip())

        used_existing = set(s.strip() for s in (po_item.custom_used_serials or "").split("\n") if s.strip())

        used_new = set(s.strip() for s in item.serial_no.split("\n") if s.strip())

        used_final = used_existing | used_new
        unused_final = all_serials - used_final

        frappe.db.set_value("Purchase Order Item",item.purchase_order_item,
            {"custom_used_serials": "\n".join(sorted(used_final)),"custom_unused_serials": "\n".join(sorted(unused_final))}
        )


def restore_serials_on_grn_cancel(doc, method):
    for item in doc.items:
        if item.purchase_order_item and item.serial_no:
            current_used = frappe.db.get_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials") or ""
            used_list = [s.strip() for s in current_used.split("\n") if s.strip()]
            to_remove = [s.strip() for s in item.serial_no.split("\n") if s.strip()]
            remaining = [s for s in used_list if s not in to_remove]
            frappe.db.set_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials", "\n".join(remaining))


# def on_submit(doc, method):
#     if not doc.custom_gate_entry:
#         return

#     gate_entry = frappe.get_doc("Gate Entry", doc.custom_gate_entry)

#     # 🔢 Current PR Total Qty
#     pr_total_qty = sum(item.qty for item in doc.items)

#     # ➕ Append new received row (NO CLEAR)
#     row = gate_entry.append("received_details", {})

#     # Purchase Receipt info
#     row.document_no = doc.name
#     row.document_date = doc.posting_date
#     row.item_qty = pr_total_qty
#     row.amounts = doc.total

#     # Gate Entry info
#     row.entry_no = gate_entry.name
#     row.entry_date = gate_entry.date
#     row.ge_qty = gate_entry.lr_quantity

#     # 🔢 Total Received Qty till now
#     total_received_qty = sum(
#         (d.item_qty or 0) for d in gate_entry.received_details
#     )

#     # 🔢 PO Total Qty
#     po_total_qty = 0
#     if gate_entry.purchase_order:
#         po = frappe.get_doc("Purchase Order", gate_entry.purchase_order)
#         po_total_qty = sum(item.qty for item in po.items)

#     # 🔄 Update Gate Entry Status
#     if total_received_qty >= po_total_qty:
#         gate_entry.status = "Fully Received"
#     else:
#         gate_entry.status = "Partially Received"

#     # 🔢 Optional cumulative fields
#     if hasattr(gate_entry, "total_qty"):
#         gate_entry.total_qty = total_received_qty

#     if hasattr(gate_entry, "total"):
#         gate_entry.total = sum(
#             (d.amounts or 0) for d in gate_entry.received_details
#         )

#     gate_entry.save(ignore_permissions=True)



def on_submit(doc, method):
    # 🔹 Collect all Gate Entry IDs from PR level and item level
    gate_entry_ids = set()

    if getattr(doc, "custom_gate_entry", None):
        gate_entry_ids.add(doc.custom_gate_entry)

    for item in doc.items:
        if getattr(item, "custom_bulk_gate_entry", None):
            gate_entry_ids.add(item.custom_bulk_gate_entry)

    # 🔹 Process each Gate Entry
    for ge_id in gate_entry_ids:
        gate_entry = frappe.get_doc("Gate Entry", ge_id)

        # 🔹 Current PR total qty for this Gate Entry
        pr_total_qty = 0
        for item in doc.items:
            if getattr(item, "custom_bulk_gate_entry", None) == ge_id:
                pr_total_qty += item.qty

        # If doc-level custom_gate_entry matches this ge_id, add full PR qty
        if getattr(doc, "custom_gate_entry", None) == ge_id:
            pr_total_qty += sum(item.qty for item in doc.items)

        # ➕ Append new received row if not already appended
        existing_row = next(
            (d for d in gate_entry.received_details if d.document_no == doc.name),
            None
        )

        if not existing_row:
            row = gate_entry.append("received_details", {})
            row.document_no = doc.name
            row.document_date = doc.posting_date
            row.item_qty = pr_total_qty
            row.amounts = doc.total
            row.entry_no = gate_entry.name
            row.entry_date = gate_entry.date
            row.ge_qty = gate_entry.lr_quantity

        # 🔢 Total Received Qty
        total_received_qty = sum(
            (d.item_qty or 0) for d in gate_entry.received_details
        )

        # 🔢 Optional cumulative fields
        if hasattr(gate_entry, "total_qty"):
            gate_entry.total_qty = total_received_qty

        if hasattr(gate_entry, "total"):
            gate_entry.total = sum(
                (d.amounts or 0) for d in gate_entry.received_details
            )

        gate_entry.save(ignore_permissions=True)


# @frappe.whitelist()
# def validate_po_serial(scanned_serial, po_items):
#     """
#     Validate scanned serial:
#     1. Must exist in custom_generated_serials
#     2. Must NOT exist in custom_used_serials
#     """

#     if isinstance(po_items, str):
#         po_items = frappe.parse_json(po_items)

#     for poi in po_items:
#         values = frappe.db.get_value(
#             "Purchase Order Item",
#             poi,
#             ["custom_generated_serials", "custom_used_serials"],
#             as_dict=True
#         )

#         if not values or not values.custom_generated_serials:
#             continue

#         generated_serials = [
#             s.strip() for s in values.custom_generated_serials.split("\n")
#             if s.strip()
#         ]

#         used_serials = [
#             s.strip() for s in (values.custom_used_serials or "").split("\n")
#             if s.strip()
#         ]

#         # ❌ Already used serial validation
#         if scanned_serial in used_serials:
#             frappe.throw(
#                 f"Duplicate scan detected. Serial No <b>{scanned_serial}</b> is already used"
#             )

#         # ✅ Valid serial
#         if scanned_serial in generated_serials:
#             return {
#                 "purchase_order_item": poi
#             }

#     # ❌ Serial not found in PO
#     frappe.throw(
#         f"Serial No <b>{scanned_serial}</b> does not exist in linked Purchase Order"
#     )

@frappe.whitelist()
def validate_po_serial(scanned_serial, po_items, is_return=0):

    if isinstance(po_items, str):
        po_items = frappe.parse_json(po_items)

    # Validate Serial exists
    # if not frappe.db.exists("Serial No", scanned_serial):
    #     frappe.throw(f"Invalid Serial No <b>{scanned_serial}</b>")

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

        # ==========================
        # 🔴 NORMAL PURCHASE
        # ==========================
        if not int(is_return):

            if scanned_serial in used_serials:
                frappe.throw(
                    f"Duplicate scan detected. Serial No <b>{scanned_serial}</b> already used"
                )

            if scanned_serial in generated_serials:
                return {
                    "purchase_order_item": poi
                }

        # ==========================
        # 🔵 RETURN PURCHASE (FIXED)
        # ==========================
        else:

            # ❗ STRICT CHECK ONLY IN GENERATED LIST
            if scanned_serial in generated_serials:
                return {
                    "purchase_order_item": poi
                }

    # ❌ Not found anywhere
    frappe.throw(
        f"Serial No <b>{scanned_serial}</b> does not belong to this Purchase Order"
    )

def validate_item(doc, method=None):
    # 🔹 Check if ANY row has PO
    po_present = any(row.purchase_order for row in doc.items)
    if not po_present:
        return

    for row in doc.items:
        if not row.purchase_order:
            continue  # skip rows without a PO

        # 🔴 PO Item must be linked to this PO
        if not row.purchase_order_item:
            frappe.throw(
                f"Row {row.idx}: Item <b>{row.item_code}</b> does not belong to "
                f"Purchase Order"
            )

        # Fetch PO Item details and parent PO
        po_item = frappe.db.get_value(
            "Purchase Order Item",
            row.purchase_order_item,
            ["parent", "qty", "received_qty"],
            as_dict=True
        )

        if not po_item:
            frappe.throw(
                f"Row {row.idx}: Invalid Purchase Order Item reference"
            )

        if po_item.parent != row.purchase_order:
            frappe.throw(
                f"Row {row.idx}: Item <b>{row.item_code}</b> does not belong to "
                f"Purchase Order <b>{row.purchase_order}</b>"
            )

        remaining_qty = (po_item.qty or 0) - (po_item.received_qty or 0)

        if row.qty > remaining_qty:
            frappe.throw(
                f"Row {row.idx}: Entered Qty <b>{row.qty}</b> exceeds "
                f"remaining PO Qty <b>{remaining_qty}</b>"
            )

# def assign_serials_from_po_on_submit(doc, method=None):
#     """
#     On submit of Purchase Receipt:
#     - Fetch serials from PO.custom_unused_serials
#     - If empty → fallback to PO.custom_generated_serials
#     - Assign serials based on qty
#     - Avoid duplicates & already scanned serials
#     """

#     for row in doc.items:

#         # 🔹 Skip if no PO item or qty
#         if not row.purchase_order_item or not row.qty:
#             continue

#         # 🔹 Fetch both fields
#         po_item = frappe.db.get_value(
#             "Purchase Order Item",
#             row.purchase_order_item,
#             ["custom_unused_serials", "custom_generated_serials"],
#             as_dict=True
#         )

#         if not po_item:
#             continue

#         # 🔹 Priority: unused → generated
#         if not po_item.custom_generated_serials:
#             return
            
#         source_serials = (
#             po_item.custom_unused_serials
#             or po_item.custom_generated_serials
#         )

#         if not source_serials:
#             frappe.throw(
#                 f"No serial numbers found in Purchase Order for item {row.item_code}"
#             )

#         po_serial_list = [
#             s.strip() for s in source_serials.split("\n") if s.strip()
#         ]

#         # 🔹 Already scanned serials in PR
#         existing_serials = []
#         if row.serial_no:
#             existing_serials = [
#                 s.strip() for s in row.serial_no.split("\n") if s.strip()
#             ]

#         # 🔹 Remove already used serials
#         available_serials = [
#             s for s in po_serial_list if s not in existing_serials
#         ]

#         # 🔹 Required serial count
#         required_qty = int(row.qty) - len(existing_serials)

#         if required_qty <= 0:
#             continue

#         # 🔹 Fetch required serials only
#         fetched_serials = available_serials[:required_qty]

#         if len(fetched_serials) < required_qty:
#             frappe.throw(
#                 f"Not enough serial numbers available in Purchase Order for item {row.item_code}"
#             )

#         # 🔹 Merge existing + fetched
#         final_serials = existing_serials + fetched_serials

#         row.serial_no = "\n".join(final_serials)

def assign_serials_from_po_on_submit(doc, method=None):
    """
    On submit of Purchase Receipt:
    - Fetch serials from PO.custom_unused_serials
    - If empty → fallback to PO.custom_generated_serials
    - Assign serials based on qty
    - Avoid duplicates & already scanned serials
    """

    for row in doc.items:

       
        item_doc = frappe.get_cached_doc("Item", row.item_code)

       
        if not item_doc.is_stock_item or not item_doc.has_serial_no:
            continue

        # 🔹 Skip if no PO item or qty
        if not row.purchase_order_item or not row.qty:
            continue

        # 🔹 Fetch both fields
        po_item = frappe.db.get_value(
            "Purchase Order Item",
            row.purchase_order_item,
            ["custom_unused_serials", "custom_generated_serials"],
            as_dict=True
        )

        if not po_item:
            continue

        # 🔹 Priority: unused → generated
        if not po_item.custom_generated_serials:
            continue
            
        source_serials = (
            po_item.custom_unused_serials
            or po_item.custom_generated_serials
        )

        if not source_serials:
            frappe.throw(
                f"No serial numbers found in Purchase Order for item {row.item_code}"
            )

        po_serial_list = [
            s.strip() for s in source_serials.split("\n") if s.strip()
        ]

        existing_serials = []
        if row.serial_no:
            existing_serials = [
                s.strip() for s in row.serial_no.split("\n") if s.strip()
            ]

        available_serials = [
            s for s in po_serial_list if s not in existing_serials
        ]

        required_qty = int(row.qty) - len(existing_serials)

        if required_qty <= 0:
            continue

        fetched_serials = available_serials[:required_qty]

        if len(fetched_serials) < required_qty:
            frappe.throw(
                f"Not enough serial numbers available in Purchase Order for item {row.item_code}"
            )

        final_serials = existing_serials + fetched_serials
        row.serial_no = "\n".join(final_serials)
     

def on_cancel(doc, method):
    # 🔹 Collect all Gate Entry IDs from PR level and item level
    gate_entry_ids = set()

    if getattr(doc, "custom_gate_entry", None):
        gate_entry_ids.add(doc.custom_gate_entry)

    for item in doc.items:
        if getattr(item, "custom_bulk_gate_entry", None):
            gate_entry_ids.add(item.custom_bulk_gate_entry)

    # 🔹 Process each Gate Entry
    for ge_id in gate_entry_ids:
        gate_entry = frappe.get_doc("Gate Entry", ge_id)

        # 🔥 Remove only THIS PR related rows from received_details
        gate_entry.received_details = [
            d for d in gate_entry.received_details
            if d.document_no != doc.name
        ]

        # 🔢 Total received qty after removal
        total_received_qty = sum(
            (d.item_qty or 0) for d in gate_entry.received_details
        )

        # 🔢 Optional cumulative fields
        if hasattr(gate_entry, "total_qty"):
            gate_entry.total_qty = total_received_qty

        if hasattr(gate_entry, "total"):
            gate_entry.total = sum(
                (d.amounts or 0) for d in gate_entry.received_details
            )

        gate_entry.save(ignore_permissions=True)



# @frappe.whitelist()
# def get_item_by_barcode(barcode):
#     """Return item_code for a barcode"""
#     if not barcode:
#         return None
#     item = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
#     if not item:
#         return None
#     return {"item_code": item}


import frappe

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



# def fix_pr_totals(doc, method):
#     if not doc.custom_source_sales_invoice:
#         return

#     si = frappe.get_doc("Sales Invoice", doc.custom_source_sales_invoice)

#     for pr_item in doc.items:
#         si_item = next(
#             (i for i in si.items if i.item_code == pr_item.item_code),
#             None
#         )
#         if not si_item:
#             continue

#         rate = si_item.net_rate or si_item.rate
#         pr_item.rate = rate
#         pr_item.price_list_rate = rate
#         pr_item.net_rate = rate

#     doc.calculate_taxes_and_totals()
def fix_pr_totals(doc, method):
    if not doc.custom_source_sales_invoice:
        return

    doc.flags.ignore_validate_update_after_submit = True

    si = frappe.get_doc("Sales Invoice", doc.custom_source_sales_invoice)

    # ---------------- ITEM RATE FIX ----------------
    for pr_item in doc.items:
        si_item = next(
            (i for i in si.items if i.item_code == pr_item.item_code),
            None
        )
        if not si_item:
            continue

        rate = si_item.net_rate or si_item.rate

        frappe.db.set_value(
            "Purchase Receipt Item",
            pr_item.name,
            {
                "rate": rate,
                "price_list_rate": rate,
                "net_rate": rate
            }
        )

    doc.calculate_taxes_and_totals()

    # ---------------- TOTAL INPUT GST ----------------
    total_gst = 0
    for tax in doc.taxes:
        if tax.account_head and "Input" in tax.account_head:
            total_gst += tax.tax_amount or 0

    if not total_gst or not doc.net_total:
        return

    # ---------------- UPDATE CUSTOM FIELDS ----------------
    for item in doc.items:
        single_rate = item.net_rate

        item_gst = (item.net_amount / doc.net_total) * total_gst
        single_item_gst = round(item_gst / item.qty, 2)

        frappe.db.set_value(
            "Purchase Receipt Item",
            item.name,
            {
                "custom_single_item_rate": single_rate,
                "custom_single_item_input_gst_amount": single_item_gst
            }
        )
    # ======================================================
    # 4️⃣ AFTER GRN SUBMIT → UPDATE SALES INVOICE CHECKBOX ✅
    # ======================================================
    if doc.docstatus == 1:
        frappe.db.set_value(
            "Sales Invoice",
            si.name,
            "custom_is_received_grn",
            1
        )
    frappe.db.commit()



# def validate_gate_entry(doc, method):
#     if not doc.supplier:
#         return

#     # Supplier gate entry flag
#     gate_required = frappe.db.get_value(
#         "Supplier",
#         doc.supplier,
#         "custom_gate_entry"
#     )

#     # Agar supplier ke liye gate entry required nahi
#     if not gate_required:
#         return

#     # Items check
#     for row in doc.items:
#         if not row.custom_bulk_gate_entry:
#             frappe.throw(
#                 "First create Gate Entry, then Purchase Receipt can be saved."
#             )
import frappe

def validate_gate_entry(doc, method):
    # Supplier mandatory check
    if not doc.supplier:
        return

    # 🔹 IF Source Sales Invoice present → allow save
    if doc.custom_source_sales_invoice:
        return
    if doc.is_subcontracted:
        return
    # Gate Entry not required for purchase return
    if doc.is_return ==1:
        return
    # Supplier gate entry flag
    gate_required = frappe.db.get_value(
        "Supplier",
        doc.supplier,
        "custom_gate_entry"
    )
    # Agar supplier ke liye gate entry required nahi
    if not gate_required:
        return

    # Items check
    for row in doc.items:
        pass
        # if not row.custom_bulk_gate_entry:
        #     frappe.throw(
        #         "First create Gate Entry, then Purchase Receipt can be saved."
        #     )


from frappe import _

def validate_gate_entry_qty_on_grn(doc, method):
     # 🚫 Skip validation for Return Purchase Receipt
    if doc.is_return:
        return
    for item in doc.items:

        gate_entry = item.custom_bulk_gate_entry
        if not gate_entry:
            continue

        # 1️⃣ Get Invoice Qty from Gate Entry
        invoice_qty = frappe.db.get_value(
            "Gate Entry",
            gate_entry,
            "quantity_as_per_invoice"
        ) or 0

        if invoice_qty <= 0:
            frappe.throw(
                _("Quantity as per invoice is zero for Gate Entry {0}. GRN cannot be created.")
                .format(gate_entry)
            )

        # 2️⃣ Already received qty from previous GRNs
        already_grn_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(pri.qty), 0) AS total_qty
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pri.custom_bulk_gate_entry = %s
            AND pr.docstatus = 1
            AND pr.name != %s
        """, (gate_entry, doc.name), as_dict=1)[0]["total_qty"]

        remaining_qty = invoice_qty - already_grn_qty

        # 3️⃣ If nothing left
        if remaining_qty <= 0:
            frappe.throw(
                _("All quantity as per invoice has already been received for Gate Entry {0}.")
                .format(gate_entry)
            )

        # 4️⃣ If user enters more than remaining
        if item.qty > remaining_qty:
            frappe.throw(
                _("Only {0} quantity is remaining as per invoice for Gate Entry {1}.")
                .format(remaining_qty, gate_entry)
            )


import frappe

@frappe.whitelist()
def get_purchase_receipt_city(purchase_receipt):
    pr = frappe.get_doc("Purchase Receipt", purchase_receipt)

    # 1️⃣ Shipping Address (priority)
    if pr.shipping_address:
        city = frappe.db.get_value(
            "Address",
            pr.shipping_address,
            "custom_citytown"
        )
        if city:
            return city

    # 2️⃣ Billing Address (fallback)
    if pr.billing_address:
        city = frappe.db.get_value(
            "Address",
            pr.billing_address,
            "custom_citytown"
        )
        if city:
            return city

    return None


def clear_si_grn_flags(doc, method):

    if not doc.custom_source_sales_invoice:
        return

    frappe.db.set_value(
        "Sales Invoice",
        doc.custom_source_sales_invoice,
        {
            "custom_is_draft_grn": 0,
            "custom_is_received_grn": 0
        }
    )

# def create_debit_note_from_pr(doc, method):
#     """Create Purchase Invoice (Debit Note) directly from Purchase Receipt Return"""

#     if not doc.is_return:
#         return

#     if not doc.custom_bulk_purchase_return:
#          return
    
#     if not doc.items:
#         return

#     # 🔹 Create Purchase Invoice
#     pi = frappe.new_doc("Purchase Invoice")

#     # 🔹 Set header fields
#     pi.is_return = 1
#     pi.company = doc.company
#     pi.supplier = doc.supplier
#     pi.update_billed_amount_in_purchase_receipt = 1
#     pi.posting_date = doc.posting_date
#     pi.posting_time = doc.posting_time
#     pi.currency = doc.currency
#     pi.conversion_rate = doc.conversion_rate

#     pi.bill_no= "RRR"
#     pi.bill_date = nowdate()

#     # 🔥 Add items from Purchase Receipt
#     for pr_item in doc.items:

#         if not pr_item.qty:
#             continue

#         pi.append("items", {
#             "item_code": pr_item.item_code,
#             "item_name": pr_item.item_name,
#             "description": pr_item.description,
#             "uom": pr_item.uom,
#             "stock_uom": pr_item.stock_uom,

#             # 🔥 Negative qty for return
#             "qty": -abs(pr_item.qty),
#             "received_qty": -abs(pr_item.qty),
            

#             "rate": pr_item.rate,
#             "base_rate": pr_item.base_rate,

#             # 🔗 Important links
#             "purchase_receipt": doc.name,
#             "pr_detail": pr_item.name,
#             "purchase_order": pr_item.purchase_order,

#             "item_tax_template": pr_item.item_tax_template,
#             # Stock fields
#             "warehouse": pr_item.warehouse,

#             # Amounts
#             "amount": -abs(pr_item.amount),
#             "base_amount": -abs(pr_item.base_amount),
#         })

#     # 🔹 Insert (you can submit if needed)
#     pi.set_missing_values()
#     pi.insert(ignore_permissions=True)

#     frappe.msgprint(f"✅ Debit Note Created: {pi.name}")