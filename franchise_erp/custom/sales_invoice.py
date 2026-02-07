import frappe
from frappe.utils import flt, cint

@frappe.whitelist()
def calculate_sis_values(customer, rate):
    # ---------------- BASIC CHECK ----------------
    if not customer or not rate:
        return None

    user_type = frappe.db.get_value(
        "User", frappe.session.user, "user_type"
    )
    if user_type == "Website User":
        return None

    # ---------------- CUSTOMER → COMPANY ----------------
    company = frappe.db.get_value(
        "Customer", customer, "represents_company"
    )
    if not company:
        return None

    # ---------------- SIS CONFIG ----------------
    c = frappe.get_value(
        "SIS Configuration",
        {"company": company},
        [
            "output_gst_min_net_rate",
            "output_gst_max_net_rate",
            "fresh_margin",
        ],
        as_dict=True,
    )

    if not c:
        return None

    rate = flt(rate)

    # ---------------- OUTPUT GST SLAB ----------------
    if rate <= flt(c.output_gst_min_net_rate):
        gst_percent = 5
    elif rate >= flt(c.output_gst_max_net_rate):
        gst_percent = 18
    else:
        gst_percent = 12

    # ---------------- GST INCLUSIVE SPLIT ----------------
    net_sale_value = flt((rate * 100) / (100 + gst_percent), 2)
    gst_value = flt(rate - net_sale_value, 2)

    # ---------------- MARGIN (ON MRP) ----------------
    margin_percent = flt(c.fresh_margin)
    margin_amount = flt((rate * margin_percent) / 100, 2)

    # ---------------- FINAL TAXABLE VALUE ----------------
    taxable_value = flt(net_sale_value - margin_amount, 2)

    return {
        "gst_percent": gst_percent,
        "output_gst_value": gst_value,
        "margin_percent": margin_percent,
        "margin_amount": margin_amount,
        "net_sale_value": net_sale_value,
        "taxable_value": taxable_value,
    }

#old code for sis calculation

# def apply_sis_pricing(doc, method=None):
#     if not doc.customer:
#         return

#     for item in doc.items:
#         old_qty = item.get_db_value("qty")

#         # Skip if already calculated & qty unchanged
#         if (
#             item.custom_sis_calculated
#             and old_qty is not None
#             and flt(item.qty) == flt(old_qty)
#         ):
#             continue

#         if not item.rate:
#             continue

#         d = calculate_sis_values(doc.customer, item.rate)
#         if not d:
#             continue

#         # -------- CUSTOM DISPLAY FIELDS --------
#         item.custom_output_gst_ = d.get("gst_percent", 0)
#         item.custom_output_gst_value = d.get("output_gst_value", 0)
#         item.custom_net_sale_value = d.get("net_sale_value", 0)
#         item.custom_margins_ = d.get("margin_percent", 0)
#         item.custom_margin_amount = d.get("margin_amount", 0)
#         item.custom_total_invoice_amount = d.get("taxable_value", 0)

#         # -------- FINAL SELLING RATE (GST EXCLUSIVE) --------
#         item.rate = d.get("taxable_value", 0)

#         # -------- ITEM TAX TEMPLATE --------
#         item.item_tax_template = get_item_tax_template(
#             d.get("gst_percent", 0)
#         )

#         item.custom_sis_calculated = 1

#     # Recalculate ERPNext taxes
#     doc.calculate_taxes_and_totals()

#for product bundle scan calculation condition

# def apply_sis_pricing(doc, method=None):
#     if not doc.customer:
#         return

#     for item in doc.items:
#         # Skip if rate not set
#         if not item.rate:
#             continue

#         # Skip if custom_product_bundle is set
#         if item.custom_product_bundle:
#             continue

#         # Calculate SIS values for this item
#         d = calculate_sis_values(doc.customer, item.rate)
#         if not d:
#             continue

#         # -------- CUSTOM DISPLAY FIELDS --------
#         item.custom_output_gst_ = d.get("gst_percent", 0)
#         item.custom_output_gst_value = d.get("output_gst_value", 0)
#         item.custom_net_sale_value = d.get("net_sale_value", 0)
#         item.custom_margins_ = d.get("margin_percent", 0)
#         item.custom_margin_amount = d.get("margin_amount", 0)
#         item.custom_total_invoice_amount = d.get("taxable_value", 0)

#         # -------- FINAL SELLING RATE (GST EXCLUSIVE) --------
#         item.rate = d.get("taxable_value", 0)

#         # -------- ITEM TAX TEMPLATE --------
#         item.item_tax_template = get_item_tax_template(d.get("gst_percent", 0))

#         # -------- FLAG TO REMEMBER CALCULATION (optional) --------
#         item.custom_sis_calculated = 1

#     # Recalculate ERPNext taxes after updating all items
#     doc.calculate_taxes_and_totals()

#Packed Item empty condition
# def apply_sis_pricing(doc, method=None):
#     if not doc.customer:
#         return

#     # 🔴 CONDITION: Product Bundle case
#     # Agar Packed Items table me data hai → calculation skip
#     if doc.get("packed_items") and len(doc.packed_items) > 0:
#         return

#     for item in doc.items:
#         # Skip if rate not set
#         if not item.rate:
#             continue

#         # Skip if product bundle item
#         if item.custom_product_bundle:
#             continue

#         d = calculate_sis_values(doc.customer, item.rate)
#         if not d:
#             continue

#         # -------- CUSTOM DISPLAY FIELDS --------
#         item.custom_output_gst_ = d.get("gst_percent", 0)
#         item.custom_output_gst_value = d.get("output_gst_value", 0)
#         item.custom_net_sale_value = d.get("net_sale_value", 0)
#         item.custom_margins_ = d.get("margin_percent", 0)
#         item.custom_margin_amount = d.get("margin_amount", 0)
#         item.custom_total_invoice_amount = d.get("taxable_value", 0)

#         # -------- FINAL SELLING RATE --------
#         item.rate = d.get("taxable_value", 0)

#         # -------- ITEM TAX TEMPLATE --------
#         item.item_tax_template = get_item_tax_template(
#             d.get("gst_percent", 0)
#         )

#         # -------- FLAG --------
#         item.custom_sis_calculated = 1

#     # Recalculate totals
#     doc.calculate_taxes_and_totals()

def apply_sis_pricing(doc, method=None):
    if not doc.customer or not doc.items:
        return

    # ❌ Product Bundle case skip
    if doc.get("packed_items"):
        return

    for item in doc.items:

        # Already calculated → skip
        if item.custom_sis_calculated:
            continue

        # Rate must exist
        if not item.rate or item.rate <= 0:
            continue

        # Product bundle line skip
        if item.custom_product_bundle:
            continue

        d = calculate_sis_values(doc.customer, item.rate)
        if not d:
            continue

        # -------- DISPLAY FIELDS --------
        item.custom_output_gst_ = d["gst_percent"]
        item.custom_output_gst_value = d["output_gst_value"]
        item.custom_net_sale_value = d["net_sale_value"]
        item.custom_margins_ = d["margin_percent"]
        item.custom_margin_amount = d["margin_amount"]
        item.custom_total_invoice_amount = d["taxable_value"]

        # -------- FINAL RATE --------
        item.rate = d["taxable_value"]

        # -------- TAX TEMPLATE --------
        item.item_tax_template = get_item_tax_template(
            d["gst_percent"]
        )

        item.custom_sis_calculated = 1

    doc.calculate_taxes_and_totals()


def get_item_tax_template(gst_percent):
    if gst_percent == 5:
        return "GST 5%"
    elif gst_percent == 18:
        return "GST 18%"
    else:
        return "GST 0%"




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

# @frappe.whitelist()
# def create_inter_company_purchase_receipt(sales_invoice):

#     si = frappe.get_doc("Sales Invoice", sales_invoice)

#     # -------------------------------------------------
#     # Find Internal Supplier
#     # -------------------------------------------------
#     supplier = frappe.get_value(
#         "Supplier",
#         {"represents_company": si.company},
#         "name"
#     )
#     if not supplier:
#         frappe.throw("Internal Supplier not found")

#     # -------------------------------------------------
#     # Create Purchase Receipt
#     # -------------------------------------------------
#     pr = frappe.new_doc("Purchase Receipt")
#     pr.supplier = supplier
#     pr.company = si.represents_company
#     pr.custom_source_sales_invoice = si.name
#     pr.posting_date = si.posting_date
#     pr.set_posting_time = 1
#     pr.posting_time = si.posting_time

#     # -------------------------------------------------
#     # 🔥 GST & ADDRESS FIX (ERPNext v15 compatible)
#     # -------------------------------------------------

#     # ---- Company Address (from Dynamic Link) ----
#     company_address = frappe.db.get_value(
#         "Dynamic Link",
#         {
#             "link_doctype": "Company",
#             "link_name": pr.company,
#             "parenttype": "Address"
#         },
#         "parent"
#     )

#     if not company_address:
#         frappe.throw(f"Company Address missing for {pr.company}")

#     pr.company_address = company_address
#     pr.company_gstin = frappe.get_value("Address", company_address, "gstin")

#     # ---- Supplier Billing Address ----
#     supplier_address = frappe.db.get_value(
#         "Dynamic Link",
#         {
#             "link_doctype": "Supplier",
#             "link_name": supplier,
#             "parenttype": "Address"
#         },
#         "parent"
#     )


#     if not supplier_address:
#         frappe.throw(f"Billing Address missing for Supplier {supplier}")

#     pr.supplier_address = supplier_address

#     # ERPNext GST wrongly checks this for Company GST
#     # pr.billing_address = supplier_address
#     # pr.billing_address = company_address

#     # -------------------------------------------------
#     # Warehouse
#     # -------------------------------------------------
#     warehouse = frappe.get_value(
#         "Warehouse",
#         {"company": pr.company, "is_group": 0},
#         "name"
#     )
#     if not warehouse:
#         frappe.throw("Warehouse not found")

#     total_qty = 0

#     # -------------------------------------------------
#     # Append Items (Discounted Rate)
#     # -------------------------------------------------
#     for item in si.items:
#         rate = item.net_rate or item.rate

#         pr.append("items", {
#             "item_code": item.item_code,
#             "item_name": item.item_name,
#             "qty": item.qty,
#             "uom": item.uom,
#             "rate": rate,
#             "price_list_rate": item.price_list_rate,
#             "warehouse": warehouse
#         })

#         total_qty += item.qty

#     # -------------------------------------------------
#     # Calculate & Save
#     # -------------------------------------------------
#     pr.run_method("set_missing_values")
#     pr.run_method("calculate_taxes_and_totals")
#     pr.save(ignore_permissions=True)

#     # -------------------------------------------------
#     # Fix Item Level Amounts (GST Safe)
#     # -------------------------------------------------
#     for si_item in si.items:
#         pr_item = frappe.get_value(
#             "Purchase Receipt Item",
#             {
#                 "parent": pr.name,
#                 "item_code": si_item.item_code
#             },
#             "name"
#         )

#         if not pr_item:
#             continue

#     rate = si_item.net_rate or si_item.rate
#     price_list_rate = si_item.price_list_rate
#     amount = rate * si_item.qty

#     frappe.db.set_value("Purchase Receipt Item", pr_item, {
#         "price_list_rate": price_list_rate,
#         "rate": rate,
#         "net_rate": rate,
#         "amount": amount,
#         "net_amount": amount,
#         "base_price_list_rate": price_list_rate,
#         "base_rate": rate,
#         "base_net_rate": rate,
#         "base_amount": amount,
#         "base_net_amount": amount
#     })


#     # -------------------------------------------------
#     # Header Totals Sync
#     # -------------------------------------------------
#     frappe.db.set_value("Purchase Receipt", pr.name, {
#         "total": si.net_total,
#         "net_total": si.net_total,
#         "grand_total": si.grand_total,
#         "base_grand_total": si.base_grand_total,
#         "rounded_total": si.rounded_total or si.grand_total,
#         "total_qty": total_qty
#     })
#     # for si_item in si.items:
#     #     create_standard_buying_item_price(
#     #         item_code=si_item.item_code,
#     #         source_price_list=si.selling_price_list
#     #     )
#     frappe.db.commit()
#     return pr.name

import frappe

# =========================================================
# ITEM TAX TEMPLATE
# =========================================================
def get_item_tax_template1(company, price_list_rate):
    if not company or not price_list_rate:
        return None

    company_abbr = frappe.get_value("Company", company, "abbr")
    if not company_abbr:
        return None

    if price_list_rate <= 2500:
        template = f"GST 5% - {company_abbr}"
    else:
        template = f"GST 18% - {company_abbr}"

    return template if frappe.db.exists("Item Tax Template", template) else None


# =========================================================
# PURCHASE TAX TEMPLATE – STATE BASED (🔥 CORE LOGIC)
# =========================================================
def get_purchase_tax_template(company, supplier):

    company_address = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
        "parent"
    )

    supplier_address = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Address"},
        "parent"
    )

    if not company_address or not supplier_address:
        frappe.throw("Company or Supplier Address missing")

    company_state = frappe.get_value("Address", company_address, "state")
    supplier_state = frappe.get_value("Address", supplier_address, "state")

    if not company_state or not supplier_state:
        frappe.throw("Company or Supplier State missing")

    company_abbr = frappe.get_value("Company", company, "abbr")
    if not company_abbr:
        frappe.throw("Company abbreviation missing")

    # 🔥 PURE STATE BASED DECISION
    if company_state == supplier_state:
        template = f"Input GST In-state - {company_abbr}"
    else:
        template = f"Input GST Out-state - {company_abbr}"

    if not frappe.db.exists("Purchase Taxes and Charges Template", template):
        frappe.throw(f"Purchase GST Template missing: {template}")

    return template


# =========================================================
# MAIN – INTER COMPANY PURCHASE RECEIPT
# =========================================================
# @frappe.whitelist()
# def create_inter_company_purchase_receipt(sales_invoice):
    
#     si = frappe.get_doc("Sales Invoice", sales_invoice)

#     supplier = frappe.get_value(
#         "Supplier",
#         {"represents_company": si.company},
#         "name"
#     )
#     if not supplier:
#         frappe.throw("Internal Supplier not found")

#     pr = frappe.new_doc("Purchase Receipt")
#     pr.company = si.represents_company
#     pr.supplier = supplier

#     # 🔥 FIX: IGNORE SUPPLIER TAX CATEGORY
#     pr.tax_category = None

#     pr.custom_source_sales_invoice = si.name
#     pr.posting_date = si.posting_date
#     pr.set_posting_time = 1
#     pr.posting_time = si.posting_time

#     # ---------------- Company Address ----------------
#     company_address = frappe.db.get_value(
#         "Dynamic Link",
#         {"link_doctype": "Company", "link_name": pr.company, "parenttype": "Address"},
#         "parent"
#     )
#     pr.company_address = company_address
#     pr.company_gstin = frappe.get_value("Address", company_address, "gstin")

#     # ---------------- Supplier Address ----------------
#     supplier_address = frappe.db.get_value(
#         "Dynamic Link",
#         {"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Address"},
#         "parent"
#     )
#     pr.supplier_address = supplier_address

#     # ---------------- Warehouse ----------------
#     warehouse = frappe.get_value(
#         "Warehouse",
#         {"company": pr.company, "is_group": 0},
#         "name"
#     )

#     # ---------------- Items ----------------
#     for item in si.items:
#         rate = item.net_rate or item.rate
#         pr.append("items", {
#             "item_code": item.item_code,
#             "item_name": item.item_name,
#             "qty": item.qty,
#             "uom": item.uom,
#             "rate": rate,
#             "price_list_rate": item.price_list_rate,
#             "warehouse": warehouse
#         })

#     # ---------------- FIRST SAVE ----------------
#     pr.run_method("set_missing_values")
#     pr.save(ignore_permissions=True)

#     # ---------------- ITEM TAX TEMPLATE ----------------
#     for row in pr.items:
#         item_tax_template = get_item_tax_template1(
#             pr.company,
#             row.rate
#         )
#         row.item_tax_template = item_tax_template

#     # ---------------- APPLY PURCHASE GST TEMPLATE ----------------
#     purchase_tax_template = get_purchase_tax_template(
#         pr.company,
#         supplier
#     )

#     # 🔥 FORCE APPLY – IGNORE ERPNext AUTO LOGIC
#     pr.taxes = []
#     pr.taxes_and_charges = purchase_tax_template
#     pr.tax_category = None

#     # ---------------- FINAL CALC ----------------
#     pr.run_method("calculate_taxes_and_totals")
#     pr.save(ignore_permissions=True)

#     frappe.db.commit()
#     return pr.name
import frappe
from frappe import _

import frappe
from frappe import _


@frappe.whitelist()
def create_inter_company_purchase_receipt(sales_invoice):

    # =====================================================
    # 🚫 DUPLICATE GRN CHECK
    # =====================================================
    existing_pr = frappe.get_value(
        "Purchase Receipt",
        {
            "custom_source_sales_invoice": sales_invoice,
            "docstatus": ["!=", 2]  # ignore cancelled PR
        },
        "name"
    )

    if existing_pr:
        frappe.throw(
            _("Inter Company GRN already created against this Sales Invoice: {0}")
            .format(existing_pr)
        )

    # =====================================================
    # SALES INVOICE
    # =====================================================
    si = frappe.get_doc("Sales Invoice", sales_invoice)

    # =====================================================
    # INTERNAL SUPPLIER
    # =====================================================
    supplier = frappe.get_value(
        "Supplier",
        {"represents_company": si.company},
        "name"
    )
    if not supplier:
        frappe.throw(_("Internal Supplier not found"))

    # =====================================================
    # CREATE PURCHASE RECEIPT
    # =====================================================
    pr = frappe.new_doc("Purchase Receipt")
    pr.company = si.represents_company
    pr.supplier = supplier

    # 🔥 IGNORE SUPPLIER TAX CATEGORY
    pr.tax_category = None

    pr.custom_source_sales_invoice = si.name
    pr.posting_date = si.posting_date
    pr.set_posting_time = 1
    pr.posting_time = si.posting_time

    # =====================================================
    # COMPANY ADDRESS
    # =====================================================
    company_address = frappe.db.get_value(
        "Dynamic Link",
        {
            "link_doctype": "Company",
            "link_name": pr.company,
            "parenttype": "Address"
        },
        "parent"
    )
    pr.company_address = company_address
    pr.company_gstin = frappe.get_value("Address", company_address, "gstin")

    # =====================================================
    # SUPPLIER ADDRESS
    # =====================================================
    supplier_address = frappe.db.get_value(
        "Dynamic Link",
        {
            "link_doctype": "Supplier",
            "link_name": supplier,
            "parenttype": "Address"
        },
        "parent"
    )
    pr.supplier_address = supplier_address

    # =====================================================
    # WAREHOUSE
    # =====================================================
    warehouse = frappe.get_value(
        "Warehouse",
        {
            "company": pr.company,
            "is_group": 0
        },
        "name"
    )

    if not warehouse:
        frappe.throw(_("No warehouse found for company {0}").format(pr.company))

    # =====================================================
    # ITEMS (COPY SERIAL NO ALSO)
    # =====================================================
    for item in si.items:
        rate = item.net_rate or item.rate

        pr_item = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "uom": item.uom,
            "rate": rate,
            "price_list_rate": item.price_list_rate,
            "warehouse": warehouse
        }

        # 🔥 COPY SERIAL NUMBERS FROM SALES INVOICE
        if item.serial_no:
            pr_item["serial_no"] = item.serial_no

        pr.append("items", pr_item)

    # =====================================================
    # FIRST SAVE
    # =====================================================
    pr.run_method("set_missing_values")
    pr.save(ignore_permissions=True)

    # =====================================================
    # ITEM TAX TEMPLATE (ROW WISE)
    # =====================================================
    for row in pr.items:
        item_tax_template = get_item_tax_template1(
            pr.company,
            row.rate
        )
        row.item_tax_template = item_tax_template

    # =====================================================
    # PURCHASE GST TEMPLATE
    # =====================================================
    purchase_tax_template = get_purchase_tax_template(
        pr.company,
        supplier
    )

    if not purchase_tax_template:
        frappe.throw(_("Purchase GST Tax Template not found"))

    # 🔥 FORCE APPLY – IGNORE ERPNext AUTO LOGIC
    pr.taxes = []
    pr.taxes_and_charges = purchase_tax_template
    pr.tax_category = None

    # =====================================================
    # FINAL CALCULATION
    # =====================================================
    pr.run_method("calculate_taxes_and_totals")
    pr.save(ignore_permissions=True)

    frappe.db.commit()
    return pr.name

# @frappe.whitelist()
# def create_inter_company_purchase_receipt(sales_invoice):

#     si = frappe.get_doc("Sales Invoice", sales_invoice)

#     # -------------------------------------------------
#     # Internal Supplier
#     # -------------------------------------------------
#     supplier = frappe.get_value(
#         "Supplier",
#         {"represents_company": si.company},
#         "name"
#     )
#     if not supplier:
#         frappe.throw("Internal Supplier not found")

#     # -------------------------------------------------
#     # Purchase Receipt
#     # -------------------------------------------------
#     pr = frappe.new_doc("Purchase Receipt")
#     pr.company = si.represents_company
#     pr.supplier = supplier
#     pr.custom_source_sales_invoice = si.name
#     pr.posting_date = si.posting_date
#     pr.set_posting_time = 1
#     pr.posting_time = si.posting_time

#     # -------------------------------------------------
#     # Company Address + GSTIN
#     # -------------------------------------------------
#     company_address = frappe.db.get_value(
#         "Dynamic Link",
#         {
#             "link_doctype": "Company",
#             "link_name": pr.company,
#             "parenttype": "Address"
#         },
#         "parent"
#     )
#     pr.company_address = company_address
#     pr.company_gstin = frappe.get_value("Address", company_address, "gstin")

#     # -------------------------------------------------
#     # Supplier Address + GSTIN (MOST IMPORTANT)
#     # -------------------------------------------------
#     supplier_address = frappe.db.get_value(
#         "Dynamic Link",
#         {
#             "link_doctype": "Supplier",
#             "link_name": supplier,
#             "parenttype": "Address"
#         },
#         "parent"
#     )
#     pr.supplier_address = supplier_address
#     pr.supplier_gstin = frappe.get_value("Address", supplier_address, "gstin")

#     # -------------------------------------------------
#     # Tax Category
#     # -------------------------------------------------
#     pr.tax_category = "GST"

#     # -------------------------------------------------
#     # Warehouse
#     # -------------------------------------------------
#     warehouse = frappe.get_value(
#         "Warehouse",
#         {"company": pr.company, "is_group": 0},
#         "name"
#     )

#     # -------------------------------------------------
#     # Items
#     # -------------------------------------------------
#     for si_item in si.items:
#         pr.append("items", {
#             "item_code": si_item.item_code,
#             "qty": si_item.qty,
#             "uom": si_item.uom,
#             "rate": flt(si_item.net_rate or si_item.rate),
#             "warehouse": warehouse
#         })

#     # -------------------------------------------------
#     # 🔥 LET ERP DO EVERYTHING
#     # -------------------------------------------------
#     pr.run_method("set_missing_values")
#     pr.run_method("calculate_taxes_and_totals")

#     pr.save(ignore_permissions=True)
#     frappe.db.commit()

#     return pr.name

# for si_item in si.items:
    #     create_standard_buying_item_price(
    #         item_code=si_item.item_code,
    #         source_price_list=si.selling_price_list
    #     )

@frappe.whitelist()
def create_standard_buying_item_price(item_code, source_price_list):
    """
    Create OR Update Standard Buying Item Price
    using rate from given source price list
    """

    # ----------------------------------
    # Get Standard Buying Price List
    # ----------------------------------
    target_price_list = frappe.db.get_value(
        "Buying Settings", None, "buying_price_list"
    )

    if not target_price_list:
        frappe.throw("Standard Buying Price List not configured")

    # ----------------------------------
    # Fetch source Item Price
    # ----------------------------------
    source_ip = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": source_price_list
        },
        fields=[
            "price_list_rate",
            "currency",
            "uom",
            "valid_from",
            "valid_upto"
        ],
        order_by="modified desc",
        limit=1
    )

    if not source_ip:
        frappe.throw(
            f"Item Price not found in <b>{source_price_list}</b>"
        )

    source_ip = source_ip[0]

    # ----------------------------------
    # Check existing Standard Buying
    # ----------------------------------
    existing_ip = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": target_price_list,
            "buying": 1,
            "currency": source_ip.currency,
            "uom": source_ip.uom
        },
        fields=["name"],
        limit=1
    )

    # ----------------------------------
    # UPDATE if exists
    # ----------------------------------
    if existing_ip:
        ip = frappe.get_doc("Item Price", existing_ip[0].name)

        ip.price_list_rate = source_ip.price_list_rate
        ip.valid_from = source_ip.valid_from
        ip.valid_upto = source_ip.valid_upto

        ip.save(ignore_permissions=True)

        frappe.msgprint(
            f"Standard Buying Item Price <b>updated</b> for {item_code}",
            alert=True
        )

        return ip.name

    # ----------------------------------
    # CREATE if not exists
    # ----------------------------------
    ip = frappe.new_doc("Item Price")
    ip.item_code = item_code
    ip.price_list = target_price_list
    ip.price_list_rate = source_ip.price_list_rate
    ip.currency = source_ip.currency
    ip.uom = source_ip.uom
    ip.valid_from = source_ip.valid_from
    ip.valid_upto = source_ip.valid_upto

    ip.buying = 1
    ip.selling = 0

    ip.insert(ignore_permissions=True)

    frappe.msgprint(
        f"Standard Buying Item Price <b>created</b> for {item_code}",
        alert=True
    )

    return ip.name



#end

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



