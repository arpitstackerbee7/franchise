# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)

    return columns, data, None, chart


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


def get_data(filters):
    conditions = "WHERE docstatus = 1"

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND posting_date BETWEEN %(from_date)s AND %(to_date)s"

    return frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(posting_date, '%%Y-%%m') AS month,
            SUM(grand_total) AS total_sales
        FROM `tabSales Invoice`
        {conditions}
        GROUP BY month
        ORDER BY month
    """, filters, as_dict=True)


def get_chart_data(data):
    labels = [d["month"] for d in data]
    values = [d["total_sales"] for d in data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Sales",
                    "values": values
                }
            ]
        },
        "type": "line",
        "colors": ["#ff5858"]
    }