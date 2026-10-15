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


def get_columns():
    return [
        {
            "label": _("User"),
            "fieldname": "user",
            "fieldtype": "Link",
            "options": "User",
            "width": 200,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 140,
        },
        {
            "label": _("Monthly Sales Range"),
            "fieldname": "monthly_sales",
            "fieldtype": "Currency",
            "width": 180,
        },
        {
            "label": _("Incentive %"),
            "fieldname": "incentive_percentage",
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "label": _("Potential Payout"),
            "fieldname": "potential_payout",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Slab Model"),
            "fieldname": "slab_model",
            "fieldtype": "Data",
            "width": 140,
        },
    ]


def get_data(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        return []

    query_filters = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    }

    company_condition = ""
    salesman_condition = ""

    # ---------------------------------------------------------
    # Counter Filter
    # ---------------------------------------------------------
    if filters.get("counter"):
        represents_company = frappe.db.get_value(
            "Customer",
            filters.get("counter"),
            "represents_company",
        )

        if not represents_company:
            return []

        query_filters["company"] = represents_company

        company_condition = """
            AND dn.company = %(company)s
        """

    # ---------------------------------------------------------
    # Sales Man Filter
    # ---------------------------------------------------------
    if filters.get("sales_man"):
        query_filters["sales_man"] = filters.get("sales_man")

        salesman_condition = """
            AND e.user_id = %(sales_man)s
        """

    # ---------------------------------------------------------
    # Get Employee-wise Delivery Note Sales
    # ---------------------------------------------------------
    rows = frappe.db.sql(
        f"""
        SELECT
            e.user_id AS user,
            e.name AS employee_id,
            e.employee_name,
            COALESCE(SUM(dn.net_total), 0) AS monthly_sales

        FROM `tabEmployee` e

        INNER JOIN `tabDelivery Note` dn
            ON dn.owner = e.user_id
            AND dn.docstatus = 1
            AND dn.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {company_condition}

        WHERE
            IFNULL(e.user_id, '') != ''
            {salesman_condition}

        GROUP BY
            e.user_id,
            e.name,
            e.employee_name

        ORDER BY
            e.employee_name
        """,
        query_filters,
        as_dict=True,
    )

    # ---------------------------------------------------------
    # Get Incentive Slabs
    # ---------------------------------------------------------
    incentive_slabs = get_incentive_slabs()

    if not incentive_slabs:
        return []

    data = []

    # ---------------------------------------------------------
    # Match Employee Sales With Incentive Slab
    # ---------------------------------------------------------
    for row in rows:
        monthly_sales = flt(row.monthly_sales)

        incentive_percentage, slab_model = get_incentive_slab(
            monthly_sales,
            incentive_slabs,
        )

        # Only show users who have an incentive slab
        if incentive_percentage is None:
            continue

        potential_payout = (
            monthly_sales * incentive_percentage / 100
        )

        data.append(
            {
                "user": row.user,
                "employee_name": row.employee_name,
                "employee_id": row.employee_id,
                "monthly_sales": monthly_sales,
                "incentive_percentage": incentive_percentage,
                "potential_payout": potential_payout,
                "slab_model": slab_model,
            }
        )

    return data


def get_incentive_slabs():
    """
    Get Individual Sales Representative Incentive slabs
    from TZU Setting child table.
    """

    meta = frappe.get_meta("TZU Setting")

    field = meta.get_field(
        "individual_sales_representative_incentives"
    )

    if not field or not field.options:
        return []

    child_table_doctype = field.options

    rows = frappe.get_all(
        child_table_doctype,
        filters={
            "parent": "TZU Setting",
            "parenttype": "TZU Setting",
            "parentfield": "individual_sales_representative_incentives",
        },
        fields=[
            "idx",
            "monthly_sales_range",
            "incentive",
            "slab_model",
        ],
        order_by="idx asc",
    )

    slabs = []

    for row in rows:
        parsed_range = parse_sales_range(
            row.monthly_sales_range
        )

        if not parsed_range:
            continue

        min_amount, max_amount = parsed_range

        slabs.append(
            {
                "idx": row.idx,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "incentive": flt(row.incentive),
                "slab_model": row.slab_model or "",
            }
        )

    slabs.sort(
        key=lambda slab: (
            slab["min_amount"],
            slab["idx"],
        )
    )

    return slabs


def parse_sales_range(range_value):
    """
    Supported formats:

    200
        -> 0 to 200

    0 - 200
        -> 0 to 200

    200 - 500
        -> 200 to 500

    1,80,000 to 2,30,000
        -> 180000 to 230000

    2,80,000 & above
        -> 280000 and above

    280000+
        -> 280000 and above
    """

    if range_value is None:
        return None

    value = str(range_value).strip().lower()

    if not value:
        return None

    # Remove currency symbol
    value = value.replace("₹", "")

    # Remove commas
    value = value.replace(",", "")

    # Normalize spaces
    value = re.sub(r"\s+", " ", value).strip()

    # Extract all numbers
    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value,
    )

    if not numbers:
        return None

    amounts = [
        flt(number)
        for number in numbers
    ]

    # ---------------------------------------------------------
    # Above / Open-ended range
    # ---------------------------------------------------------
    is_above_range = any(
        keyword in value
        for keyword in [
            "above",
            "onwards",
            "onward",
            "or more",
            "and more",
            "+",
        ]
    )

    if is_above_range:
        return amounts[0], None

    # ---------------------------------------------------------
    # Normal range with two values
    # Example: 200 - 500
    # ---------------------------------------------------------
    if len(amounts) >= 2:
        min_amount = amounts[0]
        max_amount = amounts[1]

        if min_amount > max_amount:
            min_amount, max_amount = (
                max_amount,
                min_amount,
            )

        return min_amount, max_amount

    # ---------------------------------------------------------
    # Single value
    # Example: 200
    #
    # Requirement:
    # 200 means 0 to 200
    # ---------------------------------------------------------
    return 0, amounts[0]


def get_incentive_slab(monthly_sales, slabs):
    """
    Find matching incentive slab.

    Examples:

    200
        -> 0 to 200

    200 - 500
        -> 200 to 500

    500 - 1000
        -> 500 to 1000

    1000 & above
        -> 1000 and above

    Boundary handling:

    Previous slab owns the common boundary.
    """

    if not slabs:
        return None, ""

    for index, slab in enumerate(slabs):
        min_amount = slab["min_amount"]
        max_amount = slab["max_amount"]

        # -----------------------------------------------------
        # Open-ended slab
        # Example: 1000 & above
        # -----------------------------------------------------
        if max_amount is None:
            if monthly_sales > min_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

            # If this is the first slab, include boundary
            if index == 0 and monthly_sales >= min_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

            continue

        # -----------------------------------------------------
        # First slab
        # Example: 0 to 200
        # -----------------------------------------------------
        if index == 0:
            if min_amount <= monthly_sales <= max_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

        # -----------------------------------------------------
        # Other slabs
        # Previous slab owns common boundary
        # -----------------------------------------------------
        else:
            if min_amount < monthly_sales <= max_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

    return None, ""