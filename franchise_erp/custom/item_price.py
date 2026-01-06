import frappe

def validate_item_price(doc, method):

    # Sirf Inter price list par kaam kare
    if doc.price_list != "Inter":
        return

    target_price_list = "Standard Selling"

    # Agar Standard Selling pehle se exist karta hai to error
    exists = frappe.db.exists(
        "Item Price",
        {
            "item_code": doc.item_code,
            "price_list": target_price_list,
            "uom": doc.uom
        }
    )
    

    if exists:
        frappe.throw(
            f"Item Price already exists for <b>{target_price_list}</b>",
            title="Duplicate Item Price"
        )

    # SAME PRICE copy karke Standard Selling banana
    ip = frappe.new_doc("Item Price")
    ip.item_code = doc.item_code
    ip.price_list = target_price_list
    ip.uom = doc.uom
    ip.currency = doc.currency
    ip.price_list_rate = doc.price_list_rate   # SAME RATE
    ip.valid_from = doc.valid_from
    ip.valid_upto = doc.valid_upto

    ip.selling = 1
    ip.buying = 0

    ip.insert(ignore_permissions=True)
