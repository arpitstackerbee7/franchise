import frappe
from frappe.utils import flt, getdate
from collections import defaultdict
from datetime import date

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    ReceivablePayableReport,
)

VOUCHER_TYPE_ORDER = [
    "Payment Entry",
    "Purchase Invoice",
    "Debit Note",
    "Journal Entry",
    "Purchase Order",
    "OTHERS",
]

CREDIT_ENTRY_GROUPS = {"Payment Entry", "Debit Note"}
SUPPLIER_AGENT_FIELD = "custom_agent_supplier"

def execute(filters=None):
    filters = frappe._dict(filters or {})

    group_by_party = int(filters.get("group_by_party") or 0)
    base_filters = dict(filters)
    base_filters["group_by_party"] = 0

    args = {
    "account_type": "Payable",
    "naming_by": ["Buying Settings", "supp_master_name"],
}
    result = ReceivablePayableReport(base_filters).run(args)
    columns = list(result[0])
    raw_data = [row for row in result[1] if isinstance(row, dict)]

    supplier_filter = filters.get("supplier") or []
    if supplier_filter:
        supplier_list = [
            (s if isinstance(s, str) else s.get("value", "")).strip()
            for s in supplier_filter
        ]
        supplier_list = [s for s in supplier_list if s]  
        if supplier_list:
            raw_data = [
                row for row in raw_data
                if (row.get("party") or "").strip() in supplier_list
            ]
    #Supplier Group filter (multi-select) 
    supplier_group_filter = filters.get("supplier_group") or []
    if supplier_group_filter:
        supplier_group_list = [
            (g if isinstance(g, str) else g.get("value", "")).strip()
            for g in supplier_group_filter
        ]
        supplier_group_list = [g for g in supplier_group_list if g]
        if supplier_group_list:
            raw_data = [
                row for row in raw_data
                if (row.get("supplier_group") or "").strip() in supplier_group_list
            ]
    # Party filter (generic — works for any party_type: Supplier/Customer/etc.)
    party_filter = filters.get("party") or []
    if isinstance(party_filter, str):
        party_filter = [party_filter]
    party_list = [
        (p if isinstance(p, str) else p.get("value", "")).strip()
        for p in party_filter
    ]
    party_list = [p for p in party_list if p]
    if party_list:
        raw_data = [
            row for row in raw_data
            if (row.get("party") or "").strip() in party_list
        ]
    #Party Type filter 
    party_type_filter = (filters.get("party_type") or "").strip()
    if party_type_filter:
        raw_data = [
            row for row in raw_data
            if (row.get("party_type") or "").strip() == party_type_filter
        ]

    #Payable Account filter (multi-select)
    payable_account_filter = filters.get("payable_account") or []
    if isinstance(payable_account_filter, str):
        payable_account_filter = [payable_account_filter]
    payable_account_list = [
        (a if isinstance(a, str) else a.get("value", "")).strip()
        for a in payable_account_filter
    ]
    payable_account_list = [a for a in payable_account_list if a]
    if payable_account_list:
        raw_data = [
            row for row in raw_data
            if (row.get("payable_account") or "").strip() in payable_account_list
        ]

    #Agent filter 
    agent_filter = (filters.get("agent") or "").strip()
    if agent_filter:
        parties_in_data = list({
            (row.get("party") or "").strip() for row in raw_data if row.get("party")
        })
        if parties_in_data:
            agent_map = frappe.db.get_all(
                "Supplier",
                filters={"name": ["in", parties_in_data]},
                fields=["name", SUPPLIER_AGENT_FIELD],
            )
            allowed_parties = {
                a["name"] for a in agent_map if a.get(SUPPLIER_AGENT_FIELD) == agent_filter
            }
            raw_data = [
                row for row in raw_data
                if (row.get("party") or "").strip() in allowed_parties
            ]


    #Remove unwanted columns 
    REMOVE_FIELDS = {"credit_note", "range1", "range2", "range3", "range4", "range5", "due_date", "cost_center", "project", "currency"}
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

    # ── Add Reference No / Reference Date columns (right after Voucher No) ─
    reference_no_col = {
        "label": "Cheque/Reference No",
        "fieldname": "reference_no",
        "fieldtype": "Data",
        "width": 130,
    }
    reference_date_col = {
        "label": "Reference Date",
        "fieldname": "reference_date",
        "fieldtype": "Date",
        "width": 110,
    }
    voucher_no_idx = next(
        (i for i, c in enumerate(columns) if c.get("fieldname") == "voucher_no"),
        len(columns) - 1,
    )
    columns.insert(voucher_no_idx + 1, reference_no_col)
    columns.insert(voucher_no_idx + 2, reference_date_col)

    #Batch fetch all is_return Purchase Invoices 
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

    #Batch fetch reference_no / reference_date for Payment Entry rows
    all_pe_nos = [
        row.get("voucher_no")
        for row in raw_data
        if (row.get("voucher_type") or "").strip() == "Payment Entry"
        and row.get("voucher_no")
    ]

    pe_reference_map = {}
    if all_pe_nos:
        pe_records = frappe.db.get_all(
            "Payment Entry",
            filters={"name": ["in", all_pe_nos]},
            fields=["name", "reference_no", "reference_date"],
        )
        pe_reference_map = {
            pe["name"]: (pe.get("reference_no"), pe.get("reference_date"))
            for pe in pe_records
        }

    #Patch voucher_type for Debit Notes + attach reference fields
    for row in raw_data:
        vno   = (row.get("voucher_no")   or "").strip()
        vtype = (row.get("voucher_type") or "").strip()
        if vtype == "Purchase Invoice" and (vno in return_set or vno.startswith("PINV-RET")):
            row["voucher_type"] = "Debit Note"

        if vtype == "Payment Entry" and vno in pe_reference_map:
            ref_no, ref_date = pe_reference_map[vno]
            row["reference_no"] = ref_no
            row["reference_date"] = ref_date
        else:
            row["reference_no"] = None
            row["reference_date"] = None

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
    #Credit Entry date filter 
    credit_entry_date = filters.get("credit_entry_date")
    selected_credit_groups = filters.get("credit_entry_voucher_types") or []
    selected_credit_groups = [
        (g if isinstance(g, str) else g.get("value", "")).strip()
        for g in selected_credit_groups
    ]
    selected_credit_groups = [g for g in selected_credit_groups if g] or list(CREDIT_ENTRY_GROUPS)

    if credit_entry_date:
        credit_entry_date = getdate(credit_entry_date)
        filtered = []
        for row in raw_data:
            vg = get_group(row)
            if vg in selected_credit_groups:
                row_date = row.get("posting_date")
                if row_date and getdate(row_date) > credit_entry_date:
                    continue  # exclude credit entries posted after the cutoff
            filtered.append(row)
        raw_data = filtered

    # Bucket by party
    party_order = []
    party_buckets = defaultdict(list)

    for row in raw_data:
        party = row.get("party") or ""
        if party not in party_buckets:
            party_order.append(party)
        party_buckets[party].append(row)
    # ═══════════════════════════════════════════════════════════════════
    # RAW MODE (Group By Party unchecked): flat data, no subtotal rows,
    # no vendor separators, no highlight flags.
    # ═══════════════════════════════════════════════════════════════════
    if not group_by_party:
        output = []
        for party in party_order:
            rows = party_buckets[party]
            rows.sort(key=lambda r: r.get("bill_date") or r.get("posting_date") or date.min)
            running_balance = 0.0
            for row in rows:
                running_balance += flt(row.get("outstanding"))
                row["running_balance"] = running_balance
                output.append(row)

        result = list(result)
        result[0] = columns
        result[1] = output
        return result

    # ═══════════════════════════════════════════════════════════════════
    # GROUPED MODE (Group By Party checked): voucher-type subtotals,
    # party totals, vendor-change row break, highlight flags.
    # ═══════════════════════════════════════════════════════════════════
    # ── Build output ──────────────────────────────────────────────────────
    output = []
    

    for idx, party in enumerate(party_order):
        rows = party_buckets[party]
        if not rows:
            continue
        if idx > 0:
            output.append({
        "party": "", "party_type": "", "payable_account": "",
        "voucher_type": "", "voucher_no": "", "posting_date": None,
        "bill_date": None, "reference_no": None, "reference_date": None,
        "invoiced": None, "paid": None, "outstanding": None,
        "running_balance": None, "is_row_break": 1,
        })
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
                "reference_no":    None,
                "reference_date":  None,
                "invoiced":        vg_invoiced,
                "paid":            vg_paid,
                "outstanding":     vg_outstanding,
                "running_balance": None,
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
            "reference_no":    None,
            "reference_date":  None,
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