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

def get_item_input_gst(item_code, company):
    """
    Fetch INPUT GST directly from last Purchase Invoice Item
    using FINAL calculated fields
    """

    pii = frappe.db.sql("""
        SELECT
            pii.custom_single_item_rate AS single_item_rate,
            pii.custom_single_item_input_gst_amount AS gst_amount
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE
            pii.item_code = %s
            AND pi.company = %s
            AND pi.docstatus = 1
        ORDER BY pi.posting_date DESC, pi.posting_time DESC, pii.creation DESC
        LIMIT 1
    """, (item_code, company), as_dict=True)

    if not pii:
        return Decimal("0"), Decimal("0"), Decimal("0")

    row = pii[0]

    single_item_rate = Decimal(str(row.single_item_rate or 0))
    gst_amount_per_item = Decimal(str(row.gst_amount or 0))

    # GST % derive (optional, if needed)
    gst_percent = (
        (gst_amount_per_item * 100 / single_item_rate)
        if single_item_rate > 0 else Decimal("0")
    )

    return gst_percent, gst_amount_per_item, single_item_rate

@frappe.whitelist()
def fetch_invoices(company, from_date=None, to_date=None):
    # -------------------------------------------------------------------
    # FETCH CONFIG VALUES
    # -------------------------------------------------------------------
    fresh_margin, discounted_margin, period_type, auto_credit_note_percent, discount_threshold = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        ["fresh_margin", "discounted_margin", "sis_debit_note_creation_period", "auto_credit_note_percent", "discount_threshold"]
    )

    if not period_type:
        frappe.throw(_("Please set Debit Note Creation Period in SIS Configuration"))

    fresh_margin = to_decimal(fresh_margin or 0)
    discounted_margin = to_decimal(discounted_margin or 0)
    auto_credit_note_percent = to_decimal(auto_credit_note_percent or 0)
    discount_threshold = to_decimal(discount_threshold or 0)

    # -------------------------------------------------------------------
    # CLEAN DATE INPUTS
    # -------------------------------------------------------------------
    if not from_date or from_date in ["", "null"]:
        from_date = None

    if not to_date or to_date in ["", "null"]:
        to_date = None

    # -------------------------------------------------------------------
    # SET DATE RANGE USING PERIOD TYPE
    # -------------------------------------------------------------------
    if period_type == "Fortnightly":
        from_date, to_date = get_period_dates("Fortnightly")
    else:
        if not from_date or not to_date:
            from_date, to_date = get_period_dates(period_type)

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    frappe.log_error("DATE_RANGE_USED", f"From: {from_date}, To: {to_date}, Period: {period_type}")

    # -------------------------------------------------------------------
    # FETCH SALES INVOICE DATA
    # -------------------------------------------------------------------
    invoices = frappe.db.sql("""
        SELECT 
            si.name AS name,
            si.posting_date,
            si.posting_time,
            si.customer,
            sii.name AS sii_name,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate,
            sii.price_list_rate,
            sii.discount_percentage,
            (sii.qty * sii.price_list_rate) AS total_amount,
            ((sii.qty * sii.price_list_rate) * sii.discount_percentage / 100) AS discount_amount,
            ((sii.qty * sii.price_list_rate) - ((sii.qty * sii.price_list_rate) * sii.discount_percentage / 100)) AS net_amount
        FROM `tabSales Invoice` AS si
        JOIN `tabSales Invoice Item` AS sii ON sii.parent = si.name
        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
        ORDER BY si.posting_date DESC, si.posting_time DESC, si.name, sii.idx
    """, (company, from_date, to_date), as_dict=True)


    processed = []

    # -------------------------------------------------------------------
    # PROCESS EACH ITEM
    # -------------------------------------------------------------------
    for r in invoices:
        net_amount = to_decimal(r.get("net_amount") or 0)

        # -----------------------------
        # OUTPUT GST SLAB LOGIC
        # -----------------------------
        if net_amount <= Decimal("2500"):
            gst_percent = Decimal("5.0")
        else:
            gst_percent = Decimal("18.0")

        out_put_gst_value = net_amount * gst_percent / (100 + gst_percent)
        net_sale_value = net_amount - out_put_gst_value

        discount_percentage = to_decimal(r.get("discount_percentage") or 0)
        margin_percent = discounted_margin if discount_percentage > 0 else fresh_margin
        margin_amount = (net_amount * margin_percent) / Decimal(100)
        inv_base_value = net_sale_value - margin_amount

        # -----------------------------
        # INPUT GST FROM PURCHASE
        # -----------------------------
        item_code = r.get("item_code")
        st_percent, gst_amount_per_item, single_item_rate = get_item_input_gst(item_code, company)

        input_gst_value = gst_amount_per_item 
        custom_invoice_amount = single_item_rate
        # -----------------------------
        # TOTAL SERIAL VALUE = base + gst
        # -----------------------------
        total_serial_invoice_value = custom_invoice_amount + input_gst_value

        # -----------------------------
        # CD/DN Difference
        # -----------------------------
        invoice_value = inv_base_value + input_gst_value
        cd_dn_value = total_serial_invoice_value - invoice_value

        # -----------------------------
        # STORE PROCESSED VALUES
        # -----------------------------
        r["gst_percent"] = float(gst_percent)
        r["gst_amount"] = round2(out_put_gst_value)
        r["net_sale_value"] = round2(net_sale_value)
        r["inv_base_value"] = round2(inv_base_value)
        r["in_put_gst_value"] = round2(input_gst_value)
        r["base_value"] = round2(net_sale_value)
        r["margin_percent"] = float(margin_percent)
        r["margin_amount"] = round2(margin_amount)
        r["total_amount"] = round2(to_decimal(r.get("total_amount") or 0))
        r["discount_amount"] = round2(to_decimal(r.get("discount_amount") or 0))
        r["net_amount"] = round2(net_amount)
        r["invoice_value"] = round2(invoice_value)
        r["debit_note"] = round2(cd_dn_value)

        processed.append(r)

    return {
        "invoice_list": processed,
        "period_type": period_type,
        "from_date": str(from_date),
        "to_date": str(to_date)
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

# @frappe.whitelist()
# def create_debit_note(company, period_type=None, invoices=None):

#     invoices = frappe.parse_json(invoices or [])

#     if not invoices:
#         frappe.throw("No invoice data received. Please refresh page.")

#     company_abbr = frappe.db.get_value("Company", company, "abbr")

#     # Fetch config
#     config = frappe.db.get_value(
#         "SIS Configuration",
#         {"company": company},
#         ["auto_credit_note_percent", "discount_threshold", "sis_debit_note_creation_period"],
#         as_dict=True
#     )

#     auto_credit_note_percent = config.auto_credit_note_percent
#     discount_threshold = config.discount_threshold
#     period_type = period_type or config.sis_debit_note_creation_period

#     if not auto_credit_note_percent:
#         frappe.throw("Auto Credit Note Percent missing in SIS Configuration.")

#     if discount_threshold is None:
#         frappe.throw("Discount Threshold missing in SIS Configuration.")

#     # Date Range
#     from_date, to_date = get_period_dates(period_type)

#     # Penalty Account
#     penalty_account = frappe.db.get_value(
#         "Account",
#         {
#             "company": company,
#             "root_type": "Expense",
#             "name": ["like", f"TZU Penalty%{company_abbr}"]
#         },
#         "name"
#     )

#     if not penalty_account:
#         frappe.throw(f"Create Penalty Expense Account like 'TZU Penalty Exp - {company_abbr}'.")

#     # --- Create Journal Entry ---
#     je = frappe.new_doc("Journal Entry")
#     je.posting_date = today()
#     je.company = company
#     je.voucher_type = "Credit Note"

#     total_penalty = 0
#     item_codes = []

#     # ---------------------------------------------------------
#     # 🔥 CHECK DUPLICATION ONLY IN SUBMITTED JOURNAL ENTRIES
#     # ---------------------------------------------------------
#     existing_invoices = frappe.db.sql("""
#         SELECT ja.custom_penalty_invoice
#         FROM `tabJournal Entry Account` ja
#         JOIN `tabJournal Entry` je ON ja.parent = je.name
#         WHERE ja.custom_penalty_invoice IS NOT NULL
#         AND ja.custom_penalty_invoice != ''
#         AND je.voucher_type = 'Credit Note'
#         AND je.docstatus = 1
#     """, as_dict=True)


#     already_posted = {d.custom_penalty_invoice for d in existing_invoices}

#     # ---------------------------------------------------------
#     # 🔥 PROCESS INVOICES (avoid duplicates)
#     # ---------------------------------------------------------
#     for row in invoices:

#         discount = row.get("discount_percentage", 0)
#         if discount <= discount_threshold:
#             continue

#         invoice_name = row.get("name")
#         item_code = row.get("item_code")
#         invoice_value = Decimal(str(row.get("invoice_value") or 0))

#         # Skip already processed CN
#         si_status = frappe.db.get_value(
#             "Sales Invoice",
#             invoice_name,
#             ["status", "is_return"],
#             as_dict=True
#         )

#         if si_status and (si_status.status == "Credit Note" or si_status.is_return == 1):
#             continue

#         if invoice_name in already_posted:
#             continue

#         # --------------------------
#         # Fetch HO purchase GST + Value
#         # --------------------------
#         input_gst_percent, input_gst_value, purchase_value = get_purchase_input_gst(item_code, company)

#         # --------------------------
#         # FINAL DEBIT NOTE VALUE LOGIC
#         # --------------------------
#         if purchase_value > 0:
#             # HO purchase exists → use real diff
#             penalty_amount = float(purchase_value - invoice_value)

#         else:
#             # HO purchase not found → fallback %
#             penalty_amount = float((invoice_value * Decimal(str(auto_credit_note_percent))) / 100)

#         # accumulate
#         total_penalty += penalty_amount
#         item_codes.append(item_code)

#         je.append("accounts", {
#             "account": penalty_account,
#             "credit_in_account_currency": penalty_amount,
#             "custom_penalty_invoice": invoice_name,
#             "remarks": (
#                 f"{item_code} (Disc {discount}%, "
#                 f"Threshold {discount_threshold}%, "
#                 f"Penalty based on HO Purchase Difference)"
#             )
#         })



#     if total_penalty == 0:
#         return {"message": "All invoices already processed or below threshold."}

#     # ---------------- Supplier Auto Fetch ----------------
#     supplier_info = frappe.db.sql("""
#         SELECT pi.supplier
#         FROM `tabPurchase Invoice` pi
#         JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
#         WHERE pii.item_code IN %s
#           AND pi.company = %s
#         ORDER BY pi.posting_date DESC
#         LIMIT 1
#     """, (tuple(item_codes), company), as_dict=True)

#     if not supplier_info:
#         frappe.throw("Supplier could not be identified for these items.")

#     supplier = supplier_info[0].supplier

#     # Payable account
#     creditors_account = frappe.db.get_value(
#         "Account",
#         {
#             "company": company,
#             "is_group": 0,
#             "account_type": "Payable",
#             "root_type": "Liability",
#             "name": ["like", "%Creditors%"]
#         },
#         "name"
#     )

#     if not creditors_account:
#         frappe.throw(f"No Creditors account found for company {company}")

#     # Summary row
#     je.append("accounts", {
#         "account": creditors_account,
#         "debit_in_account_currency": total_penalty,
#         "party_type": "Supplier",
#         "party": supplier,
#         "custom_penalty_invoice": "Summary",
#         "remarks": "Total Penalty Summary"
#     })

#     # Save JE
#     je.insert(ignore_permissions=True)
#     # je.submit()  # enable after testing

#     return {
#         "message": f"Journal Entry Created Successfully: {je.name}",
#         "journal_entry": je.name
#     }



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

    if not auto_credit_note_percent:
        frappe.throw("Auto Credit Note Percent missing in SIS Configuration.")

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
        si_status = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            ["status", "is_return"],
            as_dict=True
        )
        if si_status and (si_status.status == "Credit Note" or si_status.is_return == 1):
            continue

        # --------------------------
        # Fetch HO purchase GST + Value
        # --------------------------
        input_gst_percent, input_gst_value, purchase_value = get_purchase_input_gst(item_code, company)

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
    supplier_info = frappe.db.sql("""
        SELECT pi.supplier
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE pii.item_code IN %s
          AND pi.company = %s
        ORDER BY pi.posting_date DESC
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
