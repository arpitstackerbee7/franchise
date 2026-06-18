

import frappe
from frappe.utils import getdate


def execute(filters=None):

    filters = filters or {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    view_type = filters.get("view_type") or "qty"

    company = filters.get("company")

    if not from_date or not to_date:
        return [], [], None, empty_chart()

    columns = get_columns(view_type)

    data = get_data(
        from_date,
        to_date,
        company,
        view_type
    )

    chart = get_chart_data(
        data,
        view_type
    )

    return columns, data, None, chart


def get_columns(view_type):

    value_label = "Quantity" if view_type == "qty" else "Amount"

    return [

        {
            "label": "Month",
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": value_label,
            "fieldname": "value",
            "fieldtype": "Float",
            "width": 180
        }

    ]


def get_data(from_date, to_date, company, view_type):

    conditions = [
        "docstatus = 1",
        "posting_date BETWEEN %(from_date)s AND %(to_date)s"
    ]

    values = {
        "from_date": from_date,
        "to_date": to_date
    }

    if company:
        conditions.append("company = %(company)s")
        values["company"] = company

    if view_type == "qty":
        value_field = "SUM(total_qty)"
    else:
        value_field = "SUM(grand_total)"

    data = frappe.db.sql(f"""

        SELECT

            DATE_FORMAT(posting_date, '%%b') AS month,

            {value_field} AS value

        FROM `tabSales Invoice`

        WHERE {" AND ".join(conditions)}

        GROUP BY
            YEAR(posting_date),
            MONTH(posting_date)

        ORDER BY
            YEAR(posting_date),
            MONTH(posting_date)

    """, values, as_dict=True)

    return data


def get_chart_data(data, view_type):

    label = "Quantity" if view_type == "qty" else "Amount"

    values = []

    for d in data:
        values.append(
            float(d.get("value") or 0)
        )

    return {
        "data": {
            "labels": [
                d.get("month")
                for d in data
            ],

            "datasets": [
                {
                    "name": label,
                    "values": values
                }
            ]
        },

        "type": "bar"
    }


def empty_chart():

    return {
        "data": {
            "labels": [],
            "datasets": []
        },
        "type": "bar"
    }