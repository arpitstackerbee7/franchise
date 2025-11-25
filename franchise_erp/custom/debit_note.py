import frappe

@frappe.whitelist()
def fetch_invoices(company, from_date, to_date):

    invoices = frappe.db.sql("""
        SELECT 
            si.name,
            si.posting_date,
            si.customer,
            si.grand_total,
            sii.item_code,
            sii.qty,
            sii.rate,
            sii.distributed_discount_amount,
            sii.net_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
        ORDER BY si.posting_date
    """, (company, from_date, to_date), as_dict=True)

    return {
        "invoice_list": invoices,
        "message": f"{len(invoices)} invoice items found."
    }



@frappe.whitelist()
def create_debit_note(company, from_date, to_date):

    # Check if already generated
    existing = frappe.get_all(
        "Debit Note Log",
        filters={
            "company": company,
            "from_date": from_date,
            "to_date": to_date
        }
    )

    if existing:
        return "Debit Note already created for this period."

    # Fetch SIS Settings
    config = frappe.get_value(
        "SIS Configuration",
        {"company": company},
        "auto_credit_note_percent"
    )

    percent = float(config)

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]]
        },
        fields=["name"]
    )

    total = 0

    for inv in invoices:
        si = frappe.get_doc("Sales Invoice", inv.name)

        for item in si.items:
            # Calculate value
            total += item.net_amount * percent / 100

    # Create Journal Entry (Credit Note)
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Credit Note",
        "posting_date": to_date,
        "company": company,
        "accounts": [
            {
                "account": "Debtors",
                "credit_in_account_currency": total
            }
        ],
        "user_remark": f"Auto Debit Note for {from_date} to {to_date}"
    })

    je.insert()
    je.submit()

    # Log creation
    log = frappe.get_doc({
        "doctype": "Debit Note Log",
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "debit_note": je.name
    })

    log.insert()

    return f"Debit Note Created: {je.name}"
