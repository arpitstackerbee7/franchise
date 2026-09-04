# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, add_days


def execute(filters=None):

    filters = filters or {}

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


# =========================================================
# COLUMNS
# =========================================================

def get_columns(filters):

    fy = ""

    if filters.get("fiscal_year"):
        fy = filters.get("fiscal_year")

    elif filters.get("from_date") and filters.get("to_date"):
        fy = (
            filters.get("from_date")[:4]
            + "-"
            + filters.get("to_date")[:4]
        )

    return [
        {
            "label": _("Expenses"),
            "fieldname": "expense",
            "fieldtype": "Data",
            "width": 320
        },
        {
            "label": _("Expenses - {0}").format(fy),
            "fieldname": "expense_amount",
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "label": _("Income"),
            "fieldname": "income",
            "fieldtype": "Data",
            "width": 320
        },
        {
            "label": _("Income - {0}").format(fy),
            "fieldname": "income_amount",
            "fieldtype": "Currency",
            "width": 170
        }
    ]


# =========================================================
# GET MAPPINGS FROM TZU SETTING
# =========================================================

def get_statement_mappings(section=None):

    settings = frappe.get_single("TZU Setting")

    mappings = settings.get(
        "financial_statement_account_mapping"
    ) or []

    result = []

    for row in mappings:

        if not row.get("enabled"):
            continue

        if not row.get("statement_type"):
            continue

        if not row.get("account"):
            continue

        if section and row.get("statement_section") != section:
            continue

        result.append(row)

    return result


# =========================================================
# ACCOUNT BALANCE
# =========================================================

def get_account_balance(
    account_name,
    filters,
    from_date=None,
    to_date=None
):

    account = frappe.db.get_value(
        "Account",
        account_name,
        [
            "lft",
            "rgt",
            "root_type"
        ],
        as_dict=True
    )

    if not account:
        return 0

    conditions = [
        "gle.is_cancelled = 0",
        "gle.account = acc.name",
        "acc.lft >= %(lft)s",
        "acc.rgt <= %(rgt)s"
    ]

    values = {
        "lft": account.lft,
        "rgt": account.rgt
    }

    # -----------------------------------------------------
    # COMPANY
    # -----------------------------------------------------

    if filters.get("company"):

        conditions.append(
            "gle.company = %(company)s"
        )

        values["company"] = filters.get("company")

    # -----------------------------------------------------
    # DATE RANGE
    # -----------------------------------------------------

    if from_date:

        conditions.append(
            "gle.posting_date >= %(from_date)s"
        )

        values["from_date"] = from_date

    if to_date:

        conditions.append(
            "gle.posting_date <= %(to_date)s"
        )

        values["to_date"] = to_date

    # -----------------------------------------------------
    # COST CENTER
    # -----------------------------------------------------

    if filters.get("cost_center"):

        conditions.append(
            "gle.cost_center = %(cost_center)s"
        )

        values["cost_center"] = filters.get(
            "cost_center"
        )

    # -----------------------------------------------------
    # PROJECT
    # -----------------------------------------------------

    if filters.get("project"):

        conditions.append(
            "gle.project = %(project)s"
        )

        values["project"] = filters.get(
            "project"
        )

    # -----------------------------------------------------
    # FINANCE BOOK
    # -----------------------------------------------------

    if filters.get("finance_book"):

        conditions.append(
            "gle.finance_book = %(finance_book)s"
        )

        values["finance_book"] = filters.get(
            "finance_book"
        )

    result = frappe.db.sql(
        f"""
        SELECT

            COALESCE(SUM(gle.debit), 0) AS debit,
            COALESCE(SUM(gle.credit), 0) AS credit

        FROM `tabGL Entry` gle

        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE
            {' AND '.join(conditions)}
        """,
        values,
        as_dict=True
    )

    if not result:
        return 0

    debit = flt(result[0].debit)
    credit = flt(result[0].credit)

    # Same basic sign logic as Trial Balance
    if account.root_type in ("Expense", "Asset"):

        return debit - credit

    else:

        return credit - debit


# =========================================================
# MAPPING VALUE
# =========================================================

def get_mapping_value(row, filters):

    account = row.get("account")

    if not account:
        return 0

    balance_type = (
        row.get("balance_type")
        or "Period Balance"
    )

    # -----------------------------------------------------
    # PERIOD BALANCE
    # -----------------------------------------------------

    if balance_type == "Period Balance":

        return get_account_balance(
            account,
            filters,
            filters.get("from_date"),
            filters.get("to_date")
        )

    # -----------------------------------------------------
    # OPENING BALANCE
    # -----------------------------------------------------

    if balance_type == "Opening Balance":

        from_date = filters.get("from_date")

        if not from_date:
            return 0

        opening_date = add_days(
            from_date,
            -1
        )

        return get_account_balance(
            account,
            filters,
            None,
            opening_date
        )

    # -----------------------------------------------------
    # CLOSING BALANCE
    # -----------------------------------------------------

    if balance_type == "Closing Balance":

        return get_account_balance(
            account,
            filters,
            None,
            filters.get("to_date")
        )

    return 0


# =========================================================
# BUILD SIDE BY SIDE ROWS
# =========================================================

def build_rows(expense_rows, income_rows):

    rows = []

    max_length = max(
        len(expense_rows),
        len(income_rows)
    )

    for i in range(max_length):

        expense = (
            expense_rows[i]
            if i < len(expense_rows)
            else None
        )

        income = (
            income_rows[i]
            if i < len(income_rows)
            else None
        )

        rows.append({
            "expense": (
                expense["label"]
                if expense
                else ""
            ),

            "expense_amount": (
                expense["value"]
                if expense
                else ""
            ),

            "income": (
                income["label"]
                if income
                else ""
            ),

            "income_amount": (
                income["value"]
                if income
                else ""
            )
        })

    return rows


# =========================================================
# GET SECTION DATA
# =========================================================

def get_section_data(section, filters):

    mappings = get_statement_mappings(section)

    expense_rows = []
    income_rows = []

    for row in mappings:

        value = get_mapping_value(
            row,
            filters
        )
        
        if (
        not filters.get("show_zero_values")
        and not flt(value)
        ):
            continue

        item = {
            "label": row.get("statement_type"),
            "value": value
        }

        if row.get("type") == "Income":

            income_rows.append(item)

        else:

            expense_rows.append(item)

    expense_total = sum(
        flt(row["value"])
        for row in expense_rows
    )

    income_total = sum(
        flt(row["value"])
        for row in income_rows
    )

    return {
        "expense_rows": expense_rows,
        "income_rows": income_rows,
        "expense_total": expense_total,
        "income_total": income_total
    }


# =========================================================
# TRADING ACCOUNT
# =========================================================

def get_trading_values(filters):

    trading = get_section_data(
        "Trading Account",
        filters
    )

    trading["gross_profit"] = (
        trading["income_total"]
        - trading["expense_total"]
    )

    return trading


# =========================================================
# PROFIT & LOSS
# =========================================================

def get_profit_loss_values(
    filters,
    gross_profit=0
):

    pnl = get_section_data(
        "Profit & Loss Account",
        filters
    )

    # Gross profit is income in P&L
    if gross_profit >= 0:

        pnl["income_total"] += gross_profit

    else:

        pnl["expense_total"] += abs(
            gross_profit
        )

    pnl["net_profit"] = (
        pnl["income_total"]
        - pnl["expense_total"]
    )

    return pnl


# =========================================================
# KPI
# =========================================================

def get_kpi(trading, pnl):

    kpi = {}

    sales = 0

    # Find Sales from Trading income mappings
    for row in trading["income_rows"]:

        if row["label"] == "Sales":

            sales += flt(row["value"])

    gross_profit = flt(
        trading["gross_profit"]
    )

    net_profit = flt(
        pnl["net_profit"]
    )

    operating_expense = flt(
        pnl["expense_total"]
    )

    if sales:

        kpi["gross_profit_percent"] = (
            gross_profit / sales
        ) * 100

        kpi["net_profit_percent"] = (
            net_profit / sales
        ) * 100

        kpi["operating_expense_ratio"] = (
            operating_expense / sales
        ) * 100

    else:

        kpi["gross_profit_percent"] = 0
        kpi["net_profit_percent"] = 0
        kpi["operating_expense_ratio"] = 0

    kpi["net_profit"] = net_profit

    return kpi


# =========================================================
# FINAL DATA
# =========================================================

def get_data(filters):

    rows = []

    # -----------------------------------------------------
    # TRADING
    # -----------------------------------------------------

    trading = get_trading_values(filters)

    rows.append({
        "expense": "TRADING ACCOUNT",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })

    rows.extend(
        build_rows(
            trading["expense_rows"],
            trading["income_rows"]
        )
    )

    rows.append({
        "expense": "Subtotal",
        "expense_amount": trading["expense_total"],
        "income": "Subtotal",
        "income_amount": trading["income_total"]
    })

    # Gross Profit / Gross Loss
    if trading["gross_profit"] >= 0:

        rows.append({
            "expense": "Gross Profit",
            "expense_amount": trading["gross_profit"],
            "income": "",
            "income_amount": ""
        })

        trading_total = trading["income_total"]

    else:

        rows.append({
            "expense": "",
            "expense_amount": "",
            "income": "Gross Loss",
            "income_amount": abs(
                trading["gross_profit"]
            )
        })

        trading_total = trading["expense_total"]

    rows.append({
        "expense": "Total",
        "expense_amount": trading_total,
        "income": "Total",
        "income_amount": trading_total
    })

    # -----------------------------------------------------
    # P&L
    # -----------------------------------------------------

    pnl = get_profit_loss_values(
        filters,
        trading["gross_profit"]
    )

    rows.append({
        "expense": "PROFIT & LOSS ACCOUNT",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })

    rows.extend(
        build_rows(
            pnl["expense_rows"],
            pnl["income_rows"]
        )
    )

    # P&L subtotal
    rows.append({
        "expense": "Subtotal",
        "expense_amount": pnl["expense_total"],
        "income": "Subtotal",
        "income_amount": pnl["income_total"]
    })

    # Net Profit / Net Loss
    # if pnl["net_profit"] >= 0:

    #     rows.append({
    #         "expense": "Net Profit",
    #         "expense_amount": pnl["net_profit"],
    #         "income": "",
    #         "income_amount": ""
    #     })

    #     pnl_total = pnl["income_total"]

    # else:

    #     rows.append({
    #         "expense": "",
    #         "expense_amount": "",
    #         "income": "Net Loss",
    #         "income_amount": abs(
    #             pnl["net_profit"]
    #         )
    #     })

    #     pnl_total = pnl["expense_total"]
    pnl_total = max(
        pnl["expense_total"],
        pnl["income_total"]
    )

    rows.append({
        "expense": "Total",
        "expense_amount": pnl_total,
        "income": "Total",
        "income_amount": pnl_total
    })

    # -----------------------------------------------------
    # KPI
    # -----------------------------------------------------

    kpi = get_kpi(
        trading,
        pnl
    )

    rows.append({
        "expense": "KEY PERFORMANCE METRICS",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })

    rows.extend([
        {
            "expense": "Gross Profit %",
            "expense_amount": kpi["gross_profit_percent"],
            "income": "",
            "income_amount": ""
        },
        {
            "expense": "Net Profit %",
            "expense_amount": kpi["net_profit_percent"],
            "income": "",
            "income_amount": ""
        },
        {
            "expense": "Operating Expense Ratio %",
            "expense_amount": kpi["operating_expense_ratio"],
            "income": "",
            "income_amount": ""
        }
    ])

    return rows