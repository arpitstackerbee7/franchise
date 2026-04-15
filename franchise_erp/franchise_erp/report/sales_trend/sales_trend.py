import frappe


def execute(filters=None):
    filters = filters or {}

    # ALWAYS SAFE FY (reset-proof + no dependency on UI)
    fiscal_year = filters.get("fiscal_year")

    # If empty → pick current/latest FY safely
    if not fiscal_year:
        fiscal_year = frappe.db.get_value(
            "Fiscal Year",
            {},
            "name",
            order_by="year_start_date desc"
        )

    # ❌ Never throw (prevents popup)
    if not fiscal_year:
        return [], [], None, {
            "data": {"labels": [], "datasets": []},
            "type": "bar"
        }

    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    curr_start = fy.year_start_date
    curr_end = fy.year_end_date

    # Previous FY
    prev_fy = frappe.db.sql("""
        SELECT name, year_start_date, year_end_date
        FROM `tabFiscal Year`
        WHERE year_start_date < %(curr_start)s
        ORDER BY year_start_date DESC
        LIMIT 1
    """, {"curr_start": curr_start}, as_dict=True)

    prev_start = prev_end = None
    prev_label = None

    if prev_fy:
        prev_start = prev_fy[0].year_start_date
        prev_end = prev_fy[0].year_end_date
        prev_label = prev_fy[0].name

    columns = get_columns()
    data = get_data(curr_start, curr_end, prev_start, prev_end)
    chart = get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label)

    # ✅ HARD GUARANTEE: chart never breaks UI
    if not chart or not chart.get("data"):
        chart = {
            "data": {
                "labels": [],
                "datasets": []
            },
            "type": "bar"
        }

    return columns, data, None, chart


def get_columns():
    return [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 120},
        {"label": "Previous Year", "fieldname": "year_1", "fieldtype": "Currency", "width": 150},
        {"label": "Selected Year", "fieldname": "year_2", "fieldtype": "Currency", "width": 150},
    ]


def get_data(curr_start, curr_end, prev_start, prev_end):
    months_order = [
        "Apr", "May", "Jun", "Jul", "Aug", "Sep",
        "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"
    ]

    result_map = {
        m: {"month": m, "year_1": 0, "year_2": 0}
        for m in months_order
    }

    query_filters = {
        "curr_start": curr_start,
        "curr_end": curr_end,
    }

    # Previous year safe logic
    if prev_start and prev_end:
        prev_condition = """
            SUM(CASE 
                WHEN posting_date BETWEEN %(prev_start)s AND %(prev_end)s 
                THEN grand_total ELSE 0 
            END) AS year_1
        """
        query_filters["prev_start"] = prev_start
        query_filters["prev_end"] = prev_end
    else:
        prev_condition = "0 AS year_1"

    data = frappe.db.sql(f"""
        SELECT
            DATE_FORMAT(posting_date, '%%b') AS month,
            {prev_condition},
            SUM(CASE 
                WHEN posting_date BETWEEN %(curr_start)s AND %(curr_end)s 
                THEN grand_total ELSE 0 
            END) AS year_2
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date BETWEEN %(curr_start)s AND %(curr_end)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY MONTH(posting_date)
    """, query_filters, as_dict=True)

    for row in data:
        m = row.get("month")
        if m in result_map:
            result_map[m]["year_1"] = row.get("year_1") or 0
            result_map[m]["year_2"] = row.get("year_2") or 0

    return [result_map[m] for m in months_order]


def get_chart_data(data, curr_start, curr_end, prev_start, prev_end, prev_label):
    return {
        "data": {
            "labels": [d["month"] for d in data],
            "datasets": [
                {
                    "name": prev_label or "Previous Year",
                    "values": [d["year_1"] for d in data]
                },
                {
                    "name": f"{curr_start.year}-{str(curr_end.year)[-2:]}",
                    "values": [d["year_2"] for d in data]
                }
            ]
        },
        "type": "bar"
    }