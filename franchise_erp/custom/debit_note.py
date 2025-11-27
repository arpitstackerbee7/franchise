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

import frappe
from frappe.utils import getdate, add_days, nowdate
from datetime import date
import calendar


@frappe.whitelist()
def fetch_invoices(company, from_date=None, to_date=None):

    # Read SIS Configuration value
    period_type = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        "sis_debit_note_creation_period"
    )

    # If no value found in config
    if not period_type:
        frappe.throw("Please set 'Debit Note Creation Period' in SIS Configuration.")

    # Auto calculate from_date and to_date from configuration
    from_date, to_date = get_period_dates(period_type)

    # ----------------- FETCH INVOICES --------------------
    invoices = frappe.db.sql("""
        SELECT 
            si.name AS name,
            si.posting_date,
            si.posting_time,
            si.customer,
            si.additional_discount_percentage,

            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate,
            sii.price_list_rate,
            sii.discount_percentage,
            sii.price_list_rate,

            (sii.qty * sii.price_list_rate) AS total_amount,

            ((sii.qty * sii.price_list_rate) * sii.discount_percentage / 100) AS discount_amount,

            ((sii.qty * sii.price_list_rate) - 
             (((sii.qty * sii.price_list_rate) * sii.discount_percentage) / 100)
            ) AS net_amount

        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name

        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1

        ORDER BY si.posting_date DESC, si.posting_time DESC, si.name, sii.idx
    """, (company, from_date, to_date), as_dict=True)

    return {
        "invoice_list": invoices,
        "period_type": period_type,
        "from_date": from_date,
        "to_date": to_date,
        "message": f"{len(invoices)} items found for period {from_date} to {to_date}."
    }



# ======================================================
#       PERIOD DATE CALCULATION LOGIC
# ======================================================

def get_period_dates(period_type):
    today = getdate(nowdate())

    # ---------------- WEEKLY (Monday → Sunday) ----------------
    if period_type == "Weekly":
        weekday = today.weekday()  # Monday=0
        start = add_days(today, -weekday)
        end = add_days(start, 6)
        return start, end


    # ---------------- FORTNIGHTLY (1–15 / 16–End) -------------
    elif period_type == "Fortnightly":
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        if today.day <= 15:
            # 1–15
            return first_day, first_day.replace(day=15)
        else:
            # 16–Month End
            return first_day.replace(day=16), last_day


    # ---------------- MONTHLY (Whole Current Month) ----------- 
    elif period_type == "Monthly":
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        return first_day, last_day


    # ---------------- DEFAULT (Fallback) ----------------------
    return today, today


import frappe
from frappe.utils import today

@frappe.whitelist()
def create_debit_note(company, from_date, to_date):

    company_abbr = frappe.db.get_value("Company", company, "abbr")

    # Read values from SIS Configuration
    config = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        ["auto_credit_note_percent", "discount_threshold"],
        as_dict=True
    )


    if not config:
        frappe.throw("Please set Auto Credit Note Percent and Discount Threshold in SIS Configuration.")

    auto_credit_note_percent = config.auto_credit_note_percent        # Penalty %
    discount_threshold = config.discount_threshold                    # Allowed Max %

    if not auto_credit_note_percent:
        frappe.throw("Auto Credit Note Percent is missing in SIS Configuration.")

    if discount_threshold is None:
        frappe.throw("Discount Threshold is missing in SIS Configuration.")

    # Get Penalty Expense Account
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
        frappe.throw(
            f"No Penalty Expense account found for {company}. "
            f"Create account like 'TZU Penalty Exp - {company_abbr}'."
        )

    # Fetch invoice ITEMS where discount exceeds threshold
    items = frappe.db.sql("""
        SELECT 
            si.name AS invoice,
            si.customer,
            sii.item_code,
            sii.discount_percentage,
            (sii.qty * sii.rate) AS total_amount,
            ((sii.qty * sii.rate)) AS net_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND sii.discount_percentage > %s
        ORDER BY si.posting_date, si.name
    """, (company, from_date, to_date, discount_threshold), as_dict=True)

    if not items:
        return {
            "message": f"No invoice items found with discount > {discount_threshold}% (threshold)."
        }

    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.posting_date = today()
    je.company = company
    je.voucher_type = "Credit Note"

    total_penalty = 0

    # Create JE items (credit rows)
    for row in items:

        # Check duplicate entry only in submitted JEs
        existing_entry = frappe.db.sql("""
            SELECT ja.name
            FROM `tabJournal Entry Account` ja
            JOIN `tabJournal Entry` je ON je.name = ja.parent
            WHERE ja.custom_penalty_invoice = %s
              AND ja.account = %s
              AND je.docstatus = 1
            LIMIT 1
        """, (row.invoice, penalty_account))

        if existing_entry:
            continue

        # Calculate penalty based on Auto Credit Note % (always fixed)
        penalty_amount = (row.net_amount * auto_credit_note_percent) / 100
        total_penalty += penalty_amount

        je.append("accounts", {
            "account": penalty_account,
            "credit_in_account_currency": penalty_amount,
            "custom_penalty_invoice": row.invoice,
            "remarks": (
                f"{row.item_code} "
                f"(Disc {row.discount_percentage}%, "
                f"Threshold {discount_threshold}%, "
                f"Penalty {auto_credit_note_percent}%)"
            )
        })

    # If no items added due to duplicates
    if total_penalty == 0:
        return {"message": "All invoice items already have penalty entries. No new debit note created."}

    # Find the supplier who supplied these items
    supplier_info = frappe.db.sql("""
        SELECT pi.supplier
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE pii.item_code IN %s
          AND pi.company = %s
        ORDER BY pi.posting_date DESC
        LIMIT 1
    """, ([row.item_code for row in items], company), as_dict=True)

    if supplier_info:
        supplier_name = supplier_info[0].supplier
    else:
        frappe.throw("No supplier found for the sold items.")

    # Creditors account
    creditors_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "account_type": "Payable",
            "root_type": "Liability",
            "name": ["like", "%Creditors%"],
            "is_group": 0
        },
        "name"
    )

    if not creditors_account:
        frappe.throw(f"No Creditors account found for company {company}")

    # Add Debit row (balance row)
    je.append("accounts", {
        "account": creditors_account,
        "debit_in_account_currency": total_penalty,
        "custom_penalty_invoice": "Invoice Summary",
        "party_type": "Supplier",
        "party": supplier_name,
        "type": "Payable",
        "remarks": "Total Penalty Summary"
    })

    # Save JE
    je.insert(ignore_permissions=True)
    # je.submit() # enable when tested

    return {
        "message": f"Journal Entry Created Successfully: {je.name}",
        "journal_entry": je.name
    }
