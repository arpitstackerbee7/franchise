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


# def apply_purchase_term(doc, method):
#     if not doc.custom_purchase_term:
#         return

#     term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

#     for item in doc.items:
#         if not item.custom_original_rate:
#             item.custom_original_rate = item.rate

#         rate = item.custom_original_rate

#         for row in sorted(term.charges, key=lambda x: x.seq):
#             if row.charge_type == "Rate Diff":
#                 rate += row.value

#             elif row.charge_type == "Discount":
#                 rate -= (rate * row.value / 100)

#         item.rate = rate
#         item.amount = rate * item.qty
#         item.net_amount = item.amount