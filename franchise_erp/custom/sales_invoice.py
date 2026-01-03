import frappe
from frappe.utils import flt, cint



@frappe.whitelist()
def calculate_sis_values(customer, rate):

    # ---------------- BASIC CHECK ----------------
    if not customer or not rate:
        return None   # ❌ silently skip

    # ---------------- SKIP FOR CUSTOMER / BRANCH LOGIN ----------------
    user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
    if user_type == "Website User":
        return None

    # ---------------- CUSTOMER → COMPANY ----------------
    company = frappe.db.get_value("Customer", customer, "represents_company")
    if not company:
        return None   # ✅ Branch flow → skip logic

    # ---------------- SIS CONFIG ----------------
    c = frappe.get_value(
        "SIS Configuration",
        {"company": company},
        [
            "output_gst_min_net_rate",
            "output_gst_max_net_rate",
            "fresh_margin"
        ],
        as_dict=True
    )

    if not c:
        return None   # ❌ no config → skip

    rate = flt(rate)

    # ---------------- OUTPUT GST SLAB ----------------
    if rate <= flt(c.output_gst_min_net_rate):
        gst_percent = 5
    elif rate >= flt(c.output_gst_max_net_rate):
        gst_percent = 18
    else:
        gst_percent = 12

    # ---------------- GST INCLUSIVE SPLIT ----------------
    net_sale_value = flt(rate * 100 / (100 + gst_percent), 2)
    gst_value = flt(rate - net_sale_value, 2)

    # ---------------- MARGIN (ON MRP) ----------------
    margin_percent = flt(c.fresh_margin)
    margin_amount = flt(rate * margin_percent / 100, 2)

    # ---------------- FINAL TAXABLE VALUE ----------------
    taxable_value = flt(net_sale_value - margin_amount, 2)

    return {
        "gst_percent": gst_percent,
        "output_gst_value": gst_value,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "net_sale_value": net_sale_value,
        "taxable_value": taxable_value
    }



# def apply_sis_pricing(doc, method=None):

#     if not doc.customer:
#         return

#     for item in doc.items:

#         # STEP 1: Already calculated? Then SKIP
#         if item.custom_sis_calculated:
#             continue

#         if not item.rate:
#             continue

#        # Call SIS calculation
#     d = calculate_sis_values(doc.customer, item.rate)

#     if d:
#         # ✅ Populate custom fields from SIS calculation
#         item.custom_output_gst_ = d.get("gst_percent", 0)
#         item.custom_output_gst_value = d.get("output_gst_value", 0)
#         item.custom_margins_ = d.get("margin_percent", 0)
#         item.custom_margin_amount = d.get("margin_amount", 0)
#         item.custom_net_sale_value = d.get("net_sale_value", 0)
#         item.custom_total_invoice_amount = d.get("taxable_value", 0)

#         # GST EXCLUSIVE RATE
#         item.rate = d.get("taxable_value", 0)
#         item.net_rate = d.get("taxable_value", 0)
#         item.amount = flt(d.get("taxable_value", 0) * item.qty)
#         item.net_amount = item.amount

#         # Correct GST slab
#         item.item_tax_template = get_item_tax_template(d.get("gst_percent", 0))
#     else:
#         # SIS calculation skipped: fallback to defaults
#         item.custom_output_gst_ = 0
#         item.custom_output_gst_value = 0
#         item.custom_margins_ = 0
#         item.custom_margin_amount = 0
#         item.custom_net_sale_value = item.rate
#         item.custom_total_invoice_amount = item.rate

#         # GST EXCLUSIVE RATE remains same as entered
#         item.rate = item.rate
#         item.net_rate = item.rate
#         item.amount = flt(item.rate * item.qty)
#         item.net_amount = item.amount

#         # Keep original item tax template or fallback
#         # item.item_tax_template = item.item_tax_template or get_item_tax_template(0)
#         item.item_tax_template = get_item_tax_template(d.get("gst_percent", 0))



#     # 🔥 VERY IMPORTANT
#     for tax in doc.taxes:
#         tax.included_in_print_rate = 0

#     item.custom_sis_calculated = 1
#     # Reset & recalc
#     # doc.taxes = []
#     doc.calculate_taxes_and_totals()
    

from frappe.utils import flt

def apply_sis_pricing(doc, method=None):

    if not doc.customer:
        return

    for item in doc.items:

        # 🟢 Old qty from DB (None if new row)
        old_qty = item.get_db_value("qty")

        # 🔒 CASE 1: Already calculated AND qty NOT changed → SKIP
        if item.custom_sis_calculated and old_qty is not None and flt(item.qty) == flt(old_qty):
            continue

        # 🟢 No rate? Skip
        # if not item.rate:
        #     continue

        # 🔁 Call SIS calculation ONLY when:
        # - New row
        # - OR qty changed
        d = calculate_sis_values(doc.customer, item.rate)

        if not d:
            continue

        # ✅ Populate custom fields
        item.custom_output_gst_ = d.get("gst_percent", 0)
        item.custom_output_gst_value = d.get("output_gst_value", 0)
        item.custom_margins_ = d.get("margin_percent", 0)
        item.custom_margin_amount = d.get("margin_amount", 0)
        item.custom_net_sale_value = d.get("net_sale_value", 0)
        item.custom_total_invoice_amount = d.get("taxable_value", 0)

        # GST EXCLUSIVE RATE
        item.rate = d.get("taxable_value", 0)
        item.net_rate = item.rate
        item.amount = flt(item.rate * item.qty)
        item.net_amount = item.amount

        # GST slab
        item.item_tax_template = get_item_tax_template(
            d.get("gst_percent", 0)
        )

        # 🔒 Mark calculated
        item.custom_sis_calculated = 1

    # 🔁 Recalculate taxes safely
    doc.calculate_taxes_and_totals()


def get_item_tax_template(gst_percent):
    if gst_percent == 5:
        return "GST 5%"
    elif gst_percent == 12:
        return "GST 12%"
    elif gst_percent == 18:
        return "GST 18%"
    else:
        return "GST 0%"  # Default fallback


def update_packed_items_serial_no(doc, method):
    for item in doc.items:
        product_bundle = frappe.get_value("Product Bundle", {"new_item_code": item.item_code}, "name")
        
        if product_bundle:
            product_bundle_items = frappe.get_all(
                "Product Bundle Item",
                filters={"parent": product_bundle},
                fields=["item_code", "custom_serial_no"],
                order_by="idx asc"  # Ensure the order is maintained
            )

            # Assign serial numbers row by row
            for packed_item, bundle_item in zip(doc.packed_items, product_bundle_items):
                packed_item.serial_no = bundle_item["custom_serial_no"]

frappe.whitelist()(update_packed_items_serial_no)

def validate_item_from_so(doc, method=None):

    # 🔹 Skip if no row is linked to Sales Order
    if not any(row.sales_order for row in doc.items):
        return

    for row in doc.items:

        # 🔴 SO Item mandatory
        if not row.so_detail:
            frappe.throw(
                f"Row {row.idx}: Item <b>{row.item_code}</b> is not linked to Sales Order"
            )

        # 🔹 Get Sales Order Item Qty
        so_item = frappe.db.get_value(
            "Sales Order Item",
            row.so_detail,
            "qty"
        )

        if not so_item:
            frappe.throw(f"Row {row.idx}: Invalid Sales Order Item reference")

        so_qty = flt(so_item)

        # 🔹 Get TOTAL invoiced qty (Draft + Submitted, excluding current doc)
        invoiced_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(sii.qty), 0)
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON si.name = sii.parent
            WHERE
                sii.so_detail = %s
                AND si.name != %s
                AND si.docstatus IN (1)
        """, (row.so_detail, doc.name))[0][0]

        invoiced_qty = flt(invoiced_qty)

        remaining_qty = so_qty - invoiced_qty

        # 🔴 Validation
        if flt(row.qty) > remaining_qty:
            frappe.throw(
                f"Row {row.idx}: Entered Qty <b>{row.qty}</b> exceeds "
                f"remaining Sales Order Qty <b>{remaining_qty}</b>"
            )








#arpit
@frappe.whitelist()
def create_inter_company_purchase_receipt(sales_invoice):
    si = frappe.get_doc("Sales Invoice", sales_invoice)

    supplier = frappe.get_value(
        "Supplier",
        {"represents_company": si.company},
        "name"
    )

    if not supplier:
        frappe.throw("Internal Supplier not found")

    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = supplier
    pr.company = si.represents_company
    pr.set_posting_time = 1
    pr.posting_date = si.posting_date
    pr.posting_time = si.posting_time

    # 🔗 Safe reference
    pr.source_sales_invoice = si.name

    # ✅ Customer/Company ka warehouse
    target_warehouse = frappe.db.get_value(
        "Company",
        pr.company,
        "custom_default_warehouse"
    )

    # 🔁 Fallback agar default na ho
    if not target_warehouse:
        target_warehouse = frappe.get_value(
            "Warehouse",
            {"company": pr.company, "is_group": 0},
            "name"
        )

    if not target_warehouse:
        frappe.throw(f"No warehouse found for company {pr.company}")

    for item in si.items:
        pr.append("items", {
            "item_code": item.item_code,
            "qty": item.qty,
            "uom": item.uom,
            "rate": item.rate,
            "warehouse": target_warehouse
        })

    pr.insert()
    # pr.submit()

    return pr.name


import frappe
from frappe.utils import getdate, today

def validate_overdue_invoice(doc, method):
    # Only for new Sales Invoice
    if doc.is_new() and doc.customer:
        overdue_invoice = frappe.db.exists(
            "Sales Invoice",
            {
                "customer": doc.customer,
                "status": "Overdue",
                "due_date": ("<", getdate(today())),
                "docstatus": 1
            }
        )

        if overdue_invoice:
            frappe.throw(
                title="Overdue Invoice Exists",
                msg="Please clear your previous overdue invoice before creating a new Sales Invoice."
            )

