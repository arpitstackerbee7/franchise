import frappe

@frappe.whitelist()
def get_barcode_data(barcode, item_type):
    # Check Master Serial No table
    serial_info = frappe.db.get_value("Serial No", barcode, ["item_code", "name"], as_dict=1)
    
    if item_type == "Serial No":
        if not serial_info:
            frappe.throw(f"Invalid scan! '{barcode}' is NOT a Serial Number. Please use 'Non Serial No' mode for Item Codes.")
            
        item_doc = frappe.get_cached_doc("Item", serial_info.item_code)
        return {
            "item_code": item_doc.name,
            "serial_no": barcode,
            "design_no": item_doc.get("custom_sup_design_no") or "",
            "is_serialized": 1,
            "qty": 1
        }
    
    else: # Mode: Non Serial No
        if serial_info:
            frappe.throw(f"Invalid scan! '{barcode}' is a Serial Number. Please use 'Serial No' mode.")
        
        item_code = frappe.db.get_value("Item", {"name": barcode}, "name")
        if not item_code:
            item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
            
        if item_code:
            item_doc = frappe.get_cached_doc("Item", item_code)
            if item_doc.has_serial_no:
                frappe.throw(f"Item '{item_code}' is serialized. Please use 'Serial No' mode.")
            
            return {
                "item_code": item_doc.name,
                "serial_no": "-", # Center-aligned dash
                "design_no": item_doc.get("custom_sup_design_no") or "",
                "is_serialized": 0,
                "qty": 1
            }
            
    frappe.throw(f"Barcode '{barcode}' not found.")