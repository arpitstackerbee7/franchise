import frappe
from frappe.utils import flt
from collections import defaultdict

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    ReceivablePayableReport,
)



DOC_GROUP_ORDER = ["SINV", "SINV-RET", "SI", "SR", "ACC-PAY", "ACC-JV", "OTHERS"]


def get_doc_group(voucher_no: str) -> str:
    v = (voucher_no or "").strip()
    if v.startswith("SINV-RET"): return "SINV-RET"  # must be before SINV
    if v.startswith("SINV"):     return "SINV"
    if v.startswith("SR"):       return "SR"
    if v.startswith("SI"):       return "SI"
    if v.startswith("ACC-PAY"):  return "ACC-PAY"
    if v.startswith("ACC-JV"):   return "ACC-JV"
    return "OTHERS"


def execute(filters=None):
    args = {
        "account_type": "Receivable",
        "naming_by": ["Selling Settings", "cust_master_name"],
    }

    result = ReceivablePayableReport(filters).run(args)
    columns = list(result[0])

    
    raw_data = [row for row in (result[1] or []) if isinstance(row, dict)]

    columns.append({
        "label": "Running Balance",
        "fieldname": "running_balance",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 150,
    })

    buckets = defaultdict(list)
    for row in raw_data:
        voucher_no = (row.get("voucher_no") or "").strip()
        if not voucher_no:
            # skip blank separator rows ERPNext adds between groups
            continue
        group = get_doc_group(voucher_no)
        buckets[group].append(row)

    
    output = []
    running_balance = 0.0

    all_groups = DOC_GROUP_ORDER + [
        g for g in buckets if g not in DOC_GROUP_ORDER
    ]

    for group_key in all_groups:
        rows = buckets.get(group_key)
        if not rows:
            continue

        
        rows.sort(key=lambda r: str(r.get("posting_date") or "9999-99-99"))

        group_invoiced    = 0.0
        group_paid        = 0.0
        group_credit_note = 0.0
        group_outstanding = 0.0

        for row in rows:
            outstanding        = flt(row.get("outstanding"))
            running_balance   += outstanding
            group_invoiced    += flt(row.get("invoiced"))
            group_paid        += flt(row.get("paid"))
            group_credit_note += flt(row.get("credit_note"))
            group_outstanding += outstanding

            row["running_balance"] = running_balance
            output.append(row)

        
        output.append({
            "party":           f"** {group_key} Total **",
            "voucher_type":    "",
            "voucher_no":      "",
            "posting_date":    None,
            "due_date":        None,
            "invoiced":        group_invoiced,
            "paid":            group_paid,
            "credit_note":     group_credit_note,
            "outstanding":     group_outstanding,
            "running_balance": running_balance,
            "currency":        rows[0].get("currency", ""),
            "is_subtotal":     1,
        })

    result = list(result)
    result[0] = columns
    result[1] = output
    return result