# # Copyright (c) 2026, Franchise Erp and contributors
# # For license information, please see license.txt

import frappe
from frappe.utils import cint


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)

    return columns, data, None, chart


def get_columns():
    return [
        {
            "label": "Style No.",
            "fieldname": "custom_barcode_code",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Department",
            "fieldname": "custom_department",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Month",
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Sales Qty",
            "fieldname": "sales_qty",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": "Stock Qty",
            "fieldname": "stock_qty",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120,
        },
    ]


def get_data(filters):
    # frappe.msgprint(str(filters))
    conditions = ["si.docstatus = 1"]
    params = {}

    # Date Filter
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
        params["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    # Company Filter
    if filters.get("company"):
        conditions.append("si.company = %(company)s")
        params["company"] = filters.get("company")

    # Month Filter ONLY when date filter not selected
    if (
        filters.get("month")
        and not filters.get("from_date")
        and not filters.get("to_date")
    ):
        conditions.append("MONTH(si.posting_date) = %(month)s")
        params["month"] = cint(filters.get("month"))

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(
        f"""
        SELECT

            i.image,
            i.custom_barcode_code,
            i.custom_departments AS custom_department,

            MONTH(si.posting_date) AS month,

            SUM(sii.qty) AS sales_qty,

            IFNULL(
                (
                    SELECT actual_qty
                    FROM `tabBin`
                    WHERE item_code = sii.item_code
                    LIMIT 1
                ),
                0
            ) AS stock_qty,

            CASE
                WHEN
                    IFNULL(
                        (
                            SELECT actual_qty
                            FROM `tabBin`
                            WHERE item_code = sii.item_code
                            LIMIT 1
                        ),
                        0
                    ) > SUM(sii.qty)
                THEN 'In Stock'

                ELSE 'Low Stock'

            END AS status

        FROM `tabSales Invoice Item` sii

        INNER JOIN `tabSales Invoice` si
            ON sii.parent = si.name

        LEFT JOIN `tabItem` i
            ON i.item_code = sii.item_code

        WHERE {where_clause}

        GROUP BY
            sii.item_code,
            MONTH(si.posting_date)

        ORDER BY
            sales_qty DESC
        """,
        params,
        as_dict=True,
    )

    for row in data:

        if row.get("image"):

            img = row.image

            if not img.startswith("/"):
                img = "/" + img

            row["image_url"] = img

        else:
            row["image_url"] = ""

        dept = row.get("custom_department") or ""

        row["custom_department"] = (
            dept.split("-")[-1].strip() if dept else ""
        )

    return data


def get_chart_data(data):

    return {
        "data": {
            "labels": [
                d.get("custom_barcode_code") or "No Style"
                for d in data
            ],
            "datasets": [
                {
                    "name": "Sales",
                    "values": [
                        float(d.get("sales_qty") or 0)
                        for d in data
                    ],
                },
                {
                    "name": "Stock",
                    "values": [
                        float(d.get("stock_qty") or 0)
                        for d in data
                    ],
                },
            ],
        },
        "type": "bar",
    }