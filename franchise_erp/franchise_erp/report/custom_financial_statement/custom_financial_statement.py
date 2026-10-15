# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, add_days


# ============================================================
# EXECUTE
# ============================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("from_date"):
        frappe.throw(_("From Date is required"))

    if not filters.get("to_date"):
        frappe.throw(_("To Date is required"))

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


# ============================================================
# COLUMNS
# ============================================================

def get_columns(filters=None):

    return [
        {
            "label": _("Expenses"),
            "fieldname": "expense",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Expenses-FY"),
            "fieldname": "expense_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Income"),
            "fieldname": "income",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Income-FY"),
            "fieldname": "income_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


# ============================================================
# STATEMENT MAPPINGS
# ============================================================

def get_statement_mappings(section=None):
    """
    Read Statement mappings from TZU Setting.

    IMPORTANT:

    Statement Type order is EXACTLY the order of rows
    inside financial_statement_account_mapping.

    Account hierarchy is NOT used here.
    """

    settings = frappe.get_single("TZU Setting")

    mappings = (
        settings.get("financial_statement_account_mapping")
        or []
    )

    result = []

    for sequence, child in enumerate(mappings):

        # ----------------------------------------------------
        # Enabled
        # ----------------------------------------------------

        if not child.get("enabled"):
            continue

        # ----------------------------------------------------
        # Statement Type
        # ----------------------------------------------------

        statement_type = str(
            child.get("statement_type") or ""
        ).strip()

        if not statement_type:
            continue

        # ----------------------------------------------------
        # Account
        # ----------------------------------------------------

        account = child.get("account")

        if not account:
            continue

        # ----------------------------------------------------
        # Section
        # ----------------------------------------------------

        row_section = str(
            child.get("statement_section") or ""
        ).strip()

        if section and row_section != section:
            continue

        # ----------------------------------------------------
        # Copy child row
        # ----------------------------------------------------

        row = frappe._dict(
            child.as_dict()
        )

        # Exact TZU Setting sequence
        row["_sequence"] = sequence

        # ----------------------------------------------------
        # Statement Parent
        # ----------------------------------------------------

        row["statement_parent"] = str(
            child.get("statement_parent") or ""
        ).strip()

        result.append(row)

    # --------------------------------------------------------
    # ALWAYS preserve TZU Setting order
    # --------------------------------------------------------

    result.sort(
        key=lambda row: row.get(
            "_sequence",
            999999
        )
    )

    return result


# ============================================================
# STATEMENT SIDE
# ============================================================

def get_statement_side(mapping):

    statement_side = str(
        mapping.get("type")
        or mapping.get("statement_type_type")
        or ""
    ).strip().lower()

    if statement_side == "income":
        return "income"

    if statement_side == "expense":
        return "expense"

    frappe.log_error(
        title="Custom Financial Statement - Invalid Type",
        message=(
            f"Statement Type: "
            f"{mapping.get('statement_type')}\n"
            f"Account: "
            f"{mapping.get('account')}\n"
            f"Type: "
            f"{mapping.get('type')}"
        ),
    )

    return None


# ============================================================
# STATEMENT TYPE
# ============================================================

def get_statement_type(mapping):

    return str(
        mapping.get("statement_type") or ""
    ).strip()


# ============================================================
# STATEMENT PARENT
# ============================================================

def get_statement_parent(mapping):

    return str(
        mapping.get("statement_parent") or ""
    ).strip()


# ============================================================
# FIND STATEMENT PARENT
# ============================================================

def find_statement_parent(
    mapping,
    mappings,
):
    """
    Parent-child relationship is controlled ONLY by
    Statement Parent field.

    Example:

    Statement Type:
        JOB CHARGES

    Statement Parent:
        DIRECT EXPENSES

    Therefore:

        DIRECT EXPENSES
            JOB CHARGES
    """

    parent_name = get_statement_parent(
        mapping
    )

    if not parent_name:
        return None

    current_sequence = mapping.get(
        "_sequence",
        999999
    )

    current_side = get_statement_side(
        mapping
    )

    # --------------------------------------------------------
    # Find exact Statement Type
    # --------------------------------------------------------

    candidates = []

    for other in mappings:

        if other is mapping:
            continue

        other_statement_type = get_statement_type(
            other
        )

        if (
            other_statement_type
            != parent_name
        ):
            continue

        # Parent must be on same side
        if (
            get_statement_side(other)
            != current_side
        ):
            continue

        candidates.append(other)

    if not candidates:
        return None

    # --------------------------------------------------------
    # Normally Statement Type should be unique.
    #
    # If duplicate exists, use first row according to
    # TZU Setting order.
    # --------------------------------------------------------

    candidates.sort(
        key=lambda row: row.get(
            "_sequence",
            999999
        )
    )

    return candidates[0]


# ============================================================
# BUILD STATEMENT TREE
# ============================================================

def build_statement_tree(
    mappings,
):
    """
    Build explicit Statement Type hierarchy.

    Parent-child relationship is based ONLY on:

        statement_parent

    NOT on Account.parent_account.
    """

    children_map = {}

    for mapping in mappings:

        parent = find_statement_parent(
            mapping,
            mappings,
        )

        if not parent:
            continue

        parent_id = id(parent)

        children_map.setdefault(
            parent_id,
            []
        ).append(
            mapping
        )

    # --------------------------------------------------------
    # Preserve TZU Setting order
    # --------------------------------------------------------

    for parent_id in children_map:

        children_map[parent_id].sort(
            key=lambda row: row.get(
                "_sequence",
                999999
            )
        )

    return children_map


# ============================================================
# ACCOUNT BALANCE
# ============================================================

def get_account_balance(
    account,
    company,
    from_date,
    to_date,
    cost_center=None,
    project=None,
    finance_book=None,
    exclude_period_closing=False,
):
    """
    Get balance for complete Account subtree.
    """

    if not account:
        return 0

    account_details = frappe.db.get_value(
        "Account",
        account,
        [
            "lft",
            "rgt",
            "root_type",
        ],
        as_dict=True,
    )

    if not account_details:
        return 0

    conditions = [
        "gle.company = %(company)s",
        "gle.is_cancelled = 0",
        """
        acc.lft >= %(lft)s
        AND acc.rgt <= %(rgt)s
        """,
    ]

    values = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "lft": account_details.lft,
        "rgt": account_details.rgt,
    }

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if from_date:

        conditions.append(
            """
            gle.posting_date
            BETWEEN %(from_date)s
            AND %(to_date)s
            """
        )

    else:

        conditions.append(
            """
            gle.posting_date <= %(to_date)s
            """
        )

    # --------------------------------------------------------
    # PERIOD CLOSING
    # --------------------------------------------------------

    if exclude_period_closing:

        conditions.append(
            """
            (
                gle.voucher_type IS NULL
                OR gle.voucher_type != 'Period Closing Voucher'
            )
            """
        )

    # --------------------------------------------------------
    # COST CENTER
    # --------------------------------------------------------

    if cost_center:

        conditions.append(
            """
            (
                gle.cost_center = %(cost_center)s
                OR gle.cost_center IS NULL
                OR gle.cost_center = ''
            )
            """
        )

        values["cost_center"] = cost_center

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    if project:

        conditions.append(
            """
            (
                gle.project = %(project)s
                OR gle.project IS NULL
                OR gle.project = ''
            )
            """
        )

        values["project"] = project

    # --------------------------------------------------------
    # FINANCE BOOK
    # --------------------------------------------------------

    if finance_book:

        conditions.append(
            """
            (
                gle.finance_book = %(finance_book)s
                OR gle.finance_book IS NULL
                OR gle.finance_book = ''
            )
            """
        )

        values["finance_book"] = finance_book

    where_clause = " AND ".join(
        conditions
    )

    result = frappe.db.sql(
        f"""
        SELECT
            COALESCE(SUM(gle.debit), 0) AS debit,
            COALESCE(SUM(gle.credit), 0) AS credit

        FROM `tabGL Entry` gle

        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )

    debit = flt(
        result[0].debit
        if result
        else 0
    )

    credit = flt(
        result[0].credit
        if result
        else 0
    )

    root_type = account_details.root_type

    if root_type in (
        "Income",
        "Liability",
        "Equity",
    ):
        return credit - debit

    return debit - credit


# ============================================================
# MAPPING VALUE
# ============================================================

def get_mapping_value(
    mapping,
    filters,
):
    """
    Get value according to Balance Type.
    """

    account = mapping.get(
        "account"
    )

    if not account:
        return 0

    balance_type = str(
        mapping.get("balance_type") or ""
    ).strip().lower()

    # ========================================================
    # OPENING BALANCE
    # ========================================================

    if balance_type == "opening balance":

        from_date = filters.get(
            "from_date"
        )

        if not from_date:
            return 0

        opening_date = add_days(
            from_date,
            -1,
        )

        # ----------------------------------------------------
        # OPENING STOCK SPECIAL LOGIC
        # ----------------------------------------------------

        if (
            str(
                mapping.get("statement_type")
                or ""
            ).strip().lower()
            == "opening stock"
        ):

            return get_account_balance(
                account=account,
                company=filters.get(
                    "company"
                ),
                from_date=None,
                to_date=opening_date,
                cost_center=filters.get(
                    "cost_center"
                ),
                project=filters.get(
                    "project"
                ),
                finance_book=filters.get(
                    "finance_book"
                ),
                exclude_period_closing=True,
            )

        # ----------------------------------------------------
        # NORMAL OPENING
        # ----------------------------------------------------

        return get_account_balance(
            account=account,
            company=filters.get(
                "company"
            ),
            from_date=None,
            to_date=opening_date,
            cost_center=filters.get(
                "cost_center"
            ),
            project=filters.get(
                "project"
            ),
            finance_book=filters.get(
                "finance_book"
            ),
        )

    # ========================================================
    # CLOSING BALANCE
    # ========================================================

    if balance_type == "closing balance":

        return get_account_balance(
            account=account,
            company=filters.get(
                "company"
            ),
            from_date=None,
            to_date=filters.get(
                "to_date"
            ),
            cost_center=filters.get(
                "cost_center"
            ),
            project=filters.get(
                "project"
            ),
            finance_book=filters.get(
                "finance_book"
            ),
        )

    # ========================================================
    # PERIOD BALANCE
    # ========================================================

    return get_account_balance(
        account=account,
        company=filters.get(
            "company"
        ),
        from_date=filters.get(
            "from_date"
        ),
        to_date=filters.get(
            "to_date"
        ),
        cost_center=filters.get(
            "cost_center"
        ),
        project=filters.get(
            "project"
        ),
        finance_book=filters.get(
            "finance_book"
        ),
    )


# ============================================================
# BUILD ROW
# ============================================================

def make_statement_row(
    mapping,
    section,
    filters,
    children_map,
    parent_tree_id="",
    indent=0,
):
    """
    Create one Statement Type row.
    """

    statement_type = get_statement_type(
        mapping
    )

    account = mapping.get(
        "account"
    )

    side = get_statement_side(
        mapping
    )

    if not statement_type or not account or not side:
        return None

    tree_id = (
        frappe.scrub(section)
        + "__"
        + frappe.scrub(side)
        + "__"
        + str(
            mapping.get(
                "_sequence",
                999999
            )
        )
        + "__"
        + frappe.scrub(statement_type)
    )

    children = children_map.get(
        id(mapping),
        []
    )

    value = get_mapping_value(
        mapping,
        filters,
    )

    return {
        "label": statement_type,
        "value": value,
        "account": account,

        "statement_parent": get_statement_parent(
            mapping
        ),

        "indent": indent,

        "is_statement_type": 1,

        "has_children": (
            1 if children else 0
        ),

        "is_tree_node": 1,

        "is_leaf": (
            0 if children else 1
        ),

        "tree_id": tree_id,

        "tree_parent": parent_tree_id,

        "sequence": mapping.get(
            "_sequence",
            999999
        ),
    }


# ============================================================
# BUILD COMPLETE STATEMENT ROWS
# ============================================================

def build_all_statement_rows(
    mappings,
    filters,
    section,
):
    """
    Build explicit Statement Type hierarchy.

    Rules:

    1. TZU Setting controls order.
    2. Statement Parent controls hierarchy.
    3. Account hierarchy is completely ignored for
       Statement Type parent-child relation.
    4. Every configured Statement Type appears once.
    """

    if not mappings:
        return [], []

    children_map = build_statement_tree(
        mappings
    )

    expense_rows = []
    income_rows = []

    # --------------------------------------------------------
    # Roots
    #
    # A row is root when Statement Parent is blank
    # OR parent cannot be resolved.
    # --------------------------------------------------------

    roots = []

    for mapping in mappings:

        parent = find_statement_parent(
            mapping,
            mappings,
        )

        if not parent:
            roots.append(
                mapping
            )

    # --------------------------------------------------------
    # Root sequence
    # --------------------------------------------------------

    roots.sort(
        key=lambda row: row.get(
            "_sequence",
            999999
        )
    )

    # --------------------------------------------------------
    # Recursive builder
    # --------------------------------------------------------

    visited = set()

    def add_mapping(
        mapping,
        indent,
        parent_tree_id,
    ):

        mapping_id = id(mapping)

        if mapping_id in visited:
            return

        visited.add(
            mapping_id
        )

        side = get_statement_side(
            mapping
        )

        if not side:
            return

        row = make_statement_row(
            mapping=mapping,
            section=section,
            filters=filters,
            children_map=children_map,
            parent_tree_id=parent_tree_id,
            indent=indent,
        )

        if row:

            if side == "expense":
                expense_rows.append(
                    row
                )

            elif side == "income":
                income_rows.append(
                    row
                )

        children = children_map.get(
            mapping_id,
            []
        )

        children.sort(
            key=lambda child: child.get(
                "_sequence",
                999999
            )
        )

        current_tree_id = (
            row.get("tree_id")
            if row
            else parent_tree_id
        )

        for child in children:

            add_mapping(
                child,
                indent + 1,
                current_tree_id,
            )

    # --------------------------------------------------------
    # Build roots
    # --------------------------------------------------------

    for root in roots:

        add_mapping(
            root,
            0,
            "",
        )

    # --------------------------------------------------------
    # Safety:
    #
    # If there is a broken/circular parent reference,
    # don't silently lose the row.
    #
    # Add remaining mappings in original sequence.
    # --------------------------------------------------------

    remaining = [
        mapping
        for mapping in mappings
        if id(mapping) not in visited
    ]

    remaining.sort(
        key=lambda row: row.get(
            "_sequence",
            999999
        )
    )

    for mapping in remaining:

        add_mapping(
            mapping,
            0,
            "",
        )

    # --------------------------------------------------------
    # Keep side-specific sequence.
    # --------------------------------------------------------

    expense_rows.sort(
        key=lambda row: (
            row.get(
                "sequence",
                999999
            ),
            row.get(
                "indent",
                0
            ),
        )
    )

    income_rows.sort(
        key=lambda row: (
            row.get(
                "sequence",
                999999
            ),
            row.get(
                "indent",
                0
            ),
        )
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Sorting by original sequence above would destroy
    # nested visual order if a child was entered later.
    #
    # Therefore create final tree order separately.
    # --------------------------------------------------------

    def tree_order(rows):

        if not rows:
            return rows

        by_parent = {}

        for row in rows:

            by_parent.setdefault(
                row.get(
                    "tree_parent",
                    ""
                ),
                []
            ).append(row)

        for key in by_parent:

            by_parent[key].sort(
                key=lambda row: row.get(
                    "sequence",
                    999999
                )
            )

        ordered = []

        def walk(parent_id):

            children = by_parent.get(
                parent_id,
                []
            )

            for row in children:

                ordered.append(
                    row
                )

                walk(
                    row.get(
                        "tree_id",
                        ""
                    )
                )

        walk("")

        return ordered

    expense_rows = tree_order(
        expense_rows
    )

    income_rows = tree_order(
        income_rows
    )

    return (
        expense_rows,
        income_rows,
    )


# ============================================================
# BUILD SIDE BY SIDE
# ============================================================

def build_rows(
    expense_rows,
    income_rows,
):
    """
    Expense and Income are displayed side-by-side.
    """

    rows = []

    max_length = max(
        len(expense_rows),
        len(income_rows),
    )

    for index in range(
        max_length
    ):

        expense = (
            expense_rows[index]
            if index < len(expense_rows)
            else None
        )

        income = (
            income_rows[index]
            if index < len(income_rows)
            else None
        )

        data = {
            "expense": (
                expense.get("label")
                if expense
                else ""
            ),

            "expense_amount": (
                expense.get("value")
                if expense
                else ""
            ),

            "income": (
                income.get("label")
                if income
                else ""
            ),

            "income_amount": (
                income.get("value")
                if income
                else ""
            ),
        }

        # ----------------------------------------------------
        # EXPENSE META
        # ----------------------------------------------------

        if expense:

            data.update(
                {
                    "expense_account": expense.get(
                        "account",
                        "",
                    ),

                    "expense_statement_parent": expense.get(
                        "statement_parent",
                        "",
                    ),

                    "expense_indent": expense.get(
                        "indent",
                        0,
                    ),

                    "expense_is_statement_type": expense.get(
                        "is_statement_type",
                        0,
                    ),

                    "expense_has_children": expense.get(
                        "has_children",
                        0,
                    ),

                    "expense_is_tree_node": expense.get(
                        "is_tree_node",
                        0,
                    ),

                    "expense_tree_id": expense.get(
                        "tree_id",
                        "",
                    ),

                    "expense_tree_parent": expense.get(
                        "tree_parent",
                        "",
                    ),

                    "expense_is_leaf": expense.get(
                        "is_leaf",
                        1,
                    ),
                }
            )

        # ----------------------------------------------------
        # INCOME META
        # ----------------------------------------------------

        if income:

            data.update(
                {
                    "income_account": income.get(
                        "account",
                        "",
                    ),

                    "income_statement_parent": income.get(
                        "statement_parent",
                        "",
                    ),

                    "income_indent": income.get(
                        "indent",
                        0,
                    ),

                    "income_is_statement_type": income.get(
                        "is_statement_type",
                        0,
                    ),

                    "income_has_children": income.get(
                        "has_children",
                        0,
                    ),

                    "income_is_tree_node": income.get(
                        "is_tree_node",
                        0,
                    ),

                    "income_tree_id": income.get(
                        "tree_id",
                        "",
                    ),

                    "income_tree_parent": income.get(
                        "tree_parent",
                        "",
                    ),

                    "income_is_leaf": income.get(
                        "is_leaf",
                        1,
                    ),
                }
            )

        rows.append(
            data
        )

    return rows


# ============================================================
# SECTION TOTAL
# ============================================================

def calculate_section_totals(
    mappings,
    filters,
):
    """
    Total calculation is based on Statement Parent.

    RULE:

    Parent row:
        included in total

    Child row:
        NOT separately included

    Example:

        DIRECT EXPENSES
            JOB CHARGES
                Consumables

    If DIRECT EXPENSES is mapped to an Account whose balance
    already contains JOB CHARGES / Consumables, only
    DIRECT EXPENSES is counted.

    This prevents double counting.
    """

    if not mappings:
        return 0, 0

    expense_total = 0
    income_total = 0

    # --------------------------------------------------------
    # Only roots are included in total.
    # --------------------------------------------------------

    root_mappings = []

    for mapping in mappings:

        parent = find_statement_parent(
            mapping,
            mappings,
        )

        if not parent:

            root_mappings.append(
                mapping
            )

    # --------------------------------------------------------
    # Exact TZU Setting sequence
    # --------------------------------------------------------

    root_mappings.sort(
        key=lambda row: row.get(
            "_sequence",
            999999
        )
    )

    counted_expense_accounts = set()
    counted_income_accounts = set()

    for mapping in root_mappings:

        side = get_statement_side(
            mapping
        )

        if not side:
            continue

        account = mapping.get(
            "account"
        )

        if not account:
            continue

        value = get_mapping_value(
            mapping,
            filters,
        )

        # ----------------------------------------------------
        # Expense
        # ----------------------------------------------------

        if side == "expense":

            if account in counted_expense_accounts:
                continue

            counted_expense_accounts.add(
                account
            )

            expense_total += flt(
                value
            )

        # ----------------------------------------------------
        # Income
        # ----------------------------------------------------

        elif side == "income":

            if account in counted_income_accounts:
                continue

            counted_income_accounts.add(
                account
            )

            income_total += flt(
                value
            )

    return (
        expense_total,
        income_total,
    )


# ============================================================
# SECTION DATA
# ============================================================

def get_section_data(
    section,
    filters,
):

    mappings = get_statement_mappings(
        section
    )

    if not mappings:

        return {
            "section": section,
            "expense_rows": [],
            "income_rows": [],
            "expense_total": 0,
            "income_total": 0,
        }

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    (
        expense_rows,
        income_rows,
    ) = build_all_statement_rows(
        mappings=mappings,
        filters=filters,
        section=section,
    )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    (
        expense_total,
        income_total,
    ) = calculate_section_totals(
        mappings=mappings,
        filters=filters,
    )

    return {
        "section": section,
        "expense_rows": expense_rows,
        "income_rows": income_rows,
        "expense_total": expense_total,
        "income_total": income_total,
    }


# ============================================================
# SECTION HELPERS
# ============================================================

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

        section = str(
            row.get("statement_section")
            or ""
        ).strip()

        if not section:
            continue

        if section not in sections:

            sections.append(
                section
            )

    return sections


def is_trading_section(section):

    return (
        str(section or "")
        .strip()
        .lower()
        == "trading account"
    )


def is_kpi_section(section):

    section_lower = str(
        section or ""
    ).strip().lower()

    return (
        "kpi" in section_lower
        or "key performance" in section_lower
    )


# ============================================================
# KPI
# ============================================================

def get_kpi(
    section_data,
    gross_profit,
):

    expense_total = flt(
        section_data.get(
            "expense_total"
        )
    )

    income_total = flt(
        section_data.get(
            "income_total"
        )
    )

    sales = 0

    # --------------------------------------------------------
    # Sales
    # --------------------------------------------------------

    for row in section_data.get(
        "income_rows",
        [],
    ):

        if (
            row.get(
                "is_statement_type"
            )
            and str(
                row.get("label")
                or ""
            ).strip().lower()
            == "sales"
        ):

            sales += flt(
                row.get("value")
            )

    if not sales:
        sales = income_total

    # --------------------------------------------------------
    # Operating Expenses
    # --------------------------------------------------------

    operating_expenses = expense_total

    # --------------------------------------------------------
    # Gross Profit %
    # --------------------------------------------------------

    gross_profit_percent = (
        (
            gross_profit
            / sales
        )
        * 100
        if sales
        else 0
    )

    # --------------------------------------------------------
    # Operating Expense Ratio
    # --------------------------------------------------------

    operating_expense_ratio = (
        (
            operating_expenses
            / sales
        )
        * 100
        if sales
        else 0
    )

    return [
        {
            "label": "Gross Profit %",
            "value": gross_profit_percent,
            "is_kpi": 1,
        },
        {
            "label": "Operating Expense Ratio %",
            "value": operating_expense_ratio,
            "is_kpi": 1,
        },
    ]


# ============================================================
# MAIN DATA
# ============================================================

def get_data(filters):

    sections = get_statement_sections()

    if not sections:
        return []

    all_section_data = []

    gross_profit = 0

    # ========================================================
    # FIRST PASS
    # ========================================================

    for section in sections:

        section_data = get_section_data(
            section,
            filters,
        )

        all_section_data.append(
            section_data
        )

        # ----------------------------------------------------
        # Trading Account
        # ----------------------------------------------------

        if is_trading_section(
            section
        ):

            gross_profit = (
                flt(
                    section_data[
                        "income_total"
                    ]
                )
                - flt(
                    section_data[
                        "expense_total"
                    ]
                )
            )

    # ========================================================
    # FINAL ROWS
    # ========================================================

    final_rows = []

    pnl_sections = []

    kpi_section_data = None

    # ========================================================
    # SECTIONS
    # ========================================================

    for section_data in all_section_data:

        section = section_data[
            "section"
        ]

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        if is_kpi_section(
            section
        ):

            kpi_section_data = section_data
            continue

        # ----------------------------------------------------
        # SECTION HEADER
        # ----------------------------------------------------

        final_rows.append(
            {
                "expense": section,
                "expense_amount": "",
                "income": "",
                "income_amount": "",
                "is_section_header": 1,
                "section": section,
            }
        )

        # ====================================================
        # TRADING ACCOUNT
        # ====================================================

        if is_trading_section(
            section
        ):

            final_rows.extend(
                build_rows(
                    section_data[
                        "expense_rows"
                    ],
                    section_data[
                        "income_rows"
                    ],
                )
            )

            # ------------------------------------------------
            # TOTAL
            # ------------------------------------------------

            final_rows.append(
                {
                    "expense": "Total",
                    "expense_amount": section_data[
                        "expense_total"
                    ],
                    "income": "Total",
                    "income_amount": section_data[
                        "income_total"
                    ],
                    "is_total": 1,
                }
            )

            # ------------------------------------------------
            # GROSS PROFIT / LOSS
            # ------------------------------------------------

            if gross_profit >= 0:

                final_rows.append(
                    {
                        "expense": "",
                        "expense_amount": "",
                        "income": "Gross Profit",
                        "income_amount": gross_profit,
                        "is_gross_profit": 1,
                    }
                )

            else:

                final_rows.append(
                    {
                        "expense": "Gross Loss",
                        "expense_amount": abs(
                            gross_profit
                        ),
                        "income": "",
                        "income_amount": "",
                        "is_gross_profit": 1,
                    }
                )

            continue

        # ====================================================
        # P&L
        # ====================================================

        pnl_sections.append(
            section_data
        )

        final_rows.extend(
            build_rows(
                section_data[
                    "expense_rows"
                ],
                section_data[
                    "income_rows"
                ],
            )
        )

        # ----------------------------------------------------
        # SUBTOTAL
        # ----------------------------------------------------

        final_rows.append(
            {
                "expense": "Total",
                "expense_amount": section_data[
                    "expense_total"
                ],
                "income": "Total",
                "income_amount": section_data[
                    "income_total"
                ],
                "is_subtotal": 1,
            }
        )

    # ========================================================
    # P&L CALCULATION
    # ========================================================

    if pnl_sections:

        pnl_expense_total = sum(
            flt(
                item[
                    "expense_total"
                ]
            )
            for item in pnl_sections
        )

        pnl_income_total = sum(
            flt(
                item[
                    "income_total"
                ]
            )
            for item in pnl_sections
        )

        net_profit = (
            gross_profit
            + pnl_income_total
            - pnl_expense_total
        )

        # ----------------------------------------------------
        # GROSS PROFIT
        # ----------------------------------------------------

        final_rows.append(
            {
                "expense": "",
                "expense_amount": "",
                "income": "Gross Profit",
                "income_amount": gross_profit,
                "is_gross_profit": 1,
            }
        )

        # ----------------------------------------------------
        # NET PROFIT / LOSS
        # ----------------------------------------------------

        if net_profit >= 0:

            final_rows.append(
                {
                    "expense": "",
                    "expense_amount": "",
                    "income": "Net Profit",
                    "income_amount": net_profit,
                    "is_total": 1,
                }
            )

        else:

            final_rows.append(
                {
                    "expense": "Net Loss",
                    "expense_amount": abs(
                        net_profit
                    ),
                    "income": "",
                    "income_amount": "",
                    "is_total": 1,
                }
            )

    # ========================================================
    # KPI
    # ========================================================

    if kpi_section_data:

        kpi_rows = get_kpi(
            kpi_section_data,
            gross_profit,
        )

        final_rows.append(
            {
                "expense": kpi_section_data[
                    "section"
                ],
                "expense_amount": "",
                "income": "",
                "income_amount": "",
                "is_section_header": 1,
            }
        )

        for kpi in kpi_rows:

            final_rows.append(
                {
                    "expense": kpi[
                        "label"
                    ],
                    "expense_amount": kpi[
                        "value"
                    ],
                    "income": "",
                    "income_amount": "",
                    "is_kpi": 1,
                }
            )

    return final_rows