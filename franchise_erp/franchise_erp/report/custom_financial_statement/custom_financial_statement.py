# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):

    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data

from frappe import _

def get_columns(filters):

    fy = ""

    if filters.get("fiscal_year"):
        fy = filters.get("fiscal_year")
    elif filters.get("from_date"):
        fy = filters.get("from_date")[:4] + "-" + filters.get("to_date")[:4]

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
    
def get_statement_account(statement_type, company=None):

    settings = frappe.get_single("TZU Setting")

    mappings = settings.get("financial_statement_account_mapping") or []

    for row in mappings:
        if (
            row.get("statement_type") == statement_type
            and row.get("enabled")
        ):
            return row.get("account")

    return None   
    
def get_account_balance(account_name, filters):

    conditions = [
        "gle.is_cancelled = 0",
        "acc.name = gle.account"
    ]

    values = {}

    if filters.get("company"):
        conditions.append("gle.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("cost_center"):
        conditions.append("gle.cost_center = %(cost_center)s")
        values["cost_center"] = filters.get("cost_center")

    if filters.get("project"):
        conditions.append("gle.project = %(project)s")
        values["project"] = filters.get("project")

    if filters.get("finance_book"):
        conditions.append("gle.finance_book = %(finance_book)s")
        values["finance_book"] = filters.get("finance_book")

    values["account"] = account_name

    row = frappe.db.sql(
        f"""
        SELECT

            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit

        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE
            ({' AND '.join(conditions)})
            AND (
                acc.name = %(account)s
                OR acc.parent_account = %(account)s
            )
        """,
        values,
        as_dict=True,
    )

    if not row:
        return 0

    debit = flt(row[0].debit)
    credit = flt(row[0].credit)

    return debit - credit

def get_group_balance(root_account, filters):
    """
    Returns total balance of an Account Group including all child accounts.
    """

    account = frappe.db.get_value(
        "Account",
        root_account,
        ["lft", "rgt", "root_type"],
        as_dict=True
    )

    if not account:
        return 0

    conditions = [
        "gle.is_cancelled = 0",
        "acc.lft >= %(lft)s",
        "acc.rgt <= %(rgt)s",
        "gle.account = acc.name"
    ]

    values = {
        "lft": account.lft,
        "rgt": account.rgt
    }

    if filters.get("company"):
        conditions.append("gle.company=%(company)s")
        values["company"] = filters["company"]

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("cost_center"):
        conditions.append("gle.cost_center=%(cost_center)s")
        values["cost_center"] = filters["cost_center"]

    if filters.get("project"):
        conditions.append("gle.project=%(project)s")
        values["project"] = filters["project"]

    if filters.get("finance_book"):
        conditions.append("gle.finance_book=%(finance_book)s")
        values["finance_book"] = filters["finance_book"]

    result = frappe.db.sql(
        f"""
        SELECT
            COALESCE(SUM(gle.debit), 0) AS debit,
            COALESCE(SUM(gle.credit), 0) AS credit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account
        WHERE {' AND '.join(conditions)}
        """,
        values,
        as_dict=True,
    )

    if not result:
        return 0

    debit = flt(result[0].debit)
    credit = flt(result[0].credit)

    # ERPNext style sign handling
    if account.root_type in ("Expense", "Asset"):
        return debit - credit
    else:  # Income, Liability, Equity
        return credit - debit


def get_trading_values(filters):

    trading = {}

    # ===========================
    # OPENING STOCK
    # ===========================

    opening_stock_account = get_statement_account("Opening Stock")

    trading["opening_stock"] = 0

    if opening_stock_account:
        trading["opening_stock"] = get_group_balance(
            opening_stock_account,
            filters
        )

    # ===========================
    # PURCHASES
    # ===========================

    purchase_account = get_statement_account("Purchases")

    purchase = 0

    if purchase_account:
        purchase = get_group_balance(
            purchase_account,
            filters
        )

    # ===========================
    # PURCHASE RETURN
    # ===========================

    purchase_return_account = get_statement_account(
        "Purchase Return"
    )

    purchase_return = 0

    if purchase_return_account:
        purchase_return = get_group_balance(
            purchase_return_account,
            filters
        )

    # Net Purchases
    trading["purchase"] = (
        flt(purchase) - flt(purchase_return)
    )

    # ===========================
    # SALES
    # ===========================

    sales_account = get_statement_account("Sales")

    sales = 0

    if sales_account:
        sales = get_group_balance(
            sales_account,
            filters
        )

    trading["sales"] = abs(flt(sales))

    # ===========================
    # CLOSING STOCK
    # ===========================

    closing_stock_account = get_statement_account(
        "Closing Stock"
    )

    trading["closing_stock"] = 0

    if closing_stock_account:
        trading["closing_stock"] = get_group_balance(
            closing_stock_account,
            filters
        )

    # ===========================
    # TRADING TOTALS
    # ===========================

    trading["expense_total"] = (
        flt(trading["opening_stock"])
        + flt(trading["purchase"])
    )

    trading["income_total"] = (
        flt(trading["sales"])
        + flt(trading["closing_stock"])
    )

    # ===========================
    # GROSS PROFIT
    # ===========================

    trading["gross_profit"] = (
        trading["income_total"]
        - trading["expense_total"]
    )

    trading["grand_total"] = max(
        trading["expense_total"],
        trading["income_total"]
    )

    return trading


def get_profit_loss_values(filters):

    pnl = {}

    # ===========================
    # ADMINISTRATIVE EXPENSES
    # ===========================

    account = get_statement_account(
        "Administrative Expenses"
    )

    pnl["administrative"] = 0

    if account:
        pnl["administrative"] = get_group_balance(
            account,
            filters
        )

    # ===========================
    # SELLING & DISTRIBUTION
    # ===========================

    account = get_statement_account(
        "Selling & Distribution Expenses"
    )

    pnl["selling"] = 0

    if account:
        pnl["selling"] = get_group_balance(
            account,
            filters
        )

    # ===========================
    # FINANCE COSTS
    # ===========================

    account = get_statement_account(
        "Finance Costs"
    )

    pnl["finance"] = 0

    if account:
        pnl["finance"] = get_group_balance(
            account,
            filters
        )

    # ===========================
    # DEPRECIATION
    # ===========================

    account = get_statement_account(
        "Depreciation"
    )

    pnl["depreciation"] = 0

    if account:
        pnl["depreciation"] = get_group_balance(
            account,
            filters
        )

    # ===========================
    # PROVISION FOR TAX
    # ===========================

    account = get_statement_account(
        "Provision for Tax"
    )

    pnl["tax"] = 0

    if account:
        pnl["tax"] = get_group_balance(
            account,
            filters
        )

    # ===========================
    # EXPENSE TOTAL
    # ===========================

    pnl["expense_total"] = (
        flt(pnl["administrative"])
        + flt(pnl["selling"])
        + flt(pnl["finance"])
        + flt(pnl["depreciation"])
        + flt(pnl["tax"])
    )

    # ===========================
    # OTHER INCOME
    # ===========================

    account = get_statement_account(
        "Other Income"
    )

    pnl["other_income"] = 0

    if account:
        pnl["other_income"] = abs(
            get_group_balance(
                account,
                filters
            )
        )

    # ===========================
    # INVESTMENT INCOME
    # ===========================

    account = get_statement_account(
        "Investment Income"
    )

    pnl["investment_income"] = 0

    if account:
        pnl["investment_income"] = abs(
            get_group_balance(
                account,
                filters
            )
        )

    # ===========================
    # INCOME TOTAL
    # ===========================

    pnl["income_total"] = (
        flt(pnl["other_income"])
        + flt(pnl["investment_income"])
    )

    # ===========================
    # NET PROFIT
    # ===========================

    pnl["net_profit"] = (
        pnl["income_total"]
        - pnl["expense_total"]
    )

    pnl["grand_total"] = max(
        pnl["expense_total"],
        pnl["income_total"]
    )

    return pnl


def get_kpi(trading, pnl):

    kpi = {}

    sales = flt(trading.get("sales"))
    gross_profit = flt(trading.get("gross_profit"))

    expense_total = flt(pnl.get("expense_total"))
    other_income = flt(pnl.get("income_total"))

    # Net Profit
    net_profit = gross_profit + other_income - expense_total

    # Gross Profit %
    if sales:
        kpi["gross_profit_percent"] = (
            gross_profit / sales
        ) * 100
    else:
        kpi["gross_profit_percent"] = 0

    # Net Profit %
    if sales:
        kpi["net_profit_percent"] = (
            net_profit / sales
        ) * 100
    else:
        kpi["net_profit_percent"] = 0

    # Operating Expense Ratio %
    if sales:
        kpi["operating_expense_ratio"] = (
            expense_total / sales
        ) * 100
    else:
        kpi["operating_expense_ratio"] = 0

    kpi["net_profit"] = net_profit

    return kpi



def get_data(filters):

    rows = []

    trading = get_trading_values(filters)
    pnl = get_profit_loss_values(filters)

    kpi = get_kpi(trading, pnl)


    # ======================================
    # TRADING ACCOUNT HEADER
    # ======================================

    rows.append({
        "expense": "TRADING ACCOUNT",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })


    rows.extend([
    {
        "expense": "Opening Stock",
        "expense_amount": trading["opening_stock"],
        "income": "Sales",
        "income_amount": trading["sales"],
    },
    {
        "expense": "Purchase",
        "expense_amount": trading["purchase"],
        "income": "Closing Stock",
        "income_amount": trading["closing_stock"],
    },
    {
        "expense": "Subtotal",
        "expense_amount": trading["expense_total"],
        "income": "Subtotal",
        "income_amount": trading["income_total"],
    },
    {
        "expense": "Gross Profit",
        "expense_amount": trading["gross_profit"],
        "income": "",
        "income_amount": "",
    },
    {
        "expense": "Total",
        "expense_amount": trading["grand_total"],
        "income": "Total",
        "income_amount": trading["grand_total"],
    },
])
    # ======================================
    # PROFIT & LOSS ACCOUNT HEADER
    # ======================================

    rows.append({
        "expense": "PROFIT & LOSS ACCOUNT",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })


    rows.extend([
        {
            "expense": "Administrative Expenses",
            "expense_amount": pnl["administrative"],
            "income": "Other Income",
            "income_amount": pnl["other_income"],
        },
        {
            "expense": "Selling & Distribution Expenses",
            "expense_amount": pnl["selling"],
            "income": "Investment Income",
            "income_amount": pnl["investment_income"],
        },
        {
            "expense": "Finance Costs",
            "expense_amount": pnl["finance"],
            "income": "Subtotal",
            "income_amount": pnl["income_total"],
        },
        {
            "expense": "Depreciation",
            "expense_amount": pnl["depreciation"],
            "income": "",
            "income_amount": "",
        },
        {
            "expense": "Provision for Tax",
            "expense_amount": pnl["tax"],
            "income": "",
            "income_amount": "",
        },
        {
            "expense": "Subtotal",
            "expense_amount": pnl["expense_total"],
            "income": "",
            "income_amount": "",
        },
        {
            "expense": "",
            "expense_amount": "",
            "income": "",
            "income_amount": "",
        },
        {
            "expense": "Total",
            "expense_amount": pnl["grand_total"],
            "income": "Total",
            "income_amount": pnl["grand_total"],
        },
    ])


    # ======================================
    # KEY PERFORMANCE METRICS HEADER
    # ======================================

    rows.append({
        "expense": "KEY PERFORMANCE METRICS",
        "expense_amount": None,
        "income": None,
        "income_amount": None
    })


    kpi_rows = [
        ("Gross Profit %", kpi.get("gross_profit_percent")),
        ("Net Profit %", kpi.get("net_profit_percent")),
        ("Operating Expense Ratio %", kpi.get("operating_expense_ratio")),
    ]


    for label, value in kpi_rows:

        rows.append({
            "expense": label,
            "expense_amount": value,
            "income": "",
            "income_amount": ""
        })


    return rows