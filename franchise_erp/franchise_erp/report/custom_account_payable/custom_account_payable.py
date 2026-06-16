import frappe
from frappe.utils import flt
from collections import defaultdict
from datetime import date

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    ReceivablePayableReport,
)

VOUCHER_TYPE_ORDER = [
    "Purchase Invoice",
    "Debit Note",
    "Payment Entry",
    "Journal Entry",
    "Purchase Order",
    "OTHERS",
]


def execute(filters=None):
    args = {
        "account_type": "Payable",
        "naming_by": ["Buying Settings", "supp_master_name"],
    }

    result = ReceivablePayableReport(filters).run(args)
    columns = list(result[0])
    raw_data = [row for row in result[1] if isinstance(row, dict)]

    # ── Remove unwanted columns ────────────────────────────────────────────
    REMOVE_FIELDS = {"credit_note", "range1", "range2", "range3", "range4", "range5"}
    columns = [c for c in columns if c.get("fieldname") not in REMOVE_FIELDS]

    running_balance_col = {
        "label": "Running Balance",
        "fieldname": "running_balance",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 150,
    }

    outstanding_idx = next(
        (i for i, c in enumerate(columns) if c.get("fieldname") == "outstanding"),
        len(columns) - 1,
    )
    columns.insert(outstanding_idx + 1, running_balance_col)


    # ── Batch fetch all is_return Purchase Invoices ────────────────────────
    all_pinv_nos = [
        row.get("voucher_no")
        for row in raw_data
        if (row.get("voucher_type") or "").strip() == "Purchase Invoice"
        and row.get("voucher_no")
    ]

    return_set = set()
    if all_pinv_nos:
        returns = frappe.db.get_all(
            "Purchase Invoice",
            filters={"name": ["in", all_pinv_nos], "is_return": 1},
            pluck="name",
        )
        return_set = set(returns)

    # ── Patch voucher_type for Debit Notes ────────────────────────────────
    for row in raw_data:
        vno   = (row.get("voucher_no")   or "").strip()
        vtype = (row.get("voucher_type") or "").strip()
        if vtype == "Purchase Invoice" and (vno in return_set or vno.startswith("PINV-RET")):
            row["voucher_type"] = "Debit Note"

    def get_group(row):
        vtype = (row.get("voucher_type") or "").strip()
        vno   = (row.get("voucher_no")   or "").strip()
        if vtype in VOUCHER_TYPE_ORDER:
            return vtype
        if vno.startswith("ACC-PAY"): return "Payment Entry"
        if vno.startswith("ACC-JV"):  return "Journal Entry"
        if vno.startswith("PDC"):     return "Payment Entry"
        if vno.startswith("PV"):      return "Payment Entry"
        return vtype or "OTHERS"

    # ── Bucket by party ───────────────────────────────────────────────────
    party_order = []
    party_buckets = defaultdict(list)

    for row in raw_data:
        party = row.get("party") or ""
        if party not in party_buckets:
            party_order.append(party)
        party_buckets[party].append(row)

    # ── Build output ──────────────────────────────────────────────────────
    output = []
    

    for party in party_order:
        rows = party_buckets[party]
        if not rows:
            continue

        running_balance = 0.0 

        sample_row = rows[0]
        currency   = sample_row.get("currency", "")
        party_type = sample_row.get("party_type", "Supplier")

        vtype_order_seen = []
        vtype_buckets = defaultdict(list)

        for row in rows:
            vg = get_group(row)
            if vg not in vtype_buckets:
                vtype_order_seen.append(vg)
            vtype_buckets[vg].append(row)

        vtype_order_seen.sort(
            key=lambda g: VOUCHER_TYPE_ORDER.index(g)
            if g in VOUCHER_TYPE_ORDER else len(VOUCHER_TYPE_ORDER)
        )

        party_invoiced    = 0.0
        party_paid        = 0.0
        party_outstanding = 0.0

        for vg in vtype_order_seen:
            vg_rows = vtype_buckets[vg]

            # ── Sort by bill_date ascending, fallback to posting_date ─────
            vg_rows.sort(
                key=lambda r: r.get("bill_date") or r.get("posting_date") or date.min
            )

            vg_invoiced    = 0.0
            vg_paid        = 0.0
            vg_outstanding = 0.0

            for row in vg_rows:
                outstanding     = flt(row.get("outstanding"))
                running_balance += outstanding
                vg_invoiced     += flt(row.get("invoiced"))
                vg_paid         += flt(row.get("paid"))
                vg_outstanding  += outstanding
                row["running_balance"] = running_balance
                output.append(row)

            # Voucher type subtotal
            output.append({
                "party":           party,
                "party_type":      party_type,
                "payable_account": sample_row.get("payable_account", ""),
                "cost_center":     sample_row.get("cost_center", ""),
                "voucher_type":    vg,
                "currency":        currency,
                "voucher_no":      f"── {vg} Total ──",
                "posting_date":    None,
                "bill_date":       None,
                "due_date":        None,
                "invoiced":        vg_invoiced,
                "paid":            vg_paid,
                "outstanding":     vg_outstanding,
                "running_balance": running_balance,
                "is_group":        1,
            })

            party_invoiced    += vg_invoiced
            party_paid        += vg_paid
            party_outstanding += vg_outstanding

        # Party total
        output.append({
            "party":           party,
            "party_type":      party_type,
            "payable_account": sample_row.get("payable_account", ""),
            "cost_center":     sample_row.get("cost_center", ""),
            "voucher_type":    "",
            "currency":        currency,
            "voucher_no":      f"★ {party} Total ★",
            "posting_date":    None,
            "bill_date":       None,
            "due_date":        None,
            "invoiced":        party_invoiced,
            "paid":            party_paid,
            "outstanding":     party_outstanding,
            "running_balance": running_balance,
            "is_subtotal":     1,
        })

    result = list(result)
    result[0] = columns
    result[1] = output
    return result