# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SISDebitNoteLog(Document):
	pass

import frappe

# @frappe.whitelist()
# def fetch_invoices(company, from_date, to_date):

#     invoices = frappe.db.sql("""
#         SELECT 
#             si.name AS name,
#             si.posting_date,
#             si.customer,
#             si.additional_discount_percentage,

#             sii.item_code,
#             sii.item_name,
#             sii.qty,
#             sii.rate,
#             sii.price_list_rate,
#             sii.discount_percentage,
#                               sii.price_list_rate,

#             (sii.qty * sii.price_list_rate) AS total_amount,

#             -- Net Amount after applying invoice discount
#             ((sii.qty * sii.price_list_rate) - 
#              (((sii.qty * sii.price_list_rate) * sii.discount_percentage) / 100)
#             ) AS net_amount

#         FROM `tabSales Invoice` si
#         JOIN `tabSales Invoice Item` sii ON sii.parent = si.name

#         WHERE 
#             si.company = %s
#             AND si.posting_date BETWEEN %s AND %s
#             AND si.docstatus = 1

#         ORDER BY si.posting_date, si.name, sii.idx
#     """, (company, from_date, to_date), as_dict=True)

#     return {
#         "invoice_list": invoices,
#         "message": f"{len(invoices)} invoice items found."
#     }

# from frappe.utils import getdate, add_days, nowdate
# from datetime import date
# import calendar
# import datetime
# import json
# import frappe
# from frappe import _
# from decimal import Decimal, ROUND_HALF_UP

# def round2(v):
#     try:
#         v = Decimal(str(v))
#     except:
#         v = Decimal("0")
#     return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
# @frappe.whitelist()
# def fetch_invoices(company, from_date=None, to_date=None):
#     from frappe.utils import getdate, nowdate, add_days
#     import calendar
#     import json

#     def to_decimal(v):
#         try:
#             return Decimal(str(v))
#         except:
#             return Decimal("0")


#     # -------------------------------------------------------------------
#     # FETCH CONFIG VALUES
#     # -------------------------------------------------------------------
#     fresh_margin, discounted_margin, period_type, auto_credit_note_percent, discount_threshold = frappe.db.get_value(
#         "SIS Configuration",
#         {"company": company},
#         ["fresh_margin", "discounted_margin", "sis_debit_note_creation_period", "auto_credit_note_percent", "discount_threshold"]
#     )

#     if not period_type:
#         frappe.throw(_("Please set Debit Note Creation Period in SIS Configuration"))

#     fresh_margin = to_decimal(fresh_margin or 0)
#     discounted_margin = to_decimal(discounted_margin or 0)
#     auto_credit_note_percent = to_decimal(auto_credit_note_percent or 0)
#     discount_threshold = to_decimal(discount_threshold or 0)

#     # -------------------------------------------------------------------
#     # CLEAN DATE INPUTS
#     # -------------------------------------------------------------------
#     if not from_date or from_date == "" or from_date == "null":
#         from_date = None

#     if not to_date or to_date == "" or to_date == "null":
#         to_date = None

#     # -------------------------------------------------------------------
#     # SET DATE RANGE USING PERIOD TYPE
#     # -------------------------------------------------------------------
#     if period_type == "Fortnightly":
#       from_date, to_date = get_period_dates("Fortnightly")
#     else:
#         # Use provided dates OR generate new if blank
#         if not from_date or not to_date:
#             from_date, to_date = get_period_dates(period_type)

#     from_date = getdate(from_date)
#     to_date = getdate(to_date)

#     # DEBUG LOG
#     frappe.log_error("DATE_RANGE_USED", f"From: {from_date}, To: {to_date}, Period: {period_type}")

#     # -------------------------------------------------------------------
#     # FETCH INVOICE DATA
#     # -------------------------------------------------------------------
#     invoices = frappe.db.sql("""
#         SELECT 
#             si.name AS name,
#             si.posting_date,
#             si.posting_time,
#             si.customer,
#             sii.name AS sii_name,
#             sii.item_code,
#             sii.item_name,
#             sii.qty,
#             sii.rate,
#             sii.price_list_rate,
#             sii.discount_percentage,
#             (sii.qty * sii.price_list_rate) AS total_amount,
#             ((sii.qty * sii.price_list_rate) * sii.discount_percentage / 100) AS discount_amount,
#             ((sii.qty * sii.price_list_rate) - ((sii.qty * sii.price_list_rate) * sii.discount_percentage / 100)) AS net_amount,
#             sii.item_tax_rate
#         FROM `tabSales Invoice` si
#         JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
#         WHERE 
#             si.company = %s
#             AND si.posting_date BETWEEN %s AND %s
#             AND si.docstatus = 1
#         ORDER BY si.posting_date DESC, si.posting_time DESC, si.name, sii.idx
#     """, (company, from_date, to_date), as_dict=True)

#     processed = []

#     # -------------------------------------------------------------------
#     # PROCESS EACH INVOICE ITEM
#     # -------------------------------------------------------------------
#     for r in invoices:
#         net_amount = to_decimal(r.get("net_amount") or 0)

#         gst_percent = Decimal("0.0")
#         item_tax_rate_raw = r.get("item_tax_rate")

#         # Parse GST JSON
#         if item_tax_rate_raw:
#             try:
#                 tax_json = frappe.parse_json(item_tax_rate_raw)
#             except:
#                 try:
#                     tax_json = json.loads(item_tax_rate_raw)
#                 except:
#                     tax_json = {}

#             if isinstance(tax_json, dict):
#                 for v in tax_json.values():
#                     gst_percent += to_decimal(v)

#         # GST CALC
#         out_put_gst_value = net_amount * gst_percent / (100 + gst_percent)
#         net_sale_value = net_amount - out_put_gst_value
#         discount_percentage = to_decimal(r.get("discount_percentage") or 0)
#         margin_percent = discounted_margin if discount_percentage > 0 else fresh_margin
#         margin_amount = (net_amount * margin_percent) / Decimal(100)
#         inv_base_value = net_sale_value - margin_amount
#         # Fetch Input GST from Purchase Invoice Item (HO → Branch Purchase)
#         # Fetch Input GST From Serial No (Branch → End customer)
#         # r = your row dict
#         serial_no = None

#         if r.get("sii_name"):
#             serial_no = frappe.db.get_value("Sales Invoice Item", r["sii_name"], "serial_no")

#         input_gst_value = Decimal("0.00")
#         custom_invoice_amount = Decimal("0.00")

#         if serial_no:

#             # Fetch custom_input_gst
#             serial_gst = frappe.db.get_value(
#                 "Serial No",
#                 {"item_code": r.get("item_code"), "name": serial_no},
#                 "custom_input_gst"
#             )

#             if serial_gst:
#                 input_gst_value = Decimal(str(serial_gst))

#             # Fetch custom_invoice_amount
#             serial_base_amount = frappe.db.get_value(
#                 "Serial No",
#                 {"item_code": r.get("item_code"), "name": serial_no},
#                 "custom_invoice_amount"
#             )

#             if serial_base_amount:
#                 custom_invoice_amount = Decimal(str(serial_base_amount))

#         # -----------------------------------------
#         # TOTAL SERIAL VALUE = base + gst
#         # -----------------------------------------
#         total_serial_invoice_value = custom_invoice_amount + input_gst_value
#         # Example: 67.24 + 3.36 = 70.60

#         # -----------------------------------------
#         # NOW CALCULATE CD/DN DIFFERENCE
#         # -----------------------------------------
#         # invoice_value = inv_base_value + input_gst_value (your own invoice value)
#         invoice_value = inv_base_value + input_gst_value

#         cd_dn_value = total_serial_invoice_value - invoice_value

#         # Auto credit note
#         # if discount_percentage > discount_threshold:
#         #     debit_note = purchase_value - invoice_value
#         # else:
#         #     debit_note = Decimal(0)

#         # ROUNDS
#         r["gst_percent"] = float(gst_percent)
#         r["gst_amount"] = round2(out_put_gst_value)
#         r["net_sale_value"] = round2(net_sale_value)
#         r["inv_base_value"] = round2(inv_base_value)
#         r["in_put_gst_value"] = round2(input_gst_value)
#         r["base_value"] = round2(net_sale_value)
#         r["margin_percent"] = float(margin_percent)
#         r["margin_amount"] = round2(margin_amount)
#         r["total_amount"] = round2(to_decimal(r.get("total_amount") or 0))
#         r["discount_amount"] = round2(to_decimal(r.get("discount_amount") or 0))
#         r["net_amount"] = round2(net_amount)
#         r["invoice_value"] = round2(invoice_value)
#         r["debit_note"] = round2(cd_dn_value)

#         processed.append(r)

#     return {
#         "invoice_list": processed,
#         "period_type": period_type,
#         "from_date": str(from_date),
#         "to_date": str(to_date)
#     }



from frappe.utils import getdate, add_days, nowdate
from datetime import date
import calendar
import json
import frappe
from frappe import _
from decimal import Decimal, ROUND_HALF_UP

def round2(v):
    try:
        v = Decimal(str(v))
    except:
        v = Decimal("0")
    return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def to_decimal(v):
    try:
        return Decimal(str(v))
    except:
        return Decimal("0")

from decimal import Decimal
import frappe



from decimal import Decimal

# def get_item_input_gst(item_code, company):
#     """
#     Fetch INPUT GST directly from last Purchase Invoice Item
#     using FINAL calculated fields
#     """

#     pii = frappe.db.sql("""
#         SELECT
#             pii.custom_single_item_rate AS single_item_rate,
#             pii.custom_single_item_input_gst_amount AS gst_amount
#         FROM `tabPurchase Invoice Item` pii
#         JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
#         WHERE
#             pii.item_code = %s
#             AND pi.company = %s
#             AND pi.docstatus = 1
#         ORDER BY pi.posting_date DESC, pi.posting_time DESC, pii.creation DESC
#         LIMIT 1
#     """, (item_code, company), as_dict=True)

#     if not pii:
#         return Decimal("0"), Decimal("0"), Decimal("0")

#     row = pii[0]

#     single_item_rate = abs(Decimal(str(row.single_item_rate or 0)))
#     gst_amount_per_item = abs(Decimal(str(row.gst_amount or 0)))

#     # GST % derive
#     gst_percent = (
#         abs(gst_amount_per_item * 100 / single_item_rate)
#         if single_item_rate > 0 else Decimal("0")
#     )

#     return gst_percent, gst_amount_per_item, single_item_rate

def get_item_input_gst(item_code, company):
    """
    Fetch INPUT GST directly from last Purchase Receipt Item
    using FINAL calculated fields
    """

    pri = frappe.db.sql("""
        SELECT
            pri.custom_single_item_rate AS single_item_rate,
            pri.custom_single_item_input_gst_amount AS gst_amount
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE
            pri.item_code = %s
            AND pr.company = %s
            AND pr.docstatus = 1
        ORDER BY
            pr.posting_date DESC,
            pr.posting_time DESC,
            pri.creation DESC
        LIMIT 1
    """, (item_code, company), as_dict=True)

    if not pri:
        return Decimal("0"), Decimal("0"), Decimal("0")

    row = pri[0]

    single_item_rate = abs(Decimal(str(row.single_item_rate or 0)))
    gst_amount_per_item = abs(Decimal(str(row.gst_amount or 0)))

    # 🔥 GST %
    gst_percent = (
        abs((gst_amount_per_item * 100) / single_item_rate)
        if single_item_rate > 0 else Decimal("0")
    )

    return gst_percent, gst_amount_per_item, single_item_rate


# @frappe.whitelist()
# def fetch_invoices(company, from_date=None, to_date=None):
#     # -------------------------------------------------------------------
#     # FETCH CONFIG VALUES
#     # -------------------------------------------------------------------
#     fresh_margin, discounted_margin, period_type, auto_credit_note_percent, discount_threshold = frappe.db.get_value(
#         "SIS Configuration",
#         {"company": company},
#         ["fresh_margin", "discounted_margin", "sis_debit_note_creation_period", "auto_credit_note_percent", "discount_threshold"]
#     )

#     if not period_type:
#         frappe.throw(_("Please set Debit Note Creation Period in SIS Configuration"))

#     fresh_margin = to_decimal(fresh_margin or 0)
#     discounted_margin = to_decimal(discounted_margin or 0)
#     auto_credit_note_percent = to_decimal(auto_credit_note_percent or 0)
#     discount_threshold = to_decimal(discount_threshold or 0)

#     # -------------------------------------------------------------------
#     # CLEAN DATE INPUTS
#     # -------------------------------------------------------------------
#     if not from_date or from_date in ["", "null"]:
#         from_date = None

#     if not to_date or to_date in ["", "null"]:
#         to_date = None

#     # -------------------------------------------------------------------
#     # SET DATE RANGE USING PERIOD TYPE
#     # -------------------------------------------------------------------
#     if period_type == "Fortnightly":
#         from_date, to_date = get_period_dates("Fortnightly")
#     else:
#         if not from_date or not to_date:
#             from_date, to_date = get_period_dates(period_type)

#     from_date = getdate(from_date)
#     to_date = getdate(to_date)

#     frappe.log_error("DATE_RANGE_USED", f"From: {from_date}, To: {to_date}, Period: {period_type}")

#     # -------------------------------------------------------------------
#     # FETCH SALES INVOICE DATA
#     # -------------------------------------------------------------------
#     invoices = frappe.db.sql("""
#         SELECT 
#             dn.name AS name,
#             dn.posting_date,
#             dn.posting_time,
#             dn.customer,
#             dni.name AS sii_name,
#             dni.item_code,
#             dni.item_name,
#             dni.qty,
#             dni.rate,
#             dni.price_list_rate,
#             dni.discount_percentage,
#             (dni.qty * dni.price_list_rate) AS total_amount,
#             ((dni.qty * dni.price_list_rate) * dni.discount_percentage / 100) AS discount_amount,
#             ((dni.qty * dni.price_list_rate) - ((dni.qty * dni.price_list_rate) * dni.discount_percentage / 100)) AS net_amount
#         FROM `tabDelivery Note` AS dn
#         JOIN `tabDelivery Note Item` AS dni ON dni.parent = dn.name
#         WHERE 
#             dn.company = %s
#             AND dn.posting_date BETWEEN %s AND %s
#             AND dn.docstatus = 1
#         ORDER BY dn.posting_date DESC, dn.posting_time DESC, dn.name, dni.idx
#     """, (company, from_date, to_date), as_dict=True)



#     processed = []

#     # -------------------------------------------------------------------
#     # PROCESS EACH ITEM
#     # -------------------------------------------------------------------
#     for r in invoices:
#         net_amount = to_decimal(r.get("net_amount") or 0)

#         # -----------------------------
#         # OUTPUT GST SLAB LOGIC
#         # -----------------------------
#         if net_amount <= Decimal("2500"):
#             gst_percent = Decimal("5.0")
#         else:
#             gst_percent = Decimal("18.0")

#         out_put_gst_value = net_amount * gst_percent / (100 + gst_percent)
#         net_sale_value = net_amount - out_put_gst_value

#         discount_percentage = to_decimal(r.get("discount_percentage") or 0)
#         margin_percent = discounted_margin if discount_percentage > 0 else fresh_margin
#         margin_amount = (net_amount * margin_percent) / Decimal(100)
#         inv_base_value = net_sale_value - margin_amount

#         # -----------------------------
#         # INPUT GST FROM PURCHASE
#         # -----------------------------
#         item_code = r.get("item_code")
#         st_percent, gst_amount_per_item, single_item_rate = get_item_input_gst(item_code, company)

#         input_gst_value = gst_amount_per_item 
#         custom_invoice_amount = single_item_rate
#         # -----------------------------
#         # TOTAL SERIAL VALUE = base + gst
#         # -----------------------------
#         total_serial_invoice_value = custom_invoice_amount + input_gst_value

#         # -----------------------------
#         # CD/DN Difference
#         # -----------------------------
#         invoice_value = inv_base_value + input_gst_value
#         cd_dn_value = total_serial_invoice_value - invoice_value
#         # cd_dn_value = invoice_value - total_serial_invoice_value
#         # -----------------------------
#         # STORE PROCESSED VALUES
#         # -----------------------------
#         r["gst_percent"] = float(gst_percent)
#         r["gst_amount"] = round2(out_put_gst_value)
#         r["net_sale_value"] = round2(net_sale_value)
#         r["inv_base_value"] = round2(inv_base_value)
#         r["in_put_gst_value"] = round2(input_gst_value)
#         r["base_value"] = round2(net_sale_value)
#         r["margin_percent"] = float(margin_percent)
#         r["margin_amount"] = round2(margin_amount)
#         r["total_amount"] = round2(to_decimal(r.get("total_amount") or 0))
#         r["discount_amount"] = round2(to_decimal(r.get("discount_amount") or 0))
#         r["net_amount"] = round2(net_amount)
#         r["invoice_value"] = round2(invoice_value)
#         r["debit_note"] = round2(cd_dn_value)

#         processed.append(r)

#     return {
#         "invoice_list": processed,
#         "period_type": period_type,
#         "from_date": str(from_date),
#         "to_date": str(to_date)
#     }

from decimal import Decimal, ROUND_HALF_UP

def R2(val):
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
@frappe.whitelist()
def fetch_invoices(company, from_date=None, to_date=None):

    import frappe
    from decimal import Decimal
    from frappe.utils import getdate

    # -------------------------------------------------------------------
    # SMALL HELPER → ALWAYS RETURN DECIMAL
    # -------------------------------------------------------------------
    def D(val):
        return Decimal(str(val or 0))

    # -------------------------------------------------------------------
    # FETCH CONFIG VALUES
    # -------------------------------------------------------------------
    config = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        [
            "fresh_margin",
            "discounted_margin",
            "sis_debit_note_creation_period",
            "auto_credit_note_percent",
            "discount_threshold",
        ],
        as_dict=True
    )

    if not config or not config.sis_debit_note_creation_period:
        frappe.throw("Please set Debit Note Creation Period in SIS Configuration")

    fresh_margin = D(config.fresh_margin)
    discounted_margin = D(config.discounted_margin)
    period_type = config.sis_debit_note_creation_period
    auto_credit_note_percent = D(config.auto_credit_note_percent)
    discount_threshold = D(config.discount_threshold)

    # -------------------------------------------------------------------
    # CLEAN DATE INPUTS
    # -------------------------------------------------------------------
    from_date = None if not from_date or from_date in ["", "null"] else from_date
    to_date = None if not to_date or to_date in ["", "null"] else to_date

    # -------------------------------------------------------------------
    # SET DATE RANGE
    # -------------------------------------------------------------------
    # if period_type == "Date Range":
    #     if not from_date or not to_date:
    #         from_date, to_date = frappe.db.get_value(
    #             "SIS Configuration",
    #             {"company": company},
    #             ["from_date", "to_date"]
    #         )

    #     if not from_date or not to_date:
    #         frappe.throw("Please select From Date and To Date")
    # else:
    #     from_date, to_date = get_period_dates(period_type)

    # from_date = getdate(from_date)
    # to_date = getdate(to_date)

    # if from_date > to_date:
    #     frappe.throw("From Date cannot be greater than To Date")

    # 🔥 If frontend sent dates → ALWAYS use them
    if from_date and to_date:
        pass

    # fallback to config (only if frontend empty)
    elif period_type == "Date Range":
        from_date, to_date = frappe.db.get_value(
            "SIS Configuration",
            {"company": company},
            ["from_date", "to_date"]
        )

    # fallback to period type
    else:
        from_date, to_date = get_period_dates(period_type)

    if not from_date or not to_date:
        frappe.throw("Please select From Date and To Date")

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("From Date cannot be greater than To Date")

    # -------------------------------------------------------------------
    # FETCH DELIVERY NOTE DATA
    # -------------------------------------------------------------------
    invoices = frappe.db.sql("""
        SELECT 
            dn.name AS name,
            dn.posting_date,
            dn.posting_time,
            dn.customer,
            dn.is_return,              -- ✅ CORRECT
            dni.name AS sii_name,
            dni.item_code,
            dni.item_name,
            dni.qty,
            dni.rate,
            dni.price_list_rate,
            dni.discount_percentage,
            dni.custom_is_promo_scheme,
            dni.custom_promo_discount_percent,
            (dni.qty * dni.price_list_rate) AS total_amount
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
        WHERE 
            dn.company = %s
            AND dn.posting_date BETWEEN %s AND %s
            AND dn.docstatus = 1
        ORDER BY dn.posting_date DESC, dn.posting_time DESC, dn.name, dni.idx
    """, (company, from_date, to_date), as_dict=True)

    processed = []

    # -------------------------------------------------------------------
    # PROCESS EACH ITEM
    # -------------------------------------------------------------------
    for r in invoices:

        total_amount = D(r.total_amount)

        discount_percentage = D(r.discount_percentage)
        promo_discount = D(r.custom_promo_discount_percent)
        is_promo = r.custom_is_promo_scheme

        # 🔥 PROMO DISCOUNT OVERRIDE
        if is_promo and promo_discount > 0:
            discount_percentage = promo_discount

        discount_amount = (total_amount * discount_percentage) / D(100)
        net_amount = total_amount - discount_amount

        # -------------------------------------------------------------------
        # OUTPUT GST
        # -------------------------------------------------------------------
        gst_percent = D(5) if net_amount <= D(2500) else D(18)
        out_put_gst_value = net_amount * gst_percent / (D(100) + gst_percent)
        out_put_gst_value = R2(out_put_gst_value)
        net_sale_value = net_amount - out_put_gst_value

        # -------------------------------------------------------------------
        # MARGIN LOGIC
        # -------------------------------------------------------------------
        if is_promo or discount_percentage > 0:
            margin_percent = discounted_margin
        else:
            margin_percent = fresh_margin

        margin_amount = (net_amount * margin_percent) / D(100)
        inv_base_value = net_sale_value - margin_amount
        inv_base_value = R2(inv_base_value)
        # -------------------------------------------------------------------
        # INPUT GST
        # -------------------------------------------------------------------
        st_percent, gst_amount_per_item, single_item_rate = get_item_input_gst(
            r.item_code, company
        )

        gst_amount_per_item = D(gst_amount_per_item)
        single_item_rate = D(single_item_rate)

        # total_serial_invoice_value = single_item_rate + gst_amount_per_item
        # invoice_value = inv_base_value + gst_amount_per_item
        # debit_note_value = total_serial_invoice_value - invoice_value

        # Return case → GST negative
        is_return = r.is_return or 0   # 0 or 1
        if is_return == 1:
           gst_amount_per_item = -gst_amount_per_item
           single_item_rate = -single_item_rate

        total_serial_invoice_value = single_item_rate + gst_amount_per_item
        invoice_value = inv_base_value + gst_amount_per_item
        debit_note_value = single_item_rate - inv_base_value

        # -------------------------------------------------------------------
        # FINAL UPDATE
        # -------------------------------------------------------------------
        r.update({
            "total_amount": float(total_amount),
            "discount_percentage": float(discount_percentage),
            "discount_amount": float(discount_amount),
            "net_amount": float(net_amount),
            "gst_percent": float(gst_percent),
            "gst_amount": float(out_put_gst_value),
            "net_sale_value": float(net_sale_value),
            "margin_percent": float(margin_percent),
            "margin_amount": float(margin_amount),
            "inv_base_value": float(inv_base_value),
            "in_put_gst_value": float(gst_amount_per_item),
            "invoice_value": float(invoice_value),
            "debit_note": float(debit_note_value),
        })

        processed.append(r)

    # -------------------------------------------------------------------
    return {
        "invoice_list": processed,
        "period_type": period_type,
        "from_date": str(from_date),
        "to_date": str(to_date),
    }


# ======================================================
#       PERIOD DATE CALCULATION LOGIC
# ======================================================

def get_period_dates(period_type):
    today = getdate(nowdate())
    import calendar

    # WEEKLY -- Monday to Sunday
    if period_type == "Weekly":
        weekday = today.weekday()
        start = add_days(today, -weekday)
        end = add_days(start, 6)
        return start, end

    # FORTNIGHTLY
    elif period_type == "Fortnightly":
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        if today.day <= 15:
            return first_day, first_day.replace(day=15)
        else:
            return first_day.replace(day=16), last_day

    # MONTHLY
    elif period_type == "Monthly":
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        return first_day, last_day

    return today, today




import frappe
from frappe.utils import today


@frappe.whitelist()
def create_debit_note(company, period_type=None, invoices=None):

    invoices = frappe.parse_json(invoices or [])

    if not invoices:
        frappe.throw("No invoice data received. Please refresh page.")

    company_abbr = frappe.db.get_value("Company", company, "abbr")

    # Fetch config
    config = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        ["auto_credit_note_percent", "discount_threshold", "sis_debit_note_creation_period"],
        as_dict=True
    )

    auto_credit_note_percent = config.auto_credit_note_percent
    discount_threshold = config.discount_threshold
    period_type = period_type or config.sis_debit_note_creation_period

    # if not auto_credit_note_percent:
    #     frappe.throw("Auto Credit Note Percent missing in SIS Configuration.")

    if discount_threshold is None:
        frappe.throw("Discount Threshold missing in SIS Configuration.")

    # Date Range
    from_date, to_date = get_period_dates(period_type)

    # Penalty Account
    penalty_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "root_type": "Expense",
            "name": ["like", f"TZU Penalty%{company_abbr}"]
        },
        "name"
    )

    if not penalty_account:
        frappe.throw(f"Create Penalty Expense Account like 'TZU Penalty Exp - {company_abbr}'.")

    # --- Create Journal Entry ---
    je = frappe.new_doc("Journal Entry")
    je.posting_date = today()
    je.company = company
    je.voucher_type = "Credit Note"

    total_penalty = 0
    item_codes = []

    # ---------------------------------------------------------
    # 🔥 CHECK DUPLICATION ONLY IN SUBMITTED JOURNAL ENTRIES
    # ---------------------------------------------------------
    existing_invoices = frappe.db.sql("""
        SELECT ja.custom_penalty_invoice
        FROM `tabJournal Entry Account` ja
        JOIN `tabJournal Entry` je ON ja.parent = je.name
        WHERE ja.custom_penalty_invoice IS NOT NULL
        AND ja.custom_penalty_invoice != ''
        AND je.voucher_type = 'Credit Note'
        AND je.docstatus = 1
    """, as_dict=True)


    already_posted = {d.custom_penalty_invoice for d in existing_invoices}

    # ---------------------------------------------------------
    # 🔥 PROCESS INVOICES (avoid duplicates)
    # ---------------------------------------------------------
    for row in invoices:

        discount = row.get("discount_percentage", 0)
        if discount <= discount_threshold:
            continue

        invoice_name = row.get("name")
        item_code = row.get("item_code")

        # Realized / Net Sale Value (Invoice Base Value)
        invoice_value = Decimal(str(row.get("invoice_value") or 0))

        # -----------------------------
        # ⭐ NEW: CD/DN Value From Table
        # -----------------------------
        passed_penalty = row.get("debit_note") or row.get("cd_dn") or row.get("cd_dn_value")

        # Skip duplicates
        if invoice_name in already_posted:
            continue

        # Skip if invoice already a credit note
        # si_status = frappe.db.get_value(
        #     "Sales Invoice",
        #     invoice_name,
        #     ["status", "is_return"],
        #     as_dict=True
        # )
        # if si_status and (si_status.status == "Credit Note" or si_status.is_return == 1):
        #     continue

        # --------------------------
        # Fetch HO purchase GST + Value
        # --------------------------
        # input_gst_percent, input_gst_value, purchase_value = get_purchase_input_gst(item_code, company)
        st_percent, gst_amount_per_item, single_item_rate = get_item_input_gst(item_code, company)
        purchase_value = single_item_rate
        # -------------------------------------------------
        # ⭐ FINAL LOGIC — USE CD/DN VALUE IF PASSED
        # -------------------------------------------------
        if passed_penalty not in (None, "", 0):
            penalty_amount = float(passed_penalty)
        elif purchase_value > 0:
            penalty_amount = float(purchase_value - invoice_value)
        else:
            penalty_amount = float((invoice_value * Decimal(str(auto_credit_note_percent))) / 100)

        # accumulate
        total_penalty += penalty_amount
        item_codes.append(item_code)

        # -----------------------------
        # Add journal entry line
        # -----------------------------
        je.append("accounts", {
            "account": penalty_account,
            "credit_in_account_currency": penalty_amount,
            "custom_penalty_invoice": invoice_name,
            "remarks": (
                f"{item_code} (Disc {discount}%, "
                f"Threshold {discount_threshold}%, "
                f"Penalty passed from UI or HO difference)"
            )
        })




    if total_penalty == 0:
        return {"message": "All invoices already processed or below threshold."}

    # ---------------- Supplier Auto Fetch ----------------
    # supplier_info = frappe.db.sql("""
    #     SELECT pi.supplier
    #     FROM `tabPurchase Invoice` pi
    #     JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
    #     WHERE pii.item_code IN %s
    #       AND pi.company = %s
    #     ORDER BY pi.posting_date DESC
    #     LIMIT 1
    # """, (tuple(item_codes), company), as_dict=True)
    supplier_info = frappe.db.sql("""
        SELECT pr.supplier
        FROM `tabPurchase Receipt` pr
        JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE pri.item_code IN %s
        AND pr.company = %s
        AND pr.docstatus = 1
        ORDER BY pr.posting_date DESC
        LIMIT 1
        """, (tuple(item_codes), company), as_dict=True)

    if not supplier_info:
        frappe.throw("Supplier could not be identified for these items.")

    supplier = supplier_info[0].supplier

    # Payable account
    creditors_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "is_group": 0,
            "account_type": "Payable",
            "root_type": "Liability",
            "name": ["like", "%Creditors%"]
        },
        "name"
    )

    if not creditors_account:
        frappe.throw(f"No Creditors account found for company {company}")

    # Summary row
    je.append("accounts", {
        "account": creditors_account,
        "debit_in_account_currency": total_penalty,
        "party_type": "Supplier",
        "party": supplier,
        "custom_penalty_invoice": "Summary",
        "remarks": "Total Penalty Summary"
    })

    # Save JE
    je.insert(ignore_permissions=True)
    # je.submit()  # enable after testing

    return {
        "message": f"Journal Entry Created Successfully: {je.name}",
        "journal_entry": je.name
    }
