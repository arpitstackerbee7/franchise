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


def get_data(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        return []

    incentive_slabs = get_counter_incentive_slabs()
    data = []

    # ==========================================================
    # SALES MANAGER SELECTED -> Existing Behaviour
    # ==========================================================
    if filters.get("sales_manager"):

        managers = frappe.db.sql(
            """
            SELECT
                c.account_manager AS sales_manager
            FROM `tabCustomer` c
            WHERE
                c.is_internal_customer = 1
                AND IFNULL(c.represents_company,'') != ''
                AND c.account_manager = %(sales_manager)s
            GROUP BY c.account_manager
            """,
            {
                "sales_manager": filters.sales_manager
            },
            as_dict=True,
        )

        for manager in managers:

            counters = frappe.db.sql(
                """
                SELECT
                    c.name,
                    c.customer_name,
                    c.represents_company
                FROM `tabCustomer` c
                WHERE
                    c.is_internal_customer = 1
                    AND IFNULL(c.represents_company,'') != ''
                    AND c.account_manager=%(sales_manager)s
                ORDER BY
                    c.customer_name
                """,
                {
                    "sales_manager": manager.sales_manager
                },
                as_dict=True,
            )

            companies = [
                d.represents_company
                for d in counters
                if d.represents_company
            ]

            total_sales = get_total_sales(
                companies,
                filters.from_date,
                filters.to_date,
            )

            incentive = get_incentive_percentage(
                total_sales,
                len(counters),
                incentive_slabs,
            )

            payout = (
                total_sales * incentive / 100
                if incentive
                else None
            )

            counter_details = []

            for c in counters:
                counter_details.append({
                    "name": c.name,
                    "customer_name": c.customer_name,
                    "represents_company": c.represents_company,
                })

            data.append({
                "sales_manager": manager.sales_manager,
                "sales_manager_name": frappe.db.get_value(
                    "User",
                    manager.sales_manager,
                    "full_name",
                ) or "",
                "counter_count": len(counters),
                "counter_details": frappe.as_json(counter_details),
                "total_sales": total_sales,
                "incentive_percentage": incentive,
                "total_incentive_earned": payout,
            })

        return data

    # ==========================================================
    # NO SALES MANAGER FILTER -> One Row Per Counter
    # ==========================================================

    counters = frappe.db.sql(
        """
        SELECT
            c.name,
            c.customer_name,
            c.account_manager,
            c.represents_company
        FROM `tabCustomer` c
        WHERE
            c.is_internal_customer = 1
            AND IFNULL(c.represents_company,'') != ''
        ORDER BY
            c.customer_name
        """,
        as_dict=True,
    )

    for counter in counters:

        total_sales = get_total_sales(
            [counter.represents_company],
            filters.from_date,
            filters.to_date,
        )

        incentive = get_incentive_percentage(
            total_sales,
            1,
            incentive_slabs,
        )

        payout = (
            total_sales * incentive / 100
            if incentive
            else None
        )

        counter_details = frappe.as_json([
            {
                "name": counter.name,
                "customer_name": counter.customer_name,
                "represents_company": counter.represents_company,
            }
        ])

        data.append({
            "sales_manager": counter.account_manager or "",
            "sales_manager_name": frappe.db.get_value(
                "User",
                counter.account_manager,
                "full_name",
            ) if counter.account_manager else "",
            "counter_count": 1,
            "counter_details": counter_details,
            "total_sales": total_sales,
            "incentive_percentage": incentive,
            "total_incentive_earned": payout,
        })

    return data


def get_total_sales(companies, from_date, to_date):
    result = frappe.db.sql(
        """
        SELECT
            SUM(dn.total) AS total_sales
        FROM `tabDelivery Note` dn
        WHERE
            dn.docstatus = 1
            AND dn.company IN %(companies)s
            AND dn.posting_date BETWEEN %(from_date)s AND %(to_date)s
        """,
        {
            "companies": companies,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    if not result:
        return 0

    return flt(result[0].total_sales)


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

        slabs.append({
            "idx": row.idx,
            "aggregate_sales": aggregate_sales,
            "incentive": flt(row.incentive),
        })

    slabs.sort(
        key=lambda slab: (
            slab["aggregate_sales"],
            slab["idx"],
        )
    )

    return slabs


def parse_amount(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace("₹", "")
    value = value.replace(",", "")
    value = re.sub(r"\s+", "", value)

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value,
    )

    if not numbers:
        return None

    return flt(numbers[0])


def get_incentive_percentage(
    total_sales,
    counter_count,
    incentive_slabs,
):
    if not incentive_slabs:
        return None

    matched_incentive = None

    for slab in incentive_slabs:
        aggregate_target = slab["aggregate_sales"]

        if total_sales >= aggregate_target:
            matched_incentive = slab["incentive"]
        else:
            break

    return matched_incentive