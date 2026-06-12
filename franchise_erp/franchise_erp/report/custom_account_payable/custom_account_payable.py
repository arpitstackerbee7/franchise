import frappe
from frappe.utils import flt
from collections import defaultdict

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    ReceivablePayableReport,
)

DOC_GROUP_ORDER = ["PINV", "PINV-RET", "ACC-PAY", "ACC-JV", "PDC", "PV", "RT", "OTHERS"]


def get_doc_group(voucher_no: str) -> str:
    v = (voucher_no or "").strip()
    # Order matters: more specific prefixes first
    if v.startswith("PINV-RET"):   return "PINV-RET"
    if v.startswith("PINV"):       return "PINV"
    if v.startswith("ACC-PAY"):    return "ACC-PAY"
    if v.startswith("ACC-JV"):     return "ACC-JV"
    if v.startswith("PDC"):        return "PDC"
    if v.startswith("PV"):         return "PV"
    if v.startswith("RT"):         return "RT"
    return "OTHERS"


def execute(filters=None):
    args = {
        "account_type": "Payable",
        "naming_by": ["Buying Settings", "supp_master_name"],
    }

    result = ReceivablePayableReport(filters).run(args)
    columns = list(result[0])
    raw_data = [row for row in result[1] if isinstance(row, dict)]

    # ── Add Running Balance column ─────────────────────────────────────────
    columns.append({
        "label": "Running Balance",
        "fieldname": "running_balance",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 150,
    })

    # ── Bucket rows by doc group ───────────────────────────────────────────
    buckets = defaultdict(list)
    for row in raw_data:
        group = get_doc_group(row.get("voucher_no") or "")
        buckets[group].append(row)

    # ── Build final data: sorted rows + inline subtotal per group ─────────
    output = []
    running_balance = 0.0

    # Respect DOC_GROUP_ORDER, then any unexpected groups at the end
    all_groups = DOC_GROUP_ORDER + [g for g in buckets if g not in DOC_GROUP_ORDER]

    for group_key in all_groups:
        rows = buckets.get(group_key)
        if not rows:
            continue

        # Sort by bill_date ascending; rows without bill_date go last
        rows.sort(key=lambda r: str(r.get("bill_date") or r.get("posting_date") or "9999-99-99"))

        group_invoiced    = 0.0
        group_paid        = 0.0
        group_outstanding = 0.0

        for row in rows:
            outstanding = flt(row.get("outstanding"))
            running_balance  += outstanding
            group_invoiced   += flt(row.get("invoiced"))
            group_paid       += flt(row.get("paid"))
            group_outstanding += outstanding

            row["running_balance"] = running_balance
            output.append(row)

        # ── Subtotal row (inline, after each group) ────────────────────
        subtotal_row = {
            # Show label in the party column so it's always visible
            "party":           f"** {group_key} Total **",
            "voucher_no":      "",
            "bill_date":       None,
            "due_date":        None,
            "invoiced":        group_invoiced,
            "paid":            group_paid,
            "outstanding":     group_outstanding,
            "running_balance": running_balance,
            "currency":        (rows[0].get("currency") if rows else ""),
            # bold flag consumed by JS formatter
            "is_subtotal":     1,
        }
        output.append(subtotal_row)

    result = list(result)
    result[0] = columns
    result[1] = output
    return result