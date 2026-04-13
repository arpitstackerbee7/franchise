# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_years

def execute(filters=None):
    if not filters:
        filters = {}

    fiscal_year = filters.get("fiscal_year")
    if not fiscal_year:
        frappe.throw("Please select a Fiscal Year")

    # Selected FY
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    curr_start = fy.year_start_date
    curr_end = fy.year_end_date

    # Previous FY = latest fiscal year before selected
    prev_fy = frappe.db.sql("""
        SELECT name, year_start_date, year_end_date
        FROM `tabFiscal Year`
        WHERE docstatus=1
          AND year_start_date < %(curr_start)s
        ORDER BY year_start_date DESC
        LIMIT 1
    """, {"curr_start": curr_start}, as_dict=True)

    if prev_fy:
        prev_start = prev_fy[0].year_start_date
        prev_end = prev_fy[0].year_end_date
        prev_label = prev_fy[0].name
    else:
        prev_start = prev_end = None
        prev_label = None

    columns = get_columns()
    data = get_data(curr_start, curr_end, prev_start, prev_end)
    chart = get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label)

    return columns, data, None, chart


def get_columns():
    return [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 120},
        {"label": "Previous Year", "fieldname": "year_1", "fieldtype": "Currency", "width": 150},
        {"label": "Selected Year", "fieldname": "year_2", "fieldtype": "Currency", "width": 150},
    ]


def get_data(curr_start, curr_end, prev_start, prev_end):
    months_order = ["Apr", "May", "Jun", "Jul", "Aug", "Sep",
                    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

    result_map = {m: {"month": m, "year_1": 0, "year_2": 0} for m in months_order}

    query_filters = {
        "curr_start": curr_start,
        "curr_end": curr_end,
    }

    prev_condition = ""
    if prev_start and prev_end:
        prev_condition = "SUM(CASE WHEN posting_date BETWEEN %(prev_start)s AND %(prev_end)s THEN grand_total ELSE 0 END) AS year_1,"
        query_filters["prev_start"] = prev_start
        query_filters["prev_end"] = prev_end
    else:
        prev_condition = "0 AS year_1,"

    data = frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(posting_date, '%%b') AS month,
            {prev_condition}
            SUM(CASE WHEN posting_date BETWEEN %(curr_start)s AND %(curr_end)s THEN grand_total ELSE 0 END) AS year_2
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date <= %(curr_end)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY MONTH(posting_date)
    """, query_filters, as_dict=True)

    for row in data:
        if row["month"] in result_map:
            result_map[row["month"]]["year_1"] = row.get("year_1", 0)
            result_map[row["month"]]["year_2"] = row.get("year_2", 0)

    return [result_map[m] for m in months_order]


def get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label):
    prev_label_text = prev_label if prev_label else "Previous Year"
    curr_label_text = f"{curr_start.year}-{str(curr_end.year)[-2:]}"

    labels = [d["month"] for d in data]
    dataset_1 = [d["year_1"] for d in data]
    dataset_2 = [d["year_2"] for d in data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": prev_label_text, "values": dataset_1, "color": "#4F9DFF"},
                {"name": curr_label_text, "values": dataset_2, "color": "#28A745"}
            ]
        },
        "type": "bar"
    }