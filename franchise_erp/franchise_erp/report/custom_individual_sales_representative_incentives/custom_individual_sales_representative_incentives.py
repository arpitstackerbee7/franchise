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
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    company_condition = ""
    salesman_condition = ""
    join_type = "LEFT JOIN"

    # Counter Filter
    if filters.get("counter"):
        represents_company = frappe.db.get_value(
            "Customer",
            filters.counter,
            "represents_company",
        )

        if not represents_company:
            return []

        query_filters["company"] = represents_company

        company_condition = """
            AND dn.company = %(company)s
        """

        # Counter selected => only matching employees
        join_type = "INNER JOIN"

    # Sales Man Filter
    if filters.get("sales_man"):
        query_filters["sales_man"] = filters.sales_man

        salesman_condition = """
            AND e.user_id = %(sales_man)s
        """

    rows = frappe.db.sql(
        f"""
        SELECT
            e.user_id AS user,
            e.name AS employee_id,
            e.employee_name,
            COALESCE(SUM(dn.total), 0) AS monthly_sales

        FROM `tabEmployee` e

        {join_type} `tabDelivery Note` dn
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

    incentive_slabs = get_incentive_slabs()

    data = []

    for row in rows:
        monthly_sales = flt(row.monthly_sales)

        incentive_percentage, slab_model = get_incentive_slab(
            monthly_sales,
            incentive_slabs,
        )

        potential_payout = (
            monthly_sales * incentive_percentage / 100
            if incentive_percentage is not None
            else None
        )

        data.append({
            "user": row.user,
            "employee_name": row.employee_name,
            "employee_id": row.employee_id,
            "monthly_sales": monthly_sales,
            "incentive_percentage": incentive_percentage,
            "potential_payout": potential_payout,
            "slab_model": slab_model,
        })

    return data

def get_incentive_slabs():
    child_table_doctype = frappe.db.get_value(
        "DocField",
        {
            "parent": "TZU Setting",
            "fieldname": "individual_sales_representative_incentives",
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

        slabs.append({
            "idx": row.idx,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "incentive": flt(row.incentive),
            "slab_model": row.slab_model or "",
        })

    slabs.sort(
        key=lambda slab: (
            slab["min_amount"],
            slab["idx"],
        )
    )

    return slabs


def parse_sales_range(range_value):
    if not range_value:
        return None

    value = str(range_value).strip().lower()

    value = value.replace("₹", "")
    value = value.replace(",", "")
    value = re.sub(r"\s+", " ", value).strip()

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

    if len(amounts) >= 2:
        min_amount = amounts[0]
        max_amount = amounts[1]

        if min_amount > max_amount:
            min_amount, max_amount = (
                max_amount,
                min_amount,
            )

        return min_amount, max_amount

    return amounts[0], amounts[0]


def get_incentive_slab(monthly_sales, slabs):
    if not slabs:
        return None, ""

    for index, slab in enumerate(slabs):
        min_amount = slab["min_amount"]
        max_amount = slab["max_amount"]

        # Example: 2,80,000 & above
        if max_amount is None:
            if monthly_sales > min_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

            continue

        # First slab:
        # 1,80,000 to 2,30,000
        if index == 0:
            if min_amount <= monthly_sales <= max_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

        # Other slabs:
        # Previous slab owns the overlapping boundary.
        # So 2,30,000 remains in Silver.
        else:
            if min_amount < monthly_sales <= max_amount:
                return (
                    slab["incentive"],
                    slab["slab_model"],
                )

    return None, ""