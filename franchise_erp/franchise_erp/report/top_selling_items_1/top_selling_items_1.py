# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


# import frappe

# def execute(filters=None):
#     columns = get_columns()
#     data = get_data(filters)
#     return columns, data


# def get_columns():
#     return [
#         {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 250},
#         {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 120},
#     ]


# def get_data(filters):
#     limit = filters.get("limit") or 10

#     data = frappe.db.sql("""
#         SELECT 
#             item_name,
#             SUM(qty) as qty
#         FROM `tabSales Invoice Item`
#         WHERE docstatus = 1
#         GROUP BY item_name
#         ORDER BY qty DESC
#         LIMIT %s
#     """, (limit,), as_dict=1)

#     return data
















# import frappe

# def execute(filters=None):
#     columns = get_columns(filters)
#     data = get_data(filters)
#     return columns, data


# def get_columns(filters):
#     metric = filters.get("metric") or "qty"

#     if metric == "amount":
#         return [
#             {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 250},
#             {"label": "Amount", "fieldname": "value", "fieldtype": "Currency", "width": 150},
#         ]
#     else:
#         return [
#             {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 250},
#             {"label": "Quantity", "fieldname": "value", "fieldtype": "Float", "width": 150},
#         ]

# def get_data(filters):
#     limit = filters.get("limit") or 10
#     metric = filters.get("metric") or "qty"
#     period = filters.get("period") or "Monthly"

#     # Decide field
#     if metric == "amount":
#         value_field = "SUM(base_net_amount)"
#         alias = "amount"
#     else:
#         value_field = "SUM(qty)"
#         alias = "qty"

#     # Period condition
#     date_group = ""
#     if period == "Monthly":
#         date_group = "DATE_FORMAT(posting_date, '%Y-%m')"
#     elif period == "Quarterly":
#         date_group = "CONCAT(YEAR(posting_date), '-Q', QUARTER(posting_date))"
#     elif period == "Yearly":
#         date_group = "YEAR(posting_date)"

#     data = frappe.db.sql(f"""
#         SELECT 
#             item_name,
#             {value_field} as {alias}
#         FROM `tabSales Invoice Item`
#         WHERE docstatus = 1
#         GROUP BY item_name
#         ORDER BY {alias} DESC
#         LIMIT %s
#     """, (limit,), as_dict=1)

#     return data



















#new

import frappe


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)

    return columns, data, None, chart


# ------------------ COLUMNS ------------------
def get_columns(filters):
    metric = filters.get("metric") or "qty"
    period = filters.get("period") or "Monthly"

    cols = []

    # Period column
    if period in ["Monthly", "Quarterly", "Yearly"]:
        cols.append({
            "label": "Period",
            "fieldname": "period",
            "fieldtype": "Data",
            "width": 120
        })

    # Item Name
    cols.append({
        "label": "Item Name",
        "fieldname": "item_name",
        "fieldtype": "Data",
        "width": 250
    })

    # Metric column
    if metric == "qty":
        cols.append({
            "label": "Quantity",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 150
        })
    elif metric == "amount":
        cols.append({
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 150
        })

    return cols


# ------------------ DATA ------------------
def get_data(filters):
    limit = filters.get("limit") or 10
    metric = filters.get("metric") or "qty"
    period = filters.get("period") or "Monthly"

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Period grouping
    if period == "Monthly":
        date_group = "DATE_FORMAT(si.posting_date, '%%Y-%%m')"
    elif period == "Quarterly":
        date_group = "CONCAT(YEAR(si.posting_date), '-Q', QUARTER(si.posting_date))"
    elif period == "Yearly":
        date_group = "YEAR(si.posting_date)"
    else:
        date_group = None

    # SELECT fields
    select_fields = ["sii.item_name"]

    if metric == "qty":
        select_fields.append("SUM(sii.qty) AS qty")
    else:
        select_fields.append("SUM(sii.base_net_amount) AS amount")

    if date_group:
        select_fields.append(f"{date_group} AS period")

    # GROUP BY
    group_by_fields = ["sii.item_name"]
    if date_group:
        group_by_fields.append(date_group)

    # ORDER BY
    order_by = "qty DESC" if metric == "qty" else "amount DESC"

    # CONDITIONS
    conditions = "WHERE si.docstatus = 1 AND si.is_return = 0"
    params = []

    if from_date and to_date:
        conditions += " AND si.posting_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    # Add LIMIT param at end
    params.append(limit)

    # QUERY
    data = frappe.db.sql(f"""
        SELECT {", ".join(select_fields)}
        FROM `tabSales Invoice Item` AS sii
        JOIN `tabSales Invoice` AS si
          ON sii.parent = si.name
        {conditions}
        GROUP BY {", ".join(group_by_fields)}
        ORDER BY {order_by}
        LIMIT %s
    """, tuple(params), as_dict=1)

    return data


# ------------------ CHART ------------------
def get_chart_data(data, filters):
    metric = filters.get("metric") or "qty"

    labels = [d["item_name"] for d in data]

    if metric == "qty":
        values = [d.get("qty", 0) for d in data]
        dataset_name = "Quantity"
    else:
        values = [d.get("amount", 0) for d in data]
        dataset_name = "Amount"

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": dataset_name,
                    "values": values
                }
            ]
        },
        "type": "bar"
    }