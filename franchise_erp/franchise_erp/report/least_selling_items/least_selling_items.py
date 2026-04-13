# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


import frappe


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)

    return columns, data, None, chart


# ---------------- COLUMNS ----------------
def get_columns(filters):
    metric = filters.get("metric") or "qty"

    cols = [
        {
            "label": "Item Name",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 250
        }
    ]

    if metric == "qty":
        cols.append({
            "label": "Quantity",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 120
        })

    elif metric == "amount":
        cols.append({
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120
        })

    return cols


# ---------------- DATA ----------------
def get_data(filters):
    limit = filters.get("limit") or 10
    metric = filters.get("metric") or "qty"
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Metric logic
    if metric == "qty":
        select_field = "SUM(sii.qty) AS qty"
        order_by = "qty ASC"   # Least first
    else:
        select_field = "SUM(sii.base_net_amount) AS amount"
        order_by = "amount ASC"

    # Conditions
    conditions = "WHERE si.docstatus = 1 AND si.is_return = 0"
    params = []

    if from_date and to_date:
        conditions += " AND si.posting_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    # Add limit param
    params.append(limit)

    # Query
    data = frappe.db.sql(f"""
        SELECT 
            sii.item_name,
            {select_field}
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si
          ON sii.parent = si.name
        {conditions}
        GROUP BY sii.item_name
        ORDER BY {order_by}
        LIMIT %s
    """, tuple(params), as_dict=1)

    return data


# ---------------- CHART ----------------
def get_chart_data(data, filters):
    metric = filters.get("metric") or "qty"

    labels = [d["item_name"] for d in data]

    if metric == "qty":
        values = [d.get("qty", 0) for d in data]
        name = "Least Sold Quantity"
    else:
        values = [d.get("amount", 0) for d in data]
        name = "Least Sold Amount"

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": name,
                    "values": values
                }
            ]
        },
        "type": "bar"
    }