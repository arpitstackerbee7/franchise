import frappe

@frappe.whitelist()
def get_barcode_data(barcode, is_serialized_mode):
    # Convert string/boolean to integer (1 or 0)
    is_serialized_mode = int(is_serialized_mode)
    barcode = barcode.strip()

    # 1. Check if it's a Serial Number
    serial_info = frappe.db.get_value(
        "Serial No", barcode,
        ["item_code", "name"],
        as_dict=1
    )

    # ==============================
    # 🔹 MODE: SERIALIZED (Checked)
    # ==============================
    if is_serialized_mode == 1:
        if not serial_info:
            frappe.throw(
                f"Barcode '{barcode}' is NOT a valid Serial Number. "
                f"Please switch off 'Is Serialized' to scan as a normal item."
            )

        item_doc = frappe.get_cached_doc("Item", serial_info.item_code)
        
        return {
            "item_code": item_doc.name,
            "serial_no": barcode,
            "design_no": item_doc.get("custom_sup_design_no") or "",
            "is_serialized": 1,
            "qty": 1  # Default qty
        }

    # ==============================
    # 🔹 MODE: NON-SERIALIZED (Unchecked)
    # ==============================
    else:
        # User is trying to scan a Serial No in Non-Serialized mode
        if serial_info:
            frappe.throw(
                f"'{barcode}' is a Serial Number. Please turn ON 'Is Serialized' mode to scan this."
            )

        # Find Item by Code or Barcode
        item_code = frappe.db.get_value("Item", {"name": barcode}, "name")
        if not item_code:
            item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")

        if not item_code:
            frappe.throw(f"Item or Barcode '{barcode}' not found in the system.")

        item_doc = frappe.get_cached_doc("Item", item_code)

        # Safety Check: If item is actually a serialized item, don't allow scanning in non-serialized mode
        if item_doc.has_serial_no:
            frappe.throw(
                f"Item '{item_code}' requires a Serial Number. Please turn ON 'Is Serialized' mode."
            )

        return {
            "item_code": item_doc.name,
            "serial_no": "-",
            "design_no": item_doc.get("custom_sup_design_no") or "",
            "is_serialized": 0,
            "qty": 1
        }