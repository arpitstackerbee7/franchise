import frappe
from frappe.utils import flt
from collections import defaultdict
from datetime import date

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    ReceivablePayableReport,
)

VOUCHER_TYPE_ORDER = [
    "Sales Invoice",
    "Credit Note",
    "Payment Entry",
    "Journal Entry",
    "Sales Order",
    "OTHERS",
]


def execute(filters=None):
    args = {
        "account_type": "Receivable",
        "naming_by": ["Selling Settings", "cust_master_name"],
    }

    result = ReceivablePayableReport(filters).run(args)
    columns = list(result[0])
    raw_data = [row for row in (result[1] or []) if isinstance(row, dict)]

    # ── Remove unwanted columns ────────────────────────────────────────────
    REMOVE_FIELDS = {"debit_note", "range1", "range2", "range3", "range4", "range5"}
    columns = [c for c in columns if c.get("fieldname") not in REMOVE_FIELDS]

    # ── Add Running Balance column ─────────────────────────────────────────
    columns.append({
        "label": "Running Balance",
        "fieldname": "running_balance",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 150,
    })

    # ── Batch fetch all is_return Sales Invoices ───────────────────────────
    all_sinv_nos = [
        row.get("voucher_no")
        for row in raw_data
        if (row.get("voucher_type") or "").strip() == "Sales Invoice"
        and row.get("voucher_no")
    ]

    return_set = set()
    if all_sinv_nos:
        returns = frappe.db.get_all(
            "Sales Invoice",
            filters={"name": ["in", all_sinv_nos], "is_return": 1},
            pluck="name",
        )
        return_set = set(returns)

    # ── Patch voucher_type for Credit Notes ───────────────────────────────
    for row in raw_data:
        vno   = (row.get("voucher_no")   or "").strip()
        vtype = (row.get("voucher_type") or "").strip()
        if vtype == "Sales Invoice" and (vno in return_set or vno.startswith("SINV-RET")):
            row["voucher_type"] = "Credit Note"

    def get_group(row):
        vtype = (row.get("voucher_type") or "").strip()
        vno   = (row.get("voucher_no")   or "").strip()
        if vtype in VOUCHER_TYPE_ORDER:
            return vtype
        if vno.startswith("ACC-PAY"): return "Payment Entry"
        if vno.startswith("ACC-JV"):  return "Journal Entry"
        if vno.startswith("PDC"):     return "Payment Entry"
        return vtype or "OTHERS"

    # ── Bucket by party ───────────────────────────────────────────────────
    party_order = []
    party_buckets = defaultdict(list)

    for row in raw_data:
        party = row.get("party") or ""
        if not (row.get("voucher_no") or "").strip():
            continue
        if party not in party_buckets:
            party_order.append(party)
        party_buckets[party].append(row)

    # ── Build output ──────────────────────────────────────────────────────
    output = []
    running_balance = 0.0

    for party in party_order:
        rows = party_buckets[party]
        if not rows:
            continue

        sample_row = rows[0]
        currency   = sample_row.get("currency", "")
        party_type = sample_row.get("party_type", "Customer")

        # ── Sort all rows by posting_date ascending ────────────────────────
        rows.sort(key=lambda r: r.get("posting_date") or date.min)

        # ── Voucher type buckets for subtotals ────────────────────────────
        vtype_buckets = defaultdict(lambda: {"invoiced": 0.0, "paid": 0.0, "outstanding": 0.0})

        party_invoiced    = 0.0
        party_paid        = 0.0
        party_outstanding = 0.0

        for row in rows:
            outstanding     = flt(row.get("outstanding"))
            running_balance += outstanding
            row["running_balance"] = running_balance

            vg = get_group(row)
            vtype_buckets[vg]["invoiced"]    += flt(row.get("invoiced"))
            vtype_buckets[vg]["paid"]        += flt(row.get("paid"))
            vtype_buckets[vg]["outstanding"] += outstanding

            party_invoiced    += flt(row.get("invoiced"))
            party_paid        += flt(row.get("paid"))
            party_outstanding += outstanding

            output.append(row)

        # ── Voucher type subtotals at end of party ────────────────────────
        for vg in VOUCHER_TYPE_ORDER:
            if vg not in vtype_buckets:
                continue
            vg_data = vtype_buckets[vg]
            output.append({
                "party":              party,
                "party_type":         party_type,
                "receivable_account": sample_row.get("receivable_account", ""),
                "cost_center":        sample_row.get("cost_center", ""),
                "voucher_type":       vg,
                "currency":           currency,
                "voucher_no":         f"── {vg} Total ──",
                "posting_date":       None,
                "due_date":           None,
                "invoiced":           vg_data["invoiced"],
                "paid":               vg_data["paid"],
                "outstanding":        vg_data["outstanding"],
                "running_balance":    running_balance,
                "is_group":           1,
            })

        # Party total
        output.append({
            "party":              party,
            "party_type":         party_type,
            "receivable_account": sample_row.get("receivable_account", ""),
            "cost_center":        sample_row.get("cost_center", ""),
            "voucher_type":       "",
            "currency":           currency,
            "voucher_no":         f"★ {party} Total ★",
            "posting_date":       None,
            "due_date":           None,
            "invoiced":           party_invoiced,
            "paid":               party_paid,
            "outstanding":        party_outstanding,
            "running_balance":    running_balance,
            "is_subtotal":        1,
        })

    result = list(result)
    result[0] = columns
    result[1] = output
    return result