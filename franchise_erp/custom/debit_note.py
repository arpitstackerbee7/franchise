import frappe

# @frappe.whitelist()
# def fetch_invoices(company, from_date, to_date):

#     invoices = frappe.db.sql("""
#         SELECT 
#             si.name,
#             si.posting_date,
#             si.customer,
#             si.grand_total,
#             sii.item_code,
#             sii.qty,
#             sii.rate,
#             sii.distributed_discount_amount,
#             sii.net_amount
#         FROM `tabSales Invoice` si
#         JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
#         WHERE 
#             si.company = %s
#             AND si.posting_date BETWEEN %s AND %s
#             AND si.docstatus = 1
#         ORDER BY si.posting_date
#     """, (company, from_date, to_date), as_dict=True)

#     return {
#         "invoice_list": invoices,
#         "message": f"{len(invoices)} invoice items found."
#     }

# @frappe.whitelist()
# def fetch_invoices(company, from_date, to_date):

#     invoices = frappe.db.sql("""
#     SELECT 
#         si.name,
#         si.posting_date,
#         si.customer,
#         si.grand_total,
#         si.additional_discount_percentage,
#         sii.item_code,
#         sii.qty,
#         sii.rate,
#         sii.distributed_discount_amount,
#         sii.net_amount
#     FROM `tabSales Invoice` si
#     JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
#     WHERE 
#         si.company = %s
#         AND si.posting_date BETWEEN %s AND %s
#         AND si.docstatus = 1
#         AND si.additional_discount_percentage > 10
#     ORDER BY si.posting_date
# """, (company, from_date, to_date), as_dict=True)


#     return {
#         "invoice_list": invoices,
#         "message": f"{len(invoices)} invoice items found with discount > 10%."
#     }
@frappe.whitelist()
def fetch_invoices(company, from_date, to_date):

    invoices = frappe.db.sql("""
        SELECT 
            si.name AS name,
            si.posting_date,
            si.customer,
            si.additional_discount_percentage,

            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate,
            sii.discount_percentage,

            (sii.qty * sii.rate) AS total_amount,

            -- Net Amount after applying invoice discount
            ((sii.qty * sii.rate) - 
             (((sii.qty * sii.rate) * sii.discount_percentage) / 100)
            ) AS net_amount

        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name

        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1

        ORDER BY si.posting_date, si.name, sii.idx
    """, (company, from_date, to_date), as_dict=True)

    return {
        "invoice_list": invoices,
        "message": f"{len(invoices)} invoice items found."
    }

# @frappe.whitelist()
# def create_debit_note(company, from_date, to_date):

#     # Get company abbreviation
#     company_abbr = frappe.db.get_value("Company", company, "abbr")

#     # Get Debit Note % from SIS Configuration
#     debit_note_percent = frappe.db.get_value(
#         "SIS Configuration",
#         {"company": company},
#         "debit_note_percent"
#     )

#     if not debit_note_percent:
#         frappe.throw(
#             f"Debit Note % not configured. Please set it in SIS Configuration for {company}."
#         )

#     # Get dynamic penalty expense account
#     penalty_account = frappe.db.get_value(
#         "Account",
#         {
#             "company": company,
#             "root_type": "Expense",
#             "name": ["like", f"SIS Penalty%{company_abbr}"]
#         },
#         "name"
#     )

#     if not penalty_account:
#         frappe.throw(
#             f"No Penalty Expense account found for {company}. "
#             f"Please create an account like 'SIS Penalty Exp - {company_abbr}'"
#         )

#     # Fetch invoices
#     invoices = frappe.db.sql("""
#         SELECT 
#             si.name AS invoice,
#             sii.net_amount,
#             sii.discount_percentage
#         FROM `tabSales Invoice` si
#         JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
#         WHERE 
#             si.company = %s
#             AND si.posting_date BETWEEN %s AND %s
#             AND si.docstatus = 1
#     """, (company, from_date, to_date), as_dict=True)

#     if not invoices:
#         return {"message": "No invoices found in the selected range."}

#     # Create Journal Entry
#     je = frappe.new_doc("Journal Entry")
#     je.posting_date = frappe.utils.today()
#     je.company = company
#     je.voucher_type = "Credit Note"

#     total_penalty = 0

#     # Add each invoice credit line
#     for inv in invoices:
#         penalty_amount = (inv.net_amount * float(debit_note_percent)) / 100
#         total_penalty += penalty_amount

#         je.append("accounts", {
#             "account": penalty_account,
#             "credit_in_account_currency": penalty_amount,
#             "custom_penalty_invoice": inv.invoice
#         })

#     # Add balancing Debit line
#     je.append("accounts", {
#         "account": penalty_account,
#         "debit_in_account_currency": total_penalty,
#         "custom_penalty_invoice": "Penalty Summary"
#     })

#     je.insert(ignore_permissions=True)
#     # je.submit()     # Enable if you want auto submit

#     return {
#         "message": f"Journal Entry Created Successfully: {je.name}",
#         "journal_entry": je.name
#     }

import frappe
from frappe.utils import today

@frappe.whitelist()
def create_debit_note(company, from_date, to_date):

    company_abbr = frappe.db.get_value("Company", company, "abbr")

    # Read percent from SIS Configuration
    auto_credit_note_percent = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        "auto_credit_note_percent"
    )

    if not auto_credit_note_percent:
        frappe.throw("Please set Auto Credit Note Percent in SIS Configuration.")

    # Get Penalty Expense Account dynamically
    penalty_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "root_type": "Expense",
            "name": ["like", f"SIS Penalty%{company_abbr}"]
        },
        "name"
    )

    if not penalty_account:
        frappe.throw(
            f"No Penalty Expense account found for {company}. "
            f"Create account like 'SIS Penalty Exp - {company_abbr}'."
        )

    # Fetch invoice ITEMS where discount is greater
    items = frappe.db.sql("""
        SELECT 
            si.name AS invoice,
            si.customer,
            sii.item_code,
            sii.discount_percentage,
            (sii.qty * sii.rate) AS total_amount,
            (
                (sii.qty * sii.rate) -
                (((sii.qty * sii.rate) * sii.discount_percentage) / 100)
            ) AS net_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND sii.discount_percentage > %s
        ORDER BY si.posting_date, si.name
    """, (company, from_date, to_date, auto_credit_note_percent), as_dict=True)

    if not items:
        return {
            "message": f"No invoice items found with discount > {auto_credit_note_percent}%."
        }

    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.posting_date = today()
    je.company = company
    je.voucher_type = "Credit Note"

    total_penalty = 0

    # Add each line item to JE
    # Add each line item to JE, avoid duplicates
    # Add each line item to JE, avoid duplicates in submitted JEs only
    for row in items:
        # Check if this invoice item already has a JE line in a submitted JE
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
            # Skip this item, already recorded in a submitted JE
            continue

        penalty_amount = (row.net_amount * auto_credit_note_percent) / 100
        total_penalty += penalty_amount

        je.append("accounts", {
            "account": penalty_account,
            "credit_in_account_currency": penalty_amount,
            "custom_penalty_invoice": row.invoice,
            "remarks": f"{row.item_code} (Disc {row.discount_percentage}%)"
        })



    # Fetch supplier who supplied these items to the company
    # Assuming using Purchase Invoice
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
        frappe.throw(f"No supplier found for the sold items supplied to {company}")

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

    # Add balancing debit row for invoice summary with party_type and type
    je.append("accounts", {
        "account": creditors_account,
        "debit_in_account_currency": total_penalty,
        "custom_penalty_invoice": "Invoice Summary",
        "party_type": "Supplier",
        "party": supplier_name,
        "type": "Payable",
        "remarks": "Balance Penalty Entry"
    })

    je.insert(ignore_permissions=True)
    # je.submit()  # Uncomment if you want to auto-submit

    return {
        "message": f"Journal Entry Created Successfully: {je.name}",
        "journal_entry": je.name
    }
