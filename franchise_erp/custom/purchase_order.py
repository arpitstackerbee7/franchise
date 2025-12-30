import frappe
from frappe.model.naming import make_autoname

def generate_serials_on_po_submit(doc, method):
    """PO Submit par Item Series ya Item Code ke hisaab se serial generate karna"""
    for item in doc.items:

        item_info = frappe.db.get_value("Item", item.item_code, ["has_serial_no", "serial_no_series"], as_dict=True)
        
        if item_info and item_info.has_serial_no:
            generated = []
            
            series_prefix = item_info.serial_no_series if item_info.serial_no_series else f"{item.item_code}-.#####"
            
            for i in range(int(item.qty)):
                sn = make_autoname(series_prefix)
                generated.append(sn)
            
            
            item.custom_generated_serials = "\n".join(generated)
            frappe.db.set_value("Purchase Order Item", item.name, "custom_generated_serials", item.custom_generated_serials)


def validate_purchase_order(doc, method):

    if doc.custom_agent_supplier and doc.custom_agent_supplier != doc.supplier:
        pass  # allowed

    if doc.custom_transporter and doc.custom_transporter != doc.supplier:
        pass  # allowed           