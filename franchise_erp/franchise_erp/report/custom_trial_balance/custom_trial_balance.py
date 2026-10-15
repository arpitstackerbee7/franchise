# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.trial_balance.trial_balance import (
    execute as trial_balance_execute,
)

# Transaction classification
TXN_CASE = """
CASE
    WHEN gle.voucher_type = 'Purchase Invoice' AND pi.is_return = 1
        THEN 'Debit Note (Purchase Return)'
    WHEN gle.voucher_type = 'Purchase Invoice'
        THEN 'Purchase Invoice'

    WHEN gle.voucher_type = 'Purchase Receipt' AND pr.is_return = 1
        THEN 'Purchase Return (Receipt)'
    WHEN gle.voucher_type = 'Purchase Receipt'
        THEN 'Purchase Receipt'

    WHEN gle.voucher_type = 'Sales Invoice' AND si.is_return = 1
        THEN 'Credit Note (Sales Return)'
    WHEN gle.voucher_type = 'Sales Invoice' AND si.is_debit_note = 1
        THEN 'Debit Note (Sales)'
    WHEN gle.voucher_type = 'Sales Invoice'
        THEN 'Sales Invoice'

    WHEN gle.voucher_type = 'Delivery Note' AND dn.is_return = 1
        THEN 'Sales Return (Delivery)'
    WHEN gle.voucher_type = 'Delivery Note'
        THEN 'Delivery Note'

    WHEN gle.voucher_type = 'Stock Entry'
        THEN CONCAT('Stock Entry - ', IFNULL(se.stock_entry_type, ''))

    WHEN gle.voucher_type = 'Payment Entry'
        THEN CONCAT('Payment - ', IFNULL(pe.payment_type, ''))

    ELSE gle.voucher_type
END
"""

# Joins needed by TXN_CASE (breakdown aur SRBNB dono same use karte hain)
TXN_JOINS = """
LEFT JOIN `tabPurchase Invoice` pi
    ON gle.voucher_type = 'Purchase Invoice'
    AND pi.name = gle.voucher_no

LEFT JOIN `tabPurchase Receipt` pr
    ON gle.voucher_type = 'Purchase Receipt'
    AND pr.name = gle.voucher_no

LEFT JOIN `tabSales Invoice` si
    ON gle.voucher_type = 'Sales Invoice'
    AND si.name = gle.voucher_no

LEFT JOIN `tabDelivery Note` dn
    ON gle.voucher_type = 'Delivery Note'
    AND dn.name = gle.voucher_no

LEFT JOIN `tabStock Entry` se
    ON gle.voucher_type = 'Stock Entry'
    AND se.name = gle.voucher_no

LEFT JOIN `tabPayment Entry` pe
    ON gle.voucher_type = 'Payment Entry'
    AND pe.name = gle.voucher_no
"""

TXN_ORDER = [
    "Purchase Receipt",
    "Purchase Return (Receipt)",
    "Purchase Invoice",
    "Debit Note (Purchase Return)",
    "Delivery Note",
    "Sales Return (Delivery)",
    "Sales Invoice",
    "Credit Note (Sales Return)",
    "Debit Note (Sales)",
    "Payment - Receive",
    "Payment - Pay",
    "Payment - Internal Transfer",
    "Journal Entry",
    "Stock Reconciliation",
    "Landed Cost Voucher",
]


def execute(filters=None):
    filters = frappe._dict(filters or {})

    # SRBNB Breakdown view
    if filters.get("srbnb_view"):
        return execute_srbnb(filters)

    # Standard ERPNext Trial Balance
    columns, data = trial_balance_execute(filters)

    if not filters.get("show_breakdown"):
        return columns, data

    breakdown = get_breakdown(filters)

    leaf_accounts = set(
        frappe.get_all(
            "Account",
            filters={
                "company": filters.company,
                "is_group": 0,
            },
            pluck="name",
        )
    )

    output = []

    for row in data or []:
        if not isinstance(row, dict):
            output.append(row)
            continue

        account = row.get("account")

        # Account ki normal row ko touch nahi karte: ERPNext ki default
        # General Ledger link waise hi chalegi.
        output.append(row)

        # Transaction breakdown only for leaf accounts
        if not account or account not in leaf_accounts:
            continue

        transactions = sort_txns(
            breakdown.get(account, [])
        )

        for txn, debit, credit in transactions:
            output.append(
                {
                    "account": f"{account}::{txn}",
                    "parent_account": account,
                    "account_name": txn,
                    "indent": flt(row.get("indent")) + 1,
                    "opening_debit": 0,
                    "opening_credit": 0,
                    "debit": debit,
                    "credit": credit,
                    "closing_debit": 0,
                    "closing_credit": 0,
                    "currency": row.get("currency"),
                    "has_value": True,
                    "is_breakdown": 1,

                    # Click-link metadata: account + transaction type -> documents
                    "is_txn_link": 1,
                    "link_account": account,
                    "transaction_type": txn,
                    "company": filters.company,
                    "from_date": filters.from_date,
                    "to_date": filters.to_date,
                }
            )

    return columns, output


def get_purchase_receipt_analytics_value(filters):
    conditions = [
        "pr.docstatus = 1",
        "pr.company = %(company)s",
        "pr.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    # Match Purchase Analytics: Item + Value
    result = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(pri.base_net_amount), 0)
        FROM `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE {" AND ".join(conditions)}
        """,
        values,
    )

    return flt(result[0][0]) if result else 0


def _as_list(value):
    """MultiSelectList value ko list me convert karo (list / JSON string / str)."""
    if not value:
        return []

    if isinstance(value, (list, tuple)):
        return list(value)

    if isinstance(value, str):
        value = value.strip()
        if value.startswith("["):
            try:
                return list(json.loads(value))
            except ValueError:
                pass
        return [value]

    return []


def get_dimension_conditions(filters):
    """
    Cost Center / Project / Finance Book ki GL conditions.
    Breakdown aur SRBNB document view dono yahi use karte hain, taaki
    dono jagah value same filters ke hisaab se match ho.
    """
    conditions = []
    values = {}

    # Cost Center MultiSelectList, including child cost centers
    cost_centers = _as_list(filters.get("cost_center"))

    if cost_centers:
        selected_centers = set()

        for center in cost_centers:
            bounds = frappe.db.get_value(
                "Cost Center",
                center,
                ["lft", "rgt"],
            )

            if not bounds:
                continue

            children = frappe.get_all(
                "Cost Center",
                filters={
                    "lft": [">=", bounds[0]],
                    "rgt": ["<=", bounds[1]],
                },
                pluck="name",
            )

            selected_centers.update(children)

        if selected_centers:
            values["cost_centers"] = list(selected_centers)
            conditions.append("gle.cost_center IN %(cost_centers)s")
        else:
            conditions.append("1 = 0")

    # Project MultiSelectList
    projects = _as_list(filters.get("project"))

    if projects:
        values["projects"] = projects
        conditions.append("gle.project IN %(projects)s")

    # Finance Book filtering
    books = []

    if filters.get("finance_book"):
        books.append(filters.finance_book)

    if filters.get("include_default_book_entries"):
        default_book = frappe.get_cached_value(
            "Company",
            filters.company,
            "default_finance_book",
        )

        if default_book:
            books.append(default_book)

    if books:
        values["books"] = tuple(set(books))
        conditions.append(
            "(gle.finance_book IN %(books)s "
            "OR IFNULL(gle.finance_book, '') = '')"
        )
    else:
        conditions.append("IFNULL(gle.finance_book, '') = ''")

    return conditions, values


def get_breakdown(filters):
    conditions = [
        "gle.company = %(company)s",
        "gle.is_cancelled = 0",
        "gle.is_opening = 'No'",
        "gle.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    # Period closing entries
    if not filters.get("with_period_closing_entry_for_current_period"):
        conditions.append(
            "gle.voucher_type != 'Period Closing Voucher'"
        )

    dim_conditions, dim_values = get_dimension_conditions(filters)
    conditions.extend(dim_conditions)
    values.update(dim_values)

    # Transaction-wise debit and credit
    rows = frappe.db.sql(
        f"""
        SELECT
            gle.account,
            {TXN_CASE} AS txn,
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit

        FROM `tabGL Entry` gle

        {TXN_JOINS}

        WHERE {" AND ".join(conditions)}

        GROUP BY gle.account, txn

        HAVING SUM(gle.debit) != 0
            OR SUM(gle.credit) != 0
        """,
        values,
        as_dict=True,
    )

    breakdown = {}

    for row in rows:
        breakdown.setdefault(row.account, []).append(
            (
                row.txn,
                flt(row.debit),
                flt(row.credit),
            )
        )

    return breakdown


def sort_txns(items):
    def sort_key(item):
        txn = item[0]

        if txn in TXN_ORDER:
            return (TXN_ORDER.index(txn), "")

        return (len(TXN_ORDER), txn)

    return sorted(items, key=sort_key)


# ---------------------------------------------------------------------
# SRBNB Breakdown - ERPNext v15
# ---------------------------------------------------------------------

# Breakdown rows aur SRBNB views me EXACT same classification use hoti hai,
# isliye breakdown row ka naam (txn) aur document view ka filter hamesha match karega.
SRBNB_TXN_CASE = TXN_CASE
SRBNB_JOINS = TXN_JOINS

SRBNB_TXN_ORDER = [
    "Purchase Receipt",
    "Purchase Return (Receipt)",
    "Purchase Invoice",
    "Debit Note (Purchase Return)",
    "Landed Cost Voucher",
    "Journal Entry",
]


def execute_srbnb(filters):
    if not filters.get("company"):
        frappe.throw(_("Please select a Company."))

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("Please select From Date and To Date."))

    if not filters.get("account"):
        filters.account = frappe.get_cached_value(
            "Company",
            filters.company,
            "stock_received_but_not_billed",
        )

    if not filters.account:
        frappe.throw(
            _(
                "Set Stock Received But Not Billed account "
                "in Company or select an Account."
            )
        )

    dim_conditions, dim_values = get_dimension_conditions(filters)

    params = dict(filters)
    params.update(dim_values)

    opening = get_srbnb_opening(params, dim_conditions)

    if filters.get("srbnb_view") == "Document":
        return get_srbnb_document_view(filters, params, dim_conditions, opening)

    return get_srbnb_summary_view(filters, params, dim_conditions, opening)


def get_srbnb_base_conditions(dim_conditions):
    return [
        "gle.company = %(company)s",
        "gle.account = %(account)s",
        "gle.is_cancelled = 0",
    ] + dim_conditions


def get_srbnb_period_conditions(filters, dim_conditions):
    conditions = get_srbnb_base_conditions(dim_conditions) + [
        "gle.is_opening = 'No'",
        "gle.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]

    if not filters.get("with_period_closing_entry_for_current_period"):
        conditions.append("gle.voucher_type != 'Period Closing Voucher'")

    return conditions


def get_srbnb_opening(params, dim_conditions):
    conditions = get_srbnb_base_conditions(dim_conditions) + [
        "(gle.posting_date < %(from_date)s OR gle.is_opening = 'Yes')"
    ]

    result = frappe.db.sql(
        f"""
        SELECT
            COALESCE(SUM(gle.debit), 0)
            - COALESCE(SUM(gle.credit), 0)
        FROM `tabGL Entry` gle
        WHERE {" AND ".join(conditions)}
        """,
        params,
    )

    return flt(result[0][0]) if result else 0.0


def get_srbnb_split(balance):
    """Convert Dr-Cr balance to debit and credit presentation."""
    return (balance, 0.0) if balance > 0 else (0.0, -balance)


def get_srbnb_sort_key(txn):
    if txn in SRBNB_TXN_ORDER:
        return (SRBNB_TXN_ORDER.index(txn), "")

    return (len(SRBNB_TXN_ORDER), txn or "")


# ---------------------------------------------------------------------
# SRBNB Transaction Type view
# ---------------------------------------------------------------------

def get_srbnb_summary_view(filters, params, dim_conditions, opening):
    columns = [
        {
            "label": _("Transaction Type"),
            "fieldname": "txn",
            "fieldtype": "Data",
            "width": 280,
        },
        {
            "label": _("Documents"),
            "fieldname": "documents",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Net (Dr - Cr)"),
            "fieldname": "net",
            "fieldtype": "Currency",
            "width": 160,
        },
    ]

    rows = frappe.db.sql(
        f"""
        SELECT
            {SRBNB_TXN_CASE} AS txn,
            COUNT(DISTINCT gle.voucher_no) AS documents,
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit
        FROM `tabGL Entry` gle
        {SRBNB_JOINS}
        WHERE {" AND ".join(get_srbnb_period_conditions(filters, dim_conditions))}
        GROUP BY txn
        """,
        params,
        as_dict=True,
    )

    rows.sort(key=lambda row: get_srbnb_sort_key(row.txn))

    data = []

    opening_debit, opening_credit = get_srbnb_split(opening)

    data.append(
        {
            "txn": _("Opening Balance"),
            "debit": opening_debit,
            "credit": opening_credit,
            "net": opening,
            "is_bold": 1,
        }
    )

    total_debit = 0.0
    total_credit = 0.0

    for row in rows:
        debit = flt(row.debit)
        credit = flt(row.credit)

        total_debit += debit
        total_credit += credit

        data.append(
            {
                "txn": row.txn,
                "documents": row.documents,
                "debit": debit,
                "credit": credit,
                "net": debit - credit,
                "indent": 1,

                # Click -> us transaction type ke documents
                "is_srbnb_txn_link": 1,
                "link_account": filters.account,
                "transaction_type": row.txn,
                "company": filters.company,
                "from_date": filters.from_date,
                "to_date": filters.to_date,
            }
        )

    data.append(
        {
            "txn": _("Total Movement"),
            "debit": total_debit,
            "credit": total_credit,
            "net": total_debit - total_credit,
            "is_bold": 1,
        }
    )

    closing = opening + total_debit - total_credit
    closing_debit, closing_credit = get_srbnb_split(closing)

    data.append(
        {
            "txn": _("Closing Balance"),
            "debit": closing_debit,
            "credit": closing_credit,
            "net": closing,
            "is_bold": 1,
        }
    )

    return columns, data


# ---------------------------------------------------------------------
# SRBNB Document view
# ---------------------------------------------------------------------

def get_srbnb_document_view(filters, params, dim_conditions, opening):
    columns = [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Transaction Type"),
            "fieldname": "txn",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 180,
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Balance (Dr - Cr)"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 160,
        },
    ]

    conditions = get_srbnb_period_conditions(filters, dim_conditions)

    if filters.get("supplier"):
        conditions.append(
            "COALESCE(pr.supplier, pi.supplier, gle.party) = %(supplier)s"
        )

    # Breakdown row pe click kiya to sirf wahi transaction type dikhao
    transaction_type = (filters.get("transaction_type") or "").strip()
    type_filtered = bool(transaction_type)

    having = ""
    if type_filtered:
        params["transaction_type"] = transaction_type
        having = "HAVING txn = %(transaction_type)s"

    rows = frappe.db.sql(
        f"""
        SELECT
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            {SRBNB_TXN_CASE} AS txn,
            COALESCE(pr.supplier, pi.supplier, gle.party) AS supplier,
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit,
            MIN(gle.creation) AS first_creation
        FROM `tabGL Entry` gle
        {SRBNB_JOINS}
        WHERE {" AND ".join(conditions)}
        GROUP BY
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            txn,
            supplier
        {having}
        ORDER BY
            gle.posting_date,
            first_creation
        """,
        params,
        as_dict=True,
    )

    data = []

    if type_filtered:
        # Type-wise view me opening/closing ka matlab nahi, running total 0 se
        balance = 0.0
    else:
        opening_debit, opening_credit = get_srbnb_split(opening)
        balance = opening

        data.append(
            {
                "txn": _("Opening Balance"),
                "debit": opening_debit,
                "credit": opening_credit,
                "balance": opening,
                "is_bold": 1,
            }
        )

    total_debit = 0.0
    total_credit = 0.0

    for row in rows:
        debit = flt(row.debit)
        credit = flt(row.credit)

        balance += debit - credit
        total_debit += debit
        total_credit += credit

        data.append(
            {
                "posting_date": row.posting_date,
                "txn": row.txn,
                "voucher_type": row.voucher_type,
                "voucher_no": row.voucher_no,
                "supplier": row.supplier,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )

    data.append(
        {
            "txn": _("Total Movement"),
            "debit": total_debit,
            "credit": total_credit,
            "balance": total_debit - total_credit,
            "is_bold": 1,
        }
    )

    if not type_filtered:
        closing_debit, closing_credit = get_srbnb_split(balance)

        data.append(
            {
                "txn": _("Closing Balance"),
                "debit": closing_debit,
                "credit": closing_credit,
                "balance": balance,
                "is_bold": 1,
            }
        )

    return columns, data
