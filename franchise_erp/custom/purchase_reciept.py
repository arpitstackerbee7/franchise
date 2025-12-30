
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