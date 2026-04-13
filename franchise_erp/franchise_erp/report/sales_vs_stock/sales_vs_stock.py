# # Copyright (c) 2026, Franchise Erp and contributors
# # For license information, please see license.txt

# # import frappe

# import frappe
# from frappe import _

# def execute(filters=None):
#     if not filters:
#         filters = {}

#     columns = get_columns()
#     data = get_data(filters)
#     chart = get_chart_data(data)

#     return columns, data, None, chart


# # ✅ Columns
# def get_columns():
#     return [
#         {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
#         {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
#         {"label": _("Sales"), "fieldname": "sales", "fieldtype": "Float", "width": 120},
#         {"label": _("Stock"), "fieldname": "stock", "fieldtype": "Float", "width": 120},
#         {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
#     ]


# # ✅ Main Data Logic (OPTIMIZED - no loop queries)
# def get_data(filters):
#     conditions = ""
#     values = {}

#     if filters.get("from_date") and filters.get("to_date"):
#         conditions += " AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s"
#         values["from_date"] = filters.get("from_date")
#         values["to_date"] = filters.get("to_date")

#     # 🔹 Fetch Sales per Item
#     sales_data = frappe.db.sql("""
#         SELECT 
#             sii.item_code,
#             SUM(sii.qty) as total_sales
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON sii.parent = si.name
#         WHERE si.docstatus = 1
#         {conditions}
#         GROUP BY sii.item_code
#     """.format(conditions=conditions), values, as_dict=1)

#     sales_map = {d.item_code: d.total_sales for d in sales_data}

#     # 🔹 Fetch Stock from Bin
#     stock_data = frappe.db.sql("""
#         SELECT item_code, SUM(actual_qty) as stock
#         FROM `tabBin`
#         GROUP BY item_code
#     """, as_dict=1)

#     stock_map = {d.item_code: d.stock for d in stock_data}

#     # 🔹 Fetch All Items
#     items = frappe.get_all("Item", fields=["name", "item_name"])

#     data = []

#     for item in items:
#         sales = sales_map.get(item.name, 0)
#         stock = stock_map.get(item.name, 0)

#         # ✅ Status Logic
#         if stock == 0:
#             status = "SOLD OUT"
#         elif sales > 0 and stock <= (sales * 0.5):
#             status = "FAST MOVING"
#         else:
#             status = "NORMAL"

#         data.append({
#             "item_code": item.name,
#             "item_name": item.item_name,
#             "sales": sales,
#             "stock": stock,
#             "status": status
#         })

#     return data


# # ✅ Chart (Bar Chart)
# def get_chart_data(data):
#     labels = []
#     sales = []
#     stock = []

#     # Limit chart to top 10 items for better UI
#     sorted_data = sorted(data, key=lambda x: x["sales"], reverse=True)[:10]

#     for row in sorted_data:
#         labels.append(row["item_name"])
#         sales.append(row["sales"])
#         stock.append(row["stock"])

#     return {
#         "data": {
#             "labels": labels,
#             "datasets": [
#                 {"name": "Sales", "values": sales},
#                 {"name": "Stock", "values": stock}
#             ]
#         },
#         "type": "bar"
#     }
# file: monthly_item_report.py

import frappe
from frappe.utils import nowdate

def execute(filters=None):
    if not filters:
        filters = {}

    # Fix: default month (important for dashboard)
    if not filters.get("month"):
        filters["month"] = int(nowdate().split("-")[1])

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)

    return columns, data, None, chart


def get_columns():
    return [
        {"label": "Item", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": "Sales Qty", "fieldname": "sales_qty", "fieldtype": "Float", "width": 120},
        {"label": "Stock Qty", "fieldname": "stock_qty", "fieldtype": "Float", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    conditions = ""

    if filters.get("month"):
        conditions += " AND MONTH(si.posting_date) = %(month)s"

    data = frappe.db.sql(f"""
        SELECT 
            sii.item_name AS item_name,
            MONTH(si.posting_date) AS month,
            SUM(sii.qty) AS sales_qty,

            IFNULL((
                SELECT actual_qty 
                FROM `tabBin` b 
                WHERE b.item_code = sii.item_code 
                LIMIT 1
            ), 0) AS stock_qty,

            CASE 
                WHEN IFNULL((
                    SELECT actual_qty 
                    FROM `tabBin` b 
                    WHERE b.item_code = sii.item_code 
                    LIMIT 1
                ), 0) > SUM(sii.qty)
                THEN 'In Stock'
                ELSE 'Low Stock'
            END AS status

        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name

        WHERE si.docstatus = 1 {conditions}

        GROUP BY sii.item_code, MONTH(si.posting_date)
    """, filters, as_dict=1)

    return data


#  NEW: Chart function (REQUIRED for dashboard)
def get_chart_data(data):
    labels = []
    sales = []
    stock = []

    for row in data:
        labels.append(row.get("item_name") or "No Item")
        sales.append(row.get("sales_qty") or 0)
        stock.append(row.get("stock_qty") or 0)

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Sales",
                    "values": sales
                },
                {
                    "name": "Stock",
                    "values": stock
                }
            ]
        },
        "type": "bar"
    }