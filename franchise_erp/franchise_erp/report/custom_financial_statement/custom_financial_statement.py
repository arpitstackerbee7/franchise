# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, add_days


# =========================================================
# EXECUTE
# =========================================================

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

    elif (
        filters.get("from_date")
        and filters.get("to_date")
    ):

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
# GET MAPPINGS
# =========================================================

def get_statement_mappings(section=None):

    settings = frappe.get_single("TZU Setting")

    mappings = (
        settings.get(
            "financial_statement_account_mapping"
        )
        or []
    )

    result = []

    for row in mappings:

        if not row.get("enabled"):
            continue

        if not row.get("statement_type"):
            continue

        if not row.get("account"):
            continue

        if (
            section is not None
            and row.get("statement_section") != section
        ):
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
    to_date=None,
    exclude_period_closing=False
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

    # =====================================================
    # COMPANY
    # =====================================================

    if filters.get("company"):

        conditions.append(
            "gle.company = %(company)s"
        )

        values["company"] = filters.get(
            "company"
        )

    # =====================================================
    # DATE
    # =====================================================

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

    # =====================================================
    # COST CENTER
    # =====================================================

    if filters.get("cost_center"):

        conditions.append(
            "gle.cost_center = %(cost_center)s"
        )

        values["cost_center"] = filters.get(
            "cost_center"
        )

    # =====================================================
    # PROJECT
    # =====================================================

    if filters.get("project"):

        conditions.append(
            "gle.project = %(project)s"
        )

        values["project"] = filters.get(
            "project"
        )

    # =====================================================
    # FINANCE BOOK
    # =====================================================

    if filters.get("finance_book"):

        conditions.append(
            "gle.finance_book = %(finance_book)s"
        )

        values["finance_book"] = filters.get(
            "finance_book"
        )

    # =====================================================
    # PERIOD CLOSING VOUCHER
    # =====================================================

    if exclude_period_closing:

        conditions.append(
            "gle.voucher_type != "
            "'Period Closing Voucher'"
        )

    # =====================================================
    # SQL
    # =====================================================

    result = frappe.db.sql(
        f"""
        SELECT

            COALESCE(
                SUM(gle.debit),
                0
            ) AS debit,

            COALESCE(
                SUM(gle.credit),
                0
            ) AS credit

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

    debit = flt(
        result[0].debit
    )

    credit = flt(
        result[0].credit
    )

    # =====================================================
    # SIGN
    # =====================================================

    if account.root_type in (
        "Expense",
        "Asset"
    ):

        return debit - credit

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

    # =====================================================
    # PERIOD BALANCE
    # =====================================================

    if balance_type == "Period Balance":

        return get_account_balance(
            account,
            filters,
            filters.get("from_date"),
            filters.get("to_date")
        )

    # =====================================================
    # OPENING BALANCE
    # =====================================================

    if balance_type == "Opening Balance":

        from_date = filters.get(
            "from_date"
        )

        if not from_date:
            return 0

        opening_date = add_days(
            from_date,
            -1
        )

        # -------------------------------------------------
        # OPENING STOCK
        # -------------------------------------------------

        if (
            str(
                row.get("statement_type")
                or ""
            ).strip().lower()
            == "opening stock"
        ):

            return get_account_balance(
                account,
                filters,
                None,
                opening_date,
                exclude_period_closing=True
            )

        return get_account_balance(
            account,
            filters,
            None,
            opening_date
        )

    # =====================================================
    # CLOSING BALANCE
    # =====================================================

    if balance_type == "Closing Balance":

        return get_account_balance(
            account,
            filters,
            None,
            filters.get("to_date")
        )

    return 0


# =========================================================
# BUILD SIDE-BY-SIDE ROWS
# =========================================================

def build_rows(
    expense_rows,
    income_rows
):

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

def get_section_data(
    section,
    filters
):

    mappings = get_statement_mappings(
        section
    )

    expense_rows = []
    income_rows = []

    for row in mappings:

        value = get_mapping_value(
            row,
            filters
        )

        # -------------------------------------------------
        # ZERO VALUE FILTER
        # -------------------------------------------------

        if (
            not filters.get("show_zero_values")
            and not flt(value)
        ):

            continue

        item = {

            "label": row.get(
                "statement_type"
            ),

            "value": value
        }

        if row.get("type") == "Income":

            income_rows.append(
                item
            )

        else:

            expense_rows.append(
                item
            )

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
# DYNAMIC TRADING SECTION DETECTION
# =========================================================

def is_trading_section(section_data):

    labels = {

        str(
            row.get("label")
            or ""
        ).strip().lower()

        for row in (
            section_data["expense_rows"]
            + section_data["income_rows"]
        )
    }

    trading_labels = {

        "opening stock",

        "purchase",

        "sales",

        "closing stock"
    }

    return bool(
        labels.intersection(
            trading_labels
        )
    )


# =========================================================
# DYNAMIC KPI SECTION DETECTION
# =========================================================

def is_kpi_section(section_data):

    labels = {

        str(
            row.get("label")
            or ""
        ).strip().lower()

        for row in (
            section_data["expense_rows"]
            + section_data["income_rows"]
        )
    }

    kpi_labels = {

        "gross profit %",

        "net profit %",

        "operating expense ratio %"
    }

    return bool(
        labels.intersection(
            kpi_labels
        )
    )


# =========================================================
# KPI CALCULATION
# =========================================================

def get_kpi(
    trading,
    pnl
):

    kpi = {}

    sales = 0

    # =====================================================
    # SALES
    # =====================================================

    for row in trading["income_rows"]:

        if (
            str(
                row.get("label")
                or ""
            ).strip().lower()
            == "sales"
        ):

            sales += flt(
                row.get("value")
            )

    gross_profit = flt(
        trading.get(
            "gross_profit",
            0
        )
    )

    net_profit = flt(
        pnl.get(
            "net_profit",
            0
        )
    )

    operating_expense = flt(
        pnl.get(
            "expense_total",
            0
        )
    )

    # =====================================================
    # CALCULATE
    # =====================================================

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
# GET DYNAMIC SECTIONS
# =========================================================

def get_statement_sections():

    settings = frappe.get_single(
        "TZU Setting"
    )

    mappings = (
        settings.get(
            "financial_statement_account_mapping"
        )
        or []
    )

    sections = []

    for row in mappings:

        if not row.get("enabled"):
            continue

        section = row.get(
            "statement_section"
        )

        if not section:
            continue

        if section not in sections:

            sections.append(
                section
            )

    return sections


# =========================================================
# GET DATA
# =========================================================

def get_data(filters):

    rows = []

    # =====================================================
    # GET ALL SECTIONS DYNAMICALLY
    # =====================================================

    sections = get_statement_sections()

    section_data_map = {}

    trading_section = None
    trading = None

    kpi_section = None

    # =====================================================
    # FIRST PASS
    # Load all section data
    # =====================================================

    for section in sections:

        section_data = get_section_data(
            section,
            filters
        )

        section_data_map[
            section
        ] = section_data

        # -------------------------------------------------
        # TRADING SECTION
        # -------------------------------------------------

        if (
            trading_section is None
            and is_trading_section(
                section_data
            )
        ):

            trading_section = section

            trading = section_data

            trading["gross_profit"] = (

                trading["income_total"]

                - trading["expense_total"]
            )

        # -------------------------------------------------
        # KPI SECTION
        # -------------------------------------------------

        if (
            kpi_section is None
            and is_kpi_section(
                section_data
            )
        ):

            kpi_section = section

    # =====================================================
    # DISPLAY SECTIONS
    # =====================================================

    for section in sections:

        section_data = (
            section_data_map[section]
        )

        # =================================================
        # DYNAMIC SECTION HEADER
        # =================================================

        rows.append({

            "expense": str(
                section
            ).upper(),

            "expense_amount": None,

            "income": None,

            "income_amount": None
        })

        # =================================================
        # KPI SECTION
        # =================================================

        if section == kpi_section:

            # KPI rows are added later after calculation.

            continue

        # =================================================
        # NORMAL SECTION ROWS
        # =================================================

        rows.extend(
            build_rows(

                section_data[
                    "expense_rows"
                ],

                section_data[
                    "income_rows"
                ]
            )
        )

        # =================================================
        # SUBTOTAL
        # =================================================

        rows.append({

            "expense": "Subtotal",

            "expense_amount": (
                section_data[
                    "expense_total"
                ]
            ),

            "income": "Subtotal",

            "income_amount": (
                section_data[
                    "income_total"
                ]
            )
        })

        # =================================================
        # TRADING GROSS PROFIT / LOSS
        # =================================================

        if section == trading_section:

            gross_profit = flt(
                trading[
                    "gross_profit"
                ]
            )

            if gross_profit >= 0:

                rows.append({

                    "expense": "Gross Profit",

                    "expense_amount":
                        gross_profit,

                    "income": "",

                    "income_amount": ""
                })

                section_total = (
                    section_data[
                        "income_total"
                    ]
                )

            else:

                rows.append({

                    "expense": "",

                    "expense_amount": "",

                    "income": "Gross Loss",

                    "income_amount":
                        abs(gross_profit)
                })

                section_total = (
                    section_data[
                        "expense_total"
                    ]
                )

        else:

            section_total = max(

                section_data[
                    "expense_total"
                ],

                section_data[
                    "income_total"
                ]
            )

        # =================================================
        # TOTAL
        # =================================================

        rows.append({

            "expense": "Total",

            "expense_amount":
                section_total,

            "income": "Total",

            "income_amount":
                section_total
        })

    # =====================================================
    # NO TRADING SECTION
    # =====================================================

    if not trading:

        return rows

    # =====================================================
    # P&L CALCULATION
    # =====================================================

    pnl = {

        "expense_total": 0,

        "income_total": 0,

        "net_profit": 0,

        "expense_rows": [],

        "income_rows": []
    }

    # =====================================================
    # ALL NON-TRADING / NON-KPI SECTIONS
    # =====================================================

    for section in sections:

        if section == trading_section:
            continue

        if section == kpi_section:
            continue

        section_data = (
            section_data_map[
                section
            ]
        )

        pnl["expense_total"] += flt(
            section_data[
                "expense_total"
            ]
        )

        pnl["income_total"] += flt(
            section_data[
                "income_total"
            ]
        )

    # =====================================================
    # ADD GROSS PROFIT / LOSS
    # =====================================================

    if trading["gross_profit"] >= 0:

        pnl["income_total"] += flt(
            trading["gross_profit"]
        )

    else:

        pnl["expense_total"] += abs(
            trading["gross_profit"]
        )

    # =====================================================
    # NET PROFIT
    # =====================================================

    pnl["net_profit"] = (

        pnl["income_total"]

        - pnl["expense_total"]
    )

    # =====================================================
    # KPI
    # =====================================================

    kpi = get_kpi(
        trading,
        pnl
    )

    # =====================================================
    # INSERT KPI DATA INTO DYNAMIC KPI SECTION
    # =====================================================

    if kpi_section:

        kpi_rows = [

            {
                "expense": "Gross Profit %",

                "expense_amount":
                    kpi[
                        "gross_profit_percent"
                    ],

                "income": "",

                "income_amount": ""
            },

            {
                "expense": "Net Profit %",

                "expense_amount":
                    kpi[
                        "net_profit_percent"
                    ],

                "income": "",

                "income_amount": ""
            },

            {
                "expense":
                    "Operating Expense Ratio %",

                "expense_amount":
                    kpi[
                        "operating_expense_ratio"
                    ],

                "income": "",

                "income_amount": ""
            }
        ]

        # -------------------------------------------------
        # Find KPI section header
        # -------------------------------------------------

        kpi_header_index = None

        for index, row in enumerate(rows):

            if (

                row.get("expense")
                == str(
                    kpi_section
                ).upper()

                and row.get(
                    "expense_amount"
                ) is None

                and row.get(
                    "income"
                ) is None

                and row.get(
                    "income_amount"
                ) is None
            ):

                kpi_header_index = index

                break

        # -------------------------------------------------
        # Insert KPI rows immediately
        # after dynamic section heading
        # -------------------------------------------------

        if kpi_header_index is not None:

            for offset, kpi_row in enumerate(
                kpi_rows,
                start=1
            ):

                rows.insert(

                    kpi_header_index
                    + offset,

                    kpi_row
                )

    return rows