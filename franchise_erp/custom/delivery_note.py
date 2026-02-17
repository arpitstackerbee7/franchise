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


def apply_sales_person_rules(doc, method=None):

    if not doc.company:
        return

    # Properly clear child table
    doc.set("sales_team", [])

    sales_persons = frappe.get_all(
        "Sales Person",
        filters={
            "custom_company": doc.company,
            "enabled": 1
        },
        fields=["name", "custom_apply_on"]
    )

    if not sales_persons:
        return

    item_codes = {d.item_code for d in doc.items}
    item_groups = {d.item_group for d in doc.items}

    matched_sales_persons = {}
    total_amount = doc.base_net_total or doc.net_total or 0

    for sp in sales_persons:
        sp_doc = frappe.get_doc("Sales Person", sp.name)

        # -------------------------
        # Apply on Item Code
        # -------------------------
        if sp.custom_apply_on == "Item Code":
            for rule in sp_doc.custom_sales_person_item_rule:
                if rule.item in item_codes:
                    matched_sales_persons[sp.name] = {
                        "commission_rate": rule.commission_rate or 0,
                        "commission_amount": rule.commission_amount or 0
                    }
                    break

        # -------------------------
        # Apply on Item Group
        # -------------------------
        elif sp.custom_apply_on == "Item Group":
            for rule in sp_doc.custom_sales_person_item_group_rule:
                if rule.item_group in item_groups:
                    matched_sales_persons[sp.name] = {
                        "commission_rate": rule.commission_rate or 0,
                        "commission_amount": rule.commission_amount or 0
                    }
                    break

    if not matched_sales_persons:
        return

    sales_person_list = list(matched_sales_persons.keys())
    total_persons = len(sales_person_list)

    equal_percentage = round(100 / total_persons, 2)
    total_allocated_percentage = 0

    for i, sp_name in enumerate(sales_person_list):

        if i == total_persons - 1:
            allocated_percentage = 100 - total_allocated_percentage
        else:
            allocated_percentage = equal_percentage
            total_allocated_percentage += allocated_percentage

        commission_rate = matched_sales_persons[sp_name]["commission_rate"]
        commission_amount = matched_sales_persons[sp_name]["commission_amount"]

        # ✅ Calculate allocated amount
        allocated_amount = (total_amount * allocated_percentage) / 100

        # ✅ Incentive Logic
        if commission_rate:
            incentives = (allocated_amount * commission_rate) / 100
        else:
            incentives = commission_amount

        doc.append("sales_team", {
            "sales_person": sp_name,
            "commission_rate": commission_rate,
            "allocated_percentage": allocated_percentage,
            "allocated_amount": allocated_amount,
            "incentives": incentives
        })