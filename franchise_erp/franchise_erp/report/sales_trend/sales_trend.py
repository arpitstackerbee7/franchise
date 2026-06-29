# # Copyright (c) 2026, Franchise Erp and contributors
# # For license information, please see license.txt

# # import frappe


# def execute(filters=None):
# 	columns, data = [], []
# 	return columns, data
# import frappe


# def execute(filters=None):
#     filters = filters or {}

#     # ALWAYS SAFE FY (reset-proof + no dependency on UI)
#     fiscal_year = filters.get("fiscal_year")

#     # If empty → pick current/latest FY safely
#     if not fiscal_year:
#         fiscal_year = frappe.db.get_value(
#             "Fiscal Year",
#             {},
#             "name",
#             order_by="year_start_date desc"
#         )

#     # ❌ Never throw (prevents popup)
#     if not fiscal_year:
#         return [], [], None, {
#             "data": {"labels": [], "datasets": []},
#             "type": "bar"
#         }

#     fy = frappe.get_doc("Fiscal Year", fiscal_year)
#     curr_start = fy.year_start_date
#     curr_end = fy.year_end_date

#     # Previous FY
#     prev_fy = frappe.db.sql("""
#         SELECT name, year_start_date, year_end_date
#         FROM `tabFiscal Year`
#         WHERE year_start_date < %(curr_start)s
#         ORDER BY year_start_date DESC
#         LIMIT 1
#     """, {"curr_start": curr_start}, as_dict=True)

#     prev_start = prev_end = None
#     prev_label = None

#     if prev_fy:
#         prev_start = prev_fy[0].year_start_date
#         prev_end = prev_fy[0].year_end_date
#         prev_label = prev_fy[0].name

#     columns = get_columns()
#     data = get_data(curr_start, curr_end, prev_start, prev_end)
#     chart = get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label)

#     # ✅ HARD GUARANTEE: chart never breaks UI
#     if not chart or not chart.get("data"):
#         chart = {
#             "data": {
#                 "labels": [],
#                 "datasets": []
#             },
#             "type": "bar"
#         }

#     return columns, data, None, chart


# def get_columns():
#     return [
#         {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 120},
#         {"label": "Previous Year", "fieldname": "year_1", "fieldtype": "Currency", "width": 150},
#         {"label": "Selected Year", "fieldname": "year_2", "fieldtype": "Currency", "width": 150},
#     ]


# def get_data(curr_start, curr_end, prev_start, prev_end):
#     months_order = [
#         "Apr", "May", "Jun", "Jul", "Aug", "Sep",
#         "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"
#     ]

#     result_map = {
#         m: {"month": m, "year_1": 0, "year_2": 0}
#         for m in months_order
#     }

#     query_filters = {
#         "curr_start": curr_start,
#         "curr_end": curr_end,
#     }

#     # Previous year safe logic
#     if prev_start and prev_end:
#         prev_condition = """
#             SUM(CASE 
#                 WHEN posting_date BETWEEN %(prev_start)s AND %(prev_end)s 
#                 THEN grand_total ELSE 0 
#             END) AS year_1
#         """
#         query_filters["prev_start"] = prev_start
#         query_filters["prev_end"] = prev_end
#     else:
#         prev_condition = "0 AS year_1"

#     data = frappe.db.sql(f"""
#         SELECT
#             DATE_FORMAT(posting_date, '%%b') AS month,
#             {prev_condition},
#             SUM(CASE 
#                 WHEN posting_date BETWEEN %(curr_start)s AND %(curr_end)s 
#                 THEN grand_total ELSE 0 
#             END) AS year_2
#         FROM `tabSales Invoice`
#         WHERE docstatus = 1
#           AND posting_date BETWEEN %(curr_start)s AND %(curr_end)s
#         GROUP BY YEAR(posting_date), MONTH(posting_date)
#         ORDER BY MONTH(posting_date)
#     """, query_filters, as_dict=True)

#     for row in data:
#         m = row.get("month")
#         if m in result_map:
#             result_map[m]["year_1"] = row.get("year_1") or 0
#             result_map[m]["year_2"] = row.get("year_2") or 0

#     return [result_map[m] for m in months_order]


# def get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label):
#     return {
#         "data": {
#             "labels": [d["month"] for d in data],
#             "datasets": [
#                 {
#                     "name": prev_label or "Previous Year",
#                     "values": [d["year_1"] for d in data]
#                 },
#                 {
#                     "name": f"{curr_start.year}-{str(curr_end.year)[-2:]}",
#                     "values": [d["year_2"] for d in data]
#                 }
#             ]
#         },
#         "type": "bar"
#     }


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