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
    Read Financial Statement Account Mapping
    from TZU Setting.

    Each mapping contains:
        - statement_section
        - statement_type
        - type
        - account
        - balance_type
        - enabled
    """

    settings = frappe.get_single("TZU Setting")

    mappings = (
        settings.get(
            "financial_statement_account_mapping"
        )
        or []
    )

    result = []

    for row in mappings:

        # ----------------------------------------------------
        # Disabled
        # ----------------------------------------------------

        if not row.get("enabled"):
            continue

        # ----------------------------------------------------
        # Statement Type
        # ----------------------------------------------------

        statement_type = str(
            row.get("statement_type")
            or ""
        ).strip()

        if not statement_type:
            continue

        # ----------------------------------------------------
        # Account
        # ----------------------------------------------------

        account = row.get("account")

        if not account:
            continue

        # ----------------------------------------------------
        # Section
        # ----------------------------------------------------

        if section:

            row_section = str(
                row.get("statement_section")
                or ""
            ).strip()

            if row_section != section:
                continue

        result.append(row)

    return result


# ============================================================
# STATEMENT SIDE
# ============================================================

def get_statement_side(mapping):
    """
    Expense / Income is taken from the mapping's
    Type field.

    Example:

        Statement Type = Sales
        Type           = Income

    or:

        Statement Type = Employee Cost
        Type           = Expense

    IMPORTANT:
    statement_type is only the display label.
    """

    statement_side = str(
        mapping.get("type")
        or mapping.get("statement_type_type")
        or ""
    ).strip().lower()

    if statement_side == "income":
        return "income"

    if statement_side == "expense":
        return "expense"

    # --------------------------------------------------------
    # Unknown type
    # --------------------------------------------------------

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
        mapping.get("statement_type")
        or ""
    ).strip()


# ============================================================
# CONFIGURED ACCOUNTS
# ============================================================

def get_configured_account_names(mappings=None):
    """
    Return configured Account names.
    """

    if mappings is None:
        mappings = get_statement_mappings()

    accounts = set()

    for mapping in mappings:

        account = mapping.get("account")

        if account:
            accounts.add(account)

    return accounts


# ============================================================
# CHECK ACCOUNT DESCENDANT
# ============================================================

def is_account_descendant(
    child_account,
    parent_account,
    account_cache=None,
):
    """
    Check whether child_account is a descendant of
    parent_account using ERPNext parent_account hierarchy.

    Same account is NOT considered descendant.
    """

    if not child_account or not parent_account:
        return False

    if child_account == parent_account:
        return False

    current = child_account

    visited = set()

    while current:

        if current in visited:
            break

        visited.add(current)

        if account_cache and current in account_cache:

            current_row = account_cache[current]

            current = (
                current_row.get("parent_account")
                or ""
            )

        else:

            current = frappe.db.get_value(
                "Account",
                current,
                "parent_account",
            )

        if current == parent_account:
            return True

    return False


# ============================================================
# TOP LEVEL MAPPINGS
# ============================================================

def get_top_level_mappings(mappings):
    """
    Determine top-level Statement Type mappings.

    A mapping is top-level when its Account is NOT a child
    of another configured mapping Account on the same side.

    IMPORTANT:

    Same Account can be used multiple times.

    Example:

        Opening Stock -> Stock Expenses
        Purchases     -> Stock Expenses

    Both remain top-level because they are two different
    Statement Type mappings.
    """

    if not mappings:
        return []

    # --------------------------------------------------------
    # Account names
    # --------------------------------------------------------

    account_names = {
        row.get("account")
        for row in mappings
        if row.get("account")
    }

    # --------------------------------------------------------
    # Cache account parents
    # --------------------------------------------------------

    account_cache = {}

    for account_name in account_names:

        account = frappe.db.get_value(
            "Account",
            account_name,
            [
                "name",
                "parent_account",
                "lft",
                "rgt",
                "is_group",
            ],
            as_dict=True,
        )

        if account:
            account_cache[account_name] = account

    # --------------------------------------------------------
    # Find top-level
    # --------------------------------------------------------

    result = []

    for index, mapping in enumerate(mappings):

        account = mapping.get("account")

        if not account:
            continue

        side = get_statement_side(mapping)

        if not side:
            continue

        is_child = False

        for other_index, other_mapping in enumerate(mappings):

            if index == other_index:
                continue

            other_account = other_mapping.get(
                "account"
            )

            if not other_account:
                continue

            other_side = get_statement_side(
                other_mapping
            )

            if other_side != side:
                continue

            # Same account must remain separate.
            if other_account == account:
                continue

            if is_account_descendant(
                account,
                other_account,
                account_cache,
            ):
                is_child = True
                break

        if not is_child:
            result.append(mapping)

    return result


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

    If from_date is None:
        Balance is calculated from beginning of ledger
        up to to_date.

    This is required for Opening Balance.

    For Opening Stock:
        Period Closing Voucher entries are excluded.
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

    # --------------------------------------------------------
    # Conditions
    # --------------------------------------------------------

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
    # DATE CONDITION
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
    # EXCLUDE PERIOD CLOSING
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

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Root Type
    # --------------------------------------------------------

    root_type = account_details.root_type

    if root_type in (
        "Income",
        "Liability",
        "Equity",
    ):
        return credit - debit

    return debit - credit


# ============================================================
# DIRECT ACCOUNT BALANCE
# ============================================================

def get_direct_account_balance(
    account,
    company,
    from_date,
    to_date,
    cost_center=None,
    project=None,
    finance_book=None,
):
    """
    Balance for only the selected Account.
    """

    if not account:
        return 0

    root_type = frappe.db.get_value(
        "Account",
        account,
        "root_type",
    )

    if not root_type:
        return 0

    conditions = [
        "gle.company = %(company)s",
        "gle.account = %(account)s",
        "gle.is_cancelled = 0",
    ]

    values = {
        "company": company,
        "account": account,
        "from_date": from_date,
        "to_date": to_date,
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

def get_mapping_value(mapping, filters):
    """
    Get value according to configured Balance Type.

    Opening Balance:
        from_date - 1 day

    Opening Stock:
        Same opening calculation but Period Closing Voucher
        entries are excluded.

    Period Balance:
        from_date -> to_date

    Closing Balance:
        beginning -> to_date
    """

    account = mapping.get("account")

    if not account:
        return 0

    balance_type = str(
        mapping.get("balance_type")
        or ""
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
        # SPECIAL OPENING STOCK LOGIC
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
        # NORMAL OPENING BALANCE
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
# MAPPING TREE HELPERS
# ============================================================

def get_nearest_mapping_parent(
    mapping,
    mappings,
):
    """
    Find nearest configured Statement Type parent
    based on ERPNext Account hierarchy.

    Example:

        Employee Cost
            Staff Welfare

    Mapping:

        Employee Cost -> Employee Cost - TZUPL
        Employees Welfare -> Staff Welfare - TZUPL

    Result:

        Employee Cost
            Employees Welfare
    """

    account = mapping.get(
        "account"
    )

    if not account:
        return None

    side = get_statement_side(
        mapping
    )

    if not side:
        return None

    candidates = []

    for other in mappings:

        if other is mapping:
            continue

        other_account = other.get(
            "account"
        )

        if not other_account:
            continue

        if other_account == account:
            continue

        other_side = get_statement_side(
            other
        )

        if other_side != side:
            continue

        if is_account_descendant(
            account,
            other_account,
        ):

            candidates.append(
                other
            )

    if not candidates:
        return None

    # --------------------------------------------------------
    # Find nearest parent
    # --------------------------------------------------------

    nearest = None
    nearest_distance = None

    for candidate in candidates:

        candidate_account = candidate.get(
            "account"
        )

        distance = 0
        current = account
        visited = set()

        while current:

            if current in visited:
                break

            visited.add(current)

            if current == candidate_account:
                break

            current = frappe.db.get_value(
                "Account",
                current,
                "parent_account",
            )

            distance += 1

        if current == candidate_account:

            if (
                nearest_distance is None
                or distance < nearest_distance
            ):
                nearest = candidate
                nearest_distance = distance

    return nearest


# ============================================================
# STATEMENT TREE
# ============================================================

def get_statement_tree(
    root_mapping,
    mappings,
):
    """
    Build Statement Type hierarchy.

    Account names are NEVER returned as display labels.

    Example:

        Employee Cost
            Employees Welfare

    Instead of:

        Employee Cost
            Employee Cost - TZUPL
                Staff Welfare - TZUPL
    """

    root_account = root_mapping.get(
        "account"
    )

    root_side = get_statement_side(
        root_mapping
    )

    if not root_account or not root_side:
        return []

    # --------------------------------------------------------
    # Only same side
    # --------------------------------------------------------

    side_mappings = [
        row
        for row in mappings
        if get_statement_side(row)
        == root_side
    ]

    # --------------------------------------------------------
    # Mapping identity
    # --------------------------------------------------------

    def mapping_key(mapping):
        return (
            id(mapping)
        )

    # --------------------------------------------------------
    # Children
    # --------------------------------------------------------

    children_map = {}

    for mapping in side_mappings:

        if mapping is root_mapping:
            continue

        parent = get_nearest_mapping_parent(
            mapping,
            side_mappings,
        )

        if parent:

            children_map.setdefault(
                mapping_key(parent),
                [],
            ).append(
                mapping
            )

    # --------------------------------------------------------
    # Sort children according to Account lft
    # --------------------------------------------------------

    for parent_key in children_map:

        children_map[parent_key].sort(
            key=lambda row: (
                frappe.db.get_value(
                    "Account",
                    row.get("account"),
                    "lft",
                )
                or 0
            )
        )

    return children_map


# ============================================================
# BUILD STATEMENT ACCOUNT ROWS
# ============================================================

def build_statement_account_rows(
    mapping,
    filters,
    from_date,
    to_date,
    section,
    section_mappings=None,
):
    """
    Build Statement Type rows.

    IMPORTANT:

    We DO NOT show Account master names.

    Example:

        Employee Cost
            Employees Welfare

    not:

        Employee Cost
            Employee Cost - TZUPL
                Staff Welfare - TZUPL
    """

    statement_type = get_statement_type(
        mapping
    )

    account = mapping.get(
        "account"
    )

    if not statement_type or not account:
        return []

    # --------------------------------------------------------
    # Unique tree ID
    # --------------------------------------------------------

    statement_tree_id = (
        frappe.scrub(section)
        + "__"
        + frappe.scrub(
            get_statement_side(mapping)
            or "unknown"
        )
        + "__"
        + frappe.scrub(
            statement_type
        )
        + "__"
        + frappe.scrub(
            account
        )
    )

    # --------------------------------------------------------
    # Mapping value
    # --------------------------------------------------------

    mapping_value = get_mapping_value(
        mapping,
        filters,
    )

    # --------------------------------------------------------
    # Children
    # --------------------------------------------------------

    children_map = get_statement_tree(
        mapping,
        section_mappings
        or [],
    )

    # --------------------------------------------------------
    # Rows
    # --------------------------------------------------------

    rows = []

    def add_mapping(
        current_mapping,
        indent,
        parent_tree_id,
    ):
        current_statement_type = get_statement_type(
            current_mapping
        )

        current_account = current_mapping.get(
            "account"
        )

        if not current_statement_type:
            return

        current_tree_id = (
            frappe.scrub(section)
            + "__"
            + frappe.scrub(
                get_statement_side(
                    current_mapping
                )
                or "unknown"
            )
            + "__"
            + frappe.scrub(
                current_statement_type
            )
            + "__"
            + frappe.scrub(
                current_account
                or "root"
            )
        )

        children = children_map.get(
            id(current_mapping),
            [],
        )

        value = get_mapping_value(
            current_mapping,
            filters,
        )

        rows.append(
            {
                # ------------------------------------------------
                # DISPLAY LABEL
                # ------------------------------------------------
                "label": current_statement_type,

                # ------------------------------------------------
                # VALUE
                # ------------------------------------------------
                "value": value,

                # ------------------------------------------------
                # ACCOUNT ONLY INTERNAL
                # ------------------------------------------------
                "account": current_account,

                "parent_account": "",

                # ------------------------------------------------
                # TREE
                # ------------------------------------------------
                "indent": indent,

                "is_statement_type": 1,

                "has_children": (
                    1
                    if children
                    else 0
                ),

                "is_tree_node": 1,

                "is_leaf": (
                    0
                    if children
                    else 1
                ),

                "tree_id": current_tree_id,

                "tree_parent": parent_tree_id,
            }
        )

        for child in children:

            add_mapping(
                child,
                indent + 1,
                current_tree_id,
            )

    # --------------------------------------------------------
    # Root
    # --------------------------------------------------------

    add_mapping(
        mapping,
        0,
        "",
    )

    return rows


# ============================================================
# BUILD SIDE-BY-SIDE ROWS
# ============================================================

def build_rows(
    expense_rows,
    income_rows,
):
    """
    Put Expense and Income side by side.
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
        # Expense Metadata
        # ----------------------------------------------------

        if expense:

            data.update(
                {
                    "expense_account": expense.get(
                        "account",
                        "",
                    ),

                    "expense_parent_account": expense.get(
                        "parent_account",
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
        # Income Metadata
        # ----------------------------------------------------

        if income:

            data.update(
                {
                    "income_account": income.get(
                        "account",
                        "",
                    ),

                    "income_parent_account": income.get(
                        "parent_account",
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
# SECTION DATA
# ============================================================

def get_section_data(
    section,
    filters,
):
    """
    Prepare Expense / Income rows for one section.
    """

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
    # Top-level mappings
    # --------------------------------------------------------

    top_level_mappings = get_top_level_mappings(
        mappings
    )

    expense_rows = []
    income_rows = []

    # --------------------------------------------------------
    # Build trees
    # --------------------------------------------------------

    for mapping in top_level_mappings:

        side = get_statement_side(
            mapping
        )

        if not side:
            continue

        mapping_rows = build_statement_account_rows(
            mapping=mapping,
            filters=filters,
            from_date=filters.get(
                "from_date"
            ),
            to_date=filters.get(
                "to_date"
            ),
            section=section,
            section_mappings=mappings,
        )

        if side == "income":

            income_rows.extend(
                mapping_rows
            )

        elif side == "expense":

            expense_rows.extend(
                mapping_rows
            )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Since every visible row is now a Statement Type,
    # totals must NOT sum parent + child.
    #
    # We sum only top-level Statement Type values.
    # --------------------------------------------------------

    expense_total = 0
    income_total = 0

    for mapping in top_level_mappings:

        side = get_statement_side(
            mapping
        )

        if not side:
            continue

        value = get_mapping_value(
            mapping,
            filters,
        )

        if side == "expense":
            expense_total += flt(value)

        elif side == "income":
            income_total += flt(value)

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
    """
    Return unique enabled Statement Sections
    in TZU Setting order.
    """

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
    """
    Calculate KPI rows.
    """

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
        (gross_profit / sales)
        * 100
        if sales
        else 0
    )

    # --------------------------------------------------------
    # Operating Expense Ratio
    # --------------------------------------------------------

    operating_expense_ratio = (
        (operating_expenses / sales)
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
    """
    Final report data.
    """

    sections = get_statement_sections()

    if not sections:
        return []

    all_section_data = []

    gross_profit = 0
    trading_found = False

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

            trading_found = True

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

            side_rows = build_rows(
                section_data[
                    "expense_rows"
                ],
                section_data[
                    "income_rows"
                ],
            )

            final_rows.extend(
                side_rows
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

        side_rows = build_rows(
            section_data[
                "expense_rows"
            ],
            section_data[
                "income_rows"
            ],
        )

        final_rows.extend(
            side_rows
        )

        # ----------------------------------------------------
        # SECTION SUBTOTAL
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

        # ----------------------------------------------------
        # KPI HEADER
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # KPI ROWS
        # ----------------------------------------------------

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