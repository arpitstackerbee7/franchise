
import frappe

def assign_serials_to_grn(doc, method):
    for item in doc.items:
        if item.purchase_order_item and not item.serial_no:
            po_item = frappe.get_doc("Purchase Order Item", item.purchase_order_item)
            
            if not po_item.custom_generated_serials:
                continue

            all_serials = [s.strip() for s in po_item.custom_generated_serials.split("\n") if s.strip()]
            used_serials = [s.strip() for s in (po_item.custom_used_serials or "").split("\n") if s.strip()]
            
            available = [s for s in all_serials if s not in used_serials]
            
            qty = int(item.qty)
            if qty > len(available):
                frappe.throw(f"Row {item.idx}: Only {len(available)} serial numbers are remaining in the Purchase Order.")


            selected = available[:qty]
            item.serial_no = "\n".join(selected)

def lock_serials_on_grn_submit(doc, method):
    for item in doc.items:
        if item.purchase_order_item and item.serial_no:
            current_used = frappe.db.get_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials") or ""
            new_list = (current_used.split("\n") if current_used else []) + item.serial_no.split("\n")
            updated_used = "\n".join([s.strip() for s in new_list if s.strip()])
            frappe.db.set_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials", updated_used)

def restore_serials_on_grn_cancel(doc, method):
    for item in doc.items:
        if item.purchase_order_item and item.serial_no:
            current_used = frappe.db.get_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials") or ""
            used_list = [s.strip() for s in current_used.split("\n") if s.strip()]
            to_remove = [s.strip() for s in item.serial_no.split("\n") if s.strip()]
            remaining = [s for s in used_list if s not in to_remove]
            frappe.db.set_value("Purchase Order Item", item.purchase_order_item, "custom_used_serials", "\n".join(remaining))

def on_submit(doc, method):
    if not doc.custom_gate_entry:
        return

    gate_entry = frappe.get_doc("Gate Entry", doc.custom_gate_entry)

    # Clear old rows
    gate_entry.received_details = []

    for item in doc.items:
        row = gate_entry.append("received_details", {})

        # Purchase Receipt info
        row.document_no = doc.name
        row.document_date = doc.posting_date
        row.item_qty = item.qty

        # Map PR total to Gate Entry amounts
        row.amounts = doc.total  # total from Purchase Receipt

        # Gate Entry mapping
        row.entry_no = gate_entry.name    # ✅ This is a string like TPL-GE-00029-2025-2026
        row.entry_date = gate_entry.date
        row.ge_qty = gate_entry.lr_quantity

    # Optional: update header fields in Gate Entry
    if hasattr(gate_entry, "total_qty"):
        gate_entry.total_qty = sum([i.qty for i in doc.items])

    if hasattr(gate_entry, "total"):
        gate_entry.total = doc.total

    gate_entry.save(ignore_permissions=True)