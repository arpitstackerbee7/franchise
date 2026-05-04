# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)

    return columns, data, None, chart


# ---------------------------
# COLUMNS

def get_columns():
    return [
        {
            "label": "Month",
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Total Sales",
            "fieldname": "total_sales",
            "fieldtype": "Currency",
            "width": 150
        }
    ]


# ---------------------------
# DATA
# ---------------------------
def get_data(filters):
    conditions = "WHERE docstatus = 1"
    params = {}

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND posting_date BETWEEN %(from_date)s AND %(to_date)s"
        params["from_date"] = filters["from_date"]
        params["to_date"] = filters["to_date"]

    return frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(posting_date, '%%Y-%%m') AS month,
            SUM(grand_total) AS total_sales
        FROM `tabSales Invoice`
        {conditions}
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month
    """, params, as_dict=True)


# ---------------------------
# CHART
# ---------------------------
def get_chart_data(data):
    if not data:
        return None

    labels = [d.get("month") for d in data]
    values = [float(d.get("total_sales") or 0) for d in data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Sales Progress",
                    "values": values
                }
            ]
        },
        "type": "line",
        "colors": ["#ff5858"],

        # IMPORTANT for proper hover + points
        "lineOptions": {
            "hideDots": 0
        }
    }