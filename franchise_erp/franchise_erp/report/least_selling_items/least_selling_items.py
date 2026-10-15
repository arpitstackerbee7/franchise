import frappe
#from franchise_erp.utils.dashboard_permissions import get_allowed_company
from franchise_erp.utils.dashboard_permissions import resolve_dashboard_source


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data, filters)

    return columns, data, None, chart


def get_columns(filters):
    metric = filters.get("metric") or "qty"

    cols = [
        {
            "label": "Style No.",
            "fieldname": "style_no",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 150
        }
    ]

    if metric == "qty":
        cols.append({
            "label": "Quantity",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 120
        })
    else:  # amt
        cols.append({
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120
        })

    return cols


# def get_data(filters):
#     limit     = filters.get("limit") or 10
#     metric    = filters.get("metric") or "qty"
#     from_date = filters.get("from_date")
#     to_date   = filters.get("to_date")
#     company   = get_allowed_company(filters)

#     if metric == "qty":
#         select_field = "SUM(sii.qty) AS qty"
#         order_by     = "qty ASC"
#     else:  # amt
#         select_field = "SUM(sii.base_net_amount) AS amount"
#         order_by     = "amount ASC"

#     conditions = "WHERE si.docstatus = 1 AND si.is_return = 0"
#     params = []

#     if from_date and to_date:
#         conditions += " AND si.posting_date BETWEEN %s AND %s"
#         params.extend([from_date, to_date])

#     if company:
#         conditions += " AND si.company = %s"
#         params.append(company)

#     params.append(limit)

#     data = frappe.db.sql(f"""
#         SELECT
#             i.custom_barcode_code AS style_no,
#             i.custom_departments  AS department,
#             i.image,
#             {select_field}
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON sii.parent = si.name
#         LEFT JOIN `tabItem` i ON i.item_code = sii.item_code
#         {conditions}
#         GROUP BY i.custom_barcode_code
#         ORDER BY {order_by}
#         LIMIT %s
#     """, tuple(params), as_dict=1)

#     for row in data:
#         img = row.get("image")
#         row["image_url"] = ("/" + img if img and not img.startswith("/") else img) or ""
#         dept = row.get("department") or ""
#         row["department"] = dept.split("-")[-1].strip() if dept else ""

#     return data

def get_data(filters):
    limit     = filters.get("limit") or 10
    metric    = filters.get("metric") or "qty"
    from_date = filters.get("from_date")
    to_date   = filters.get("to_date")

    company, doctype = resolve_dashboard_source(filters)

    if doctype == "Sales Invoice":
        parent_table, child_table, amount_field = "tabSales Invoice", "tabSales Invoice Item", "base_net_amount"
    else:
        parent_table, child_table, amount_field = "tabDelivery Note", "tabDelivery Note Item", "base_amount"

    if metric == "qty":
        select_field = "SUM(item.qty) AS qty"
        order_by     = "qty ASC"
    else:  # amt
        select_field = f"SUM(item.{amount_field}) AS amount"
        order_by     = "amount ASC"

    conditions = "WHERE txn.docstatus = 1 AND txn.is_return = 0 AND txn.company = %s"
    params = [company]

    if from_date and to_date:
        conditions += " AND txn.posting_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    params.append(limit)

    data = frappe.db.sql(f"""
        SELECT
            i.custom_barcode_code AS style_no,
            i.custom_departments  AS department,
            i.image,
            {select_field}
        FROM `{child_table}` item
        JOIN `{parent_table}` txn ON item.parent = txn.name
        LEFT JOIN `tabItem` i ON i.item_code = item.item_code
        {conditions}
        GROUP BY i.custom_barcode_code
        ORDER BY {order_by}
        LIMIT %s
    """, tuple(params), as_dict=1)

    for row in data:
        img = row.get("image")
        row["image_url"] = ("/" + img if img and not img.startswith("/") else img) or ""
        dept = row.get("department") or ""
        row["department"] = dept.split("-")[-1].strip() if dept else ""

    return data

def get_chart_data(data, filters):
    metric = filters.get("metric") or "qty"

    if not data:
        return {
            "data": {
                "labels": [],
                "datasets": [{"name": "Least Sold", "values": []}]
            },
            "type": "bar"
        }

    labels = [d.get("style_no") or "No Style" for d in data]

    if metric == "qty":
        values = [float(d.get("qty") or 0) for d in data]
        name   = "Least Sold Quantity"
    else:  # amt
        values = [float(d.get("amount") or 0) for d in data]
        name   = "Least Sold Amount"

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": name, "values": values}]
        },
        "type": "bar"
    }