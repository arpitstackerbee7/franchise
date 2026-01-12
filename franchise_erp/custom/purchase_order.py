import frappe
from frappe.model.naming import make_autoname

def generate_serials_on_po_submit(doc, method):
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


def apply_purchase_term(doc, method):
    if not doc.custom_purchase_term:
        return

    term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

    total_flat_discount = 0.0
    header_discount_percent = 0.0

    # -------------------------------
    # 1️⃣ ITEM LEVEL : RATE DIFF ONLY
    # -------------------------------
    for item in doc.items:

        # store base rate once (idempotent)
        if not item.custom_base_rate_new:
            item.custom_base_rate_new = item.rate

        adjusted_rate = item.custom_base_rate_new

        for row in term.purchase_term_charges:
            if row.charge_type == "Rate Diff":
                adjusted_rate -= row.value

        item.rate = adjusted_rate


    # -----------------------------------
    # 2️⃣ DOCUMENT LEVEL : DISCOUNT ONLY
    # -----------------------------------
    for row in term.purchase_term_charges:
        if row.charge_type == "Discount":

            # Percentage discount on Net Total / Grand Total
            if row.value_type == "Percentage":
                header_discount_percent = row.value

            # Flat amount discount
            elif row.value_type == "Amount":
                total_flat_discount += row.value


    # -----------------------------------
    # 3️⃣ PUSH TO ERPNext STANDARD FIELDS
    # -----------------------------------
    if header_discount_percent:
        doc.apply_discount_on = row.apply_on
        doc.additional_discount_percentage = header_discount_percent


    elif total_flat_discount:
        doc.apply_discount_on = row.apply_on
        print(row.value_type)
        print(row.apply_on)
        doc.discount_amount = total_flat_discount


def apply_purchase_term_freight(doc, method):
    if not doc.custom_purchase_term:
        return

    term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

    has_freight = any(
        row.charge_type == "Freight"
        for row in term.purchase_term_charges
    )

    if not has_freight:
        return

    freight_account = get_freight_account(doc.company)

    for row in term.purchase_term_charges:
        if row.charge_type != "Freight":
            continue

        if any(
            t.account_head == freight_account
            and t.charge_type == "Actual"
            for t in doc.taxes
        ):
            continue

        tax = doc.append("taxes", {})
        tax.charge_type = "Actual"
        tax.category = "Total"
        tax.add_deduct_tax = "Add"
        tax.account_head = freight_account
        tax.tax_amount = row.value
        tax.total = row.value + doc.total
        tax.description = "Freight Charges (Purchase Term)"



def get_freight_account(company):
    account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "custom_is_freight_account": 1,
            "is_group": 0
        },
        "name"
    )

    if not account:
        frappe.throw(
            f"No Freight Account configured for company {company}"
        )

    return account

import frappe

@frappe.whitelist()
def get_gate_entry_with_po_child(doctype, txt, filters, page_length=20, start=0):
    """
    Returns Gate Entries for MultiSelectDialog
    """
    return frappe.db.sql("""
        SELECT
            ge.name AS name,
            IFNULL(ge.purchase_ids, '') AS purchase_ids,
            IFNULL(ge.purchase_order, '') AS purchase_order,
            IFNULL(ge.owner_site, '') AS owner_site
        FROM `tabGate Entry` ge
        WHERE ge.docstatus = 1
        AND ge.consignor = %(consignor)s
    """, filters, as_dict=True)


@frappe.whitelist()
def get_items_from_gate_entry(gate_entry_name):
    """
    Returns all items linked to a Gate Entry
    """
    items = frappe.db.get_all(
        'Gate Entry Item',
        filters={'parent': gate_entry_name},
        fields=['item_code', 'qty', 'purchase_order', 'purchase_order_item']
    )

    # Ensure all values are strings or numbers
    for item in items:
        item['item_code'] = item.get('item_code') or ''
        item['qty'] = item.get('qty') or 0
        item['purchase_order'] = item.get('purchase_order') or ''
        item['purchase_order_item'] = item.get('purchase_order_item') or ''

    return items



# import frappe
# import json
# from frappe.model.mapper import get_mapped_doc
# from frappe.utils import flt

# @frappe.whitelist()
# def make_purchase_receipt_with_gate_entry(source_name, target_doc=None, args=None):
#     if args is None:
#         args = {}
#     if isinstance(args, str):
#         args = json.loads(args)

#     # 🔥 VALIDATION: Submitted Gate Entry must exist
#     gate_entries = frappe.get_all(
#         "Gate Entry",
#         filters={
#             "purchase_order": source_name,
#             "docstatus": 1
#         },
#         pluck="name"
#     )

#     if not gate_entries:
#         frappe.throw(
#             f"No Submitted Gate Entry found for Purchase Order {source_name}"
#         )

#     has_unit_price_items = frappe.db.get_value(
#         "Purchase Order",
#         source_name,
#         "has_unit_price_items"
#     )

#     def is_unit_price_row(source):
#         return has_unit_price_items and source.qty == 0

#     def update_item(obj, target, source_parent):
#         remaining_qty = flt(obj.qty) - flt(obj.received_qty)

#         if remaining_qty <= 0:
#             return

#         target.qty = remaining_qty
#         target.stock_qty = remaining_qty * flt(obj.conversion_factor)
#         target.amount = remaining_qty * flt(obj.rate)
#         target.base_amount = (
#             remaining_qty * flt(obj.rate) * flt(source_parent.conversion_rate)
#         )

#     def select_item(d):
#         filtered_items = args.get("filtered_children", [])
#         return d.name in filtered_items if filtered_items else True

#     doc = get_mapped_doc(
#         "Purchase Order",
#         source_name,
#         {
#             "Purchase Order": {
#                 "doctype": "Purchase Receipt",
#                 "field_map": {
#                     "supplier_warehouse": "supplier_warehouse",
#                 },
#                 "validation": {
#                     "docstatus": ["=", 1],
#                 },
#             },
#             "Purchase Order Item": {
#                 "doctype": "Purchase Receipt Item",
#                 "field_map": {
#                     "name": "purchase_order_item",
#                     "parent": "purchase_order",
#                 },
#                 "postprocess": update_item,
#                 "condition": lambda doc: (
#                     True if is_unit_price_row(doc)
#                     else abs(doc.received_qty) < abs(doc.qty)
#                 )
#                 and doc.delivered_by_supplier != 1
#                 and select_item(doc),
#             },
#         },
#         target_doc,
#     )

#     # 🔥 PASS GATE ENTRY ID (first submitted one)
#     doc.custom_gate_entry = gate_entries[0]

#     return doc


# @frappe.whitelist()
# def get_purchase_orders_with_gate_entry():
#     return frappe.db.sql("""
#         SELECT DISTINCT po.name
#         FROM `tabPurchase Order` po
#         INNER JOIN `tabGate Entry` ge
#             ON ge.purchase_order = po.name
#         WHERE
#             ge.docstatus = 1
#             AND po.docstatus = 1
#             AND po.per_received < 99.99
#             AND po.status NOT IN ('Closed', 'On Hold')
#     """, as_dict=True)

