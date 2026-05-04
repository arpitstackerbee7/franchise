import frappe
from frappe.model.naming import make_autoname
import re
from datetime import datetime
from frappe.utils import nowdate

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



def set_dn_naming_series(doc, method=None):

    # Clean abbreviation (allow only letters & numbers)
    abbr = re.sub(r"[^A-Za-z0-9]", "", doc.custom_abbr or "")

    # ✅ Get Financial Year (26-27)
    fy = frappe.defaults.get_user_default("fiscal_year")

    if fy and "-" in fy:
        start, end = fy.split("-")
        fy_code = f"{start[-2:]}-{end[-2:]}"
    else:
        year = datetime.now().year
        fy_code = f"{str(year)[-2:]}-{str(year+1)[-2:]}"

    # ✅ Apply FY to ALL series
    if doc.is_return:
        series = f"DRET-{abbr}-{fy_code}-"
    elif abbr:
        series = f"DN-{abbr}-{fy_code}-"
    else:
        series = f"DN-{fy_code}-"

    doc.naming_series = series
    
# def set_dn_naming_series(doc, method):
#     if doc.is_return:
#         doc.naming_series = "DRET-.YY.-"
#     else:
#         doc.naming_series = "DN-.YY.-"


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




@frappe.whitelist()
def get_delivery_note_by_serial(serial):

    if not serial:
        return []

    invoices = frappe.db.sql("""
        SELECT DISTINCT parent
        FROM `tabDelivery Note Item`
        WHERE serial_no LIKE %s
    """, ("%" + serial + "%"))

    return [d[0] for d in invoices]


def create_credit_note_from_dn(doc, method):
    """Create Sales Invoice (Credit Note) from Delivery Note Return"""

    if not doc.is_return:
        return
    if not doc.custom_bulk_sales_return:
        return
    if not doc.items:
        return

    # 🔹 Create Sales Invoice
    si = frappe.new_doc("Sales Invoice")

    # 🔹 Header fields
    si.is_return = 1
    si.company = doc.company
    si.customer = doc.customer
    si.update_billed_amount_in_delivery_note = 1
    si.posting_date = doc.posting_date
    si.posting_time = doc.posting_time
    si.currency = doc.currency
    si.conversion_rate = doc.conversion_rate
    si.update_stock = 0

    # 🔥 Add items
    for dn_item in doc.items:

        if not dn_item.qty:
            continue

        si.append("items", {
            "item_code": dn_item.item_code,
            "item_name": dn_item.item_name,
            "description": dn_item.description,
            "uom": dn_item.uom,
            "stock_uom": dn_item.stock_uom,

            # 🔥 Negative qty
            "qty": -abs(dn_item.qty),
            "stock_qty": -abs(dn_item.qty),

            "rate": dn_item.rate,
            "base_rate": dn_item.base_rate,

            # 🔗 Links
            "delivery_note": doc.name,
            "dn_detail": dn_item.name,
            "sales_order": dn_item.against_sales_order,

            "warehouse": dn_item.warehouse,
            "item_tax_template": dn_item.item_tax_template,
            # Amount
            "amount": -abs(dn_item.amount),
            "base_amount": -abs(dn_item.base_amount),
        })
    si.set_missing_values()
    si.insert(ignore_permissions=True)

    frappe.msgprint(f"✅ Credit Note Created: {si.name}")