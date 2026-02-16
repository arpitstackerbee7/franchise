import frappe

#for 2 get 1 free item
def set_promo_group_id(doc, method=None):
    # Agar koi free item hi nahi hai → koi promo nahi
    has_free_item = any(item.is_free_item for item in doc.items)

    if not has_free_item:
        return

    for item in doc.items:
        # ✅ Sirf PAID items par checkbox set hoga
        if not item.is_free_item and item.rate > 0:
            item.custom_is_promo_scheme = 1   # CHECKBOX ✅


#for 2 buy 1 item discount like 20%

def set_percent_off_promo_flags(doc, method=None):
    discounted_items = []

    for item in doc.items:
        if (
            item.price_list_rate
            and item.rate
            and item.rate < item.price_list_rate
        ):
            discounted_items.append(item)

    if not discounted_items:
        return

    for item in doc.items:
        if item.rate > 0:
            item.db_set("custom_is_promo_scheme", 1)
            item.db_set("custom_promo_discount_percent", 0)

    for item in discounted_items:
        discount_percent = round(
            (1 - (item.rate / item.price_list_rate)) * 100,
            2
        )
        item.db_set("custom_promo_discount_percent", discount_percent)



def set_dn_naming_series(doc, method):
    if doc.is_return:
        doc.naming_series = "DRET-.YY.-"
    else:
        doc.naming_series = "DN-.YY.-"


def disable_eway_notification(doc, method):
    # Agar E-Way bilkul nahi chahiye
    doc.ewaybill = None
    doc.ewaybill_validity = None
    doc.transport_mode = None
    doc.vehicle_no = None
    doc.distance = 0
    doc.gst_transporter_id = None

def set_sales_person(doc, method=None):

    user = frappe.session.user

    sales_person = frappe.db.get_value(
        "Sales Person",
        {"custom_user": user},
        ["name", "commission_rate", "custom_commission_amount"],
        as_dict=True
    )

    if not sales_person:
        return

    # 🔹 Clear entire sales_team table
    doc.set("sales_team", [])

    # 🔹 Append fresh controlled row
    doc.append("sales_team", {
        "sales_person": sales_person.name,
        "allocated_percentage": 100,
        "commission_rate": sales_person.commission_rate or 0,
        "incentives": sales_person.custom_commission_amount or 0
    })