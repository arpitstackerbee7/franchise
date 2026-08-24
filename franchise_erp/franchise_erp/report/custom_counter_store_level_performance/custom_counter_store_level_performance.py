# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# =========================================================
# COLUMNS
# =========================================================

def get_columns():
    return [
        {
            "label": _("Sales Manager"),
            "fieldname": "sales_manager",
            "fieldtype": "Link",
            "options": "User",
            "width": 200,
        },
        {
            "label": _("Sales Manager Name"),
            "fieldname": "sales_manager_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("No. of Counters"),
            "fieldname": "counter_count",
            "fieldtype": "Int",
            "width": 130,
        },
        {
            "label": _("Counter Details"),
            "fieldname": "counter_details",
            "fieldtype": "Data",
            "hidden": 1,
        },
        {
            "label": _("Total Sales"),
            "fieldname": "total_sales",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Incentive %"),
            "fieldname": "incentive_percentage",
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "label": _("Total Incentive Earned"),
            "fieldname": "total_incentive_earned",
            "fieldtype": "Currency",
            "width": 190,
        },
    ]


# =========================================================
# MAIN DATA
# =========================================================
def get_data(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        return []

    incentive_slabs = get_counter_incentive_slabs()

    conditions = [
        "IFNULL(TRIM(c.account_manager), '') != ''"
    ]

    values = {}

    # =========================================================
    # SALES MANAGER FILTER
    # =========================================================

    if filters.get("sales_manager"):
        conditions.append(
            "TRIM(c.account_manager) = %(sales_manager)s"
        )

        values["sales_manager"] = (
            filters.sales_manager.strip()
        )

    # =========================================================
    # FETCH COUNTERS
    # =========================================================

    counters = frappe.db.sql(
        f"""
        SELECT
            c.name,
            c.customer_name,
            TRIM(c.account_manager) AS account_manager,
            c.represents_company
        FROM `tabCustomer` c
        WHERE
            {" AND ".join(conditions)}
        ORDER BY
            c.account_manager,
            c.customer_name
        """,
        values,
        as_dict=True,
    )

    # =========================================================
    # GROUP COUNTERS BY SALES MANAGER
    # =========================================================

    manager_groups = {}

    for counter in counters:

        manager = (
            counter.account_manager or ""
        ).strip()

        if not manager:
            continue

        if manager not in manager_groups:
            manager_groups[manager] = []

        manager_groups[manager].append(
            {
                "name": counter.name,
                "customer_name": counter.customer_name,
                "represents_company": (
                    counter.represents_company
                ),
            }
        )

    data = []

    # =========================================================
    # ONE ROW PER SALES MANAGER
    # =========================================================

    for manager, manager_counters in manager_groups.items():

        counter_count = len(manager_counters)

        # Assigned counters ki represents_company values
        companies = list(
            dict.fromkeys(
                counter["represents_company"].strip()
                for counter in manager_counters
                if counter.get("represents_company")
                and counter["represents_company"].strip()
            )
        )

        # Delivery Note company ke basis par Total Sales
        total_sales = get_total_sales(
            companies,
            filters.from_date,
            filters.to_date,
        )

        incentive = get_incentive_percentage(
            total_sales,
            incentive_slabs,
        )

        payout = calculate_payout(
            total_sales,
            incentive,
        )

        sales_manager_name = (
            frappe.db.get_value(
                "User",
                manager,
                "full_name",
            )
            or ""
        )

        data.append(
            {
                "sales_manager": manager,
                "sales_manager_name": sales_manager_name,
                "counter_count": counter_count,
                "counter_details": frappe.as_json(
                    manager_counters
                ),
                "total_sales": total_sales,
                "incentive_percentage": incentive,
                "total_incentive_earned": payout,
            }
        )
    return data

# =========================================================
# GET SALES BY OWNER
# =========================================================

def get_sales_by_owner(
    owner,
    from_date,
    to_date,
):
    """
    Calculate total submitted Delivery Note sales
    for a specific user/owner.
    """

    if not owner:
        return 0

    result = frappe.db.sql(
        """
        SELECT
            COALESCE(
                SUM(dn.net_total),
                0
            ) AS total_sales

        FROM `tabDelivery Note` dn

        WHERE
            dn.owner = %(owner)s
            AND dn.docstatus = 1
            AND dn.posting_date >= %(from_date)s
            AND dn.posting_date <= %(to_date)s
        """,
        {
            "owner": owner,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    if not result:
        return 0

    return flt(
        result[0].total_sales
    )


# =========================================================
# GET TOTAL SALES
# =========================================================
# =========================================================
# GET TOTAL SALES
# =========================================================
def get_total_sales(
    companies,
    from_date,
    to_date,
):
    """
    Calculate Total Sales from Delivery Notes.

    Logic:

    Sales Manager
        ↓
    Assigned Counter
        ↓
    Counter.represents_company
        ↓
    Delivery Note.company
        ↓
    SUM(Delivery Note.net_total)
    """

    if not companies:
        return 0

    if isinstance(companies, str):
        companies = [companies]

    companies = list(
        dict.fromkeys(
            company.strip()
            for company in companies
            if company and company.strip()
        )
    )

    if not companies:
        return 0

    result = frappe.db.sql(
        """
        SELECT
            COALESCE(
                SUM(dn.net_total),
                0
            ) AS total_sales

        FROM `tabDelivery Note` dn

        WHERE
            dn.docstatus = 1

            AND dn.company IN %(companies)s

            AND dn.posting_date BETWEEN
                %(from_date)s
                AND %(to_date)s
        """,
        {
            "companies": tuple(companies),
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    if not result:
        return 0

    return flt(
        result[0].total_sales
    )

# =========================================================
# CALCULATE PAYOUT
# =========================================================

def calculate_payout(
    total_sales,
    incentive,
):
    """
    Calculate incentive payout.

    Example:

        Sales = 40,546
        Incentive = 0.1%

        Payout = 40.55
    """

    if incentive is None:
        return 0

    return (
        flt(total_sales)
        * flt(incentive)
        / 100
    )


# =========================================================
# GET INCENTIVE SLABS
# =========================================================

def get_counter_incentive_slabs():

    child_table_doctype = frappe.db.get_value(
        "DocField",
        {
            "parent": "TZU Setting",
            "fieldname": "counter_store_level_performance",
            "fieldtype": "Table",
        },
        "options",
    )

    if not child_table_doctype:
        return []

    rows = frappe.get_all(
        child_table_doctype,

        filters={
            "parent": "TZU Setting",
            "parenttype": "TZU Setting",
            "parentfield": "counter_store_level_performance",
        },

        fields=[
            "idx",
            "aggregate_sales",
            "incentive",
        ],

        order_by="idx asc",
    )

    slabs = []

    for row in rows:

        aggregate_sales = parse_amount(
            row.aggregate_sales
        )

        if aggregate_sales is None:
            continue

        slabs.append(
            {
                "idx": row.idx,
                "aggregate_sales": aggregate_sales,
                "incentive": flt(
                    row.incentive
                ),
            }
        )

    # -----------------------------------------------------
    # Sort by aggregate sales
    # -----------------------------------------------------

    slabs.sort(
        key=lambda slab: (
            slab["aggregate_sales"],
            slab["idx"],
        )
    )

    return slabs


# =========================================================
# PARSE AMOUNT
# =========================================================

def parse_amount(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # Remove currency symbol
    value = value.replace(
        "₹",
        "",
    )

    # Remove commas
    value = value.replace(
        ",",
        "",
    )

    # Remove spaces
    value = re.sub(
        r"\s+",
        "",
        value,
    )

    # Extract numbers
    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value,
    )

    if not numbers:
        return None

    return flt(
        numbers[0]
    )


# =========================================================
# GET INCENTIVE PERCENTAGE
# =========================================================

def get_incentive_percentage(
    total_sales,
    incentive_slabs,
):
    """
    Find the highest applicable incentive slab.

    Example:

        0 - 100000      -> 0%
        100000 - 200000 -> 0.5%
        200000+         -> 1%

    If sales = 250000
    incentive = 1%
    """

    if not incentive_slabs:
        return None

    matched_incentive = None

    for slab in incentive_slabs:

        aggregate_target = (
            slab["aggregate_sales"]
        )

        if total_sales >= aggregate_target:

            matched_incentive = (
                slab["incentive"]
            )

        else:
            break

    return matched_incentive