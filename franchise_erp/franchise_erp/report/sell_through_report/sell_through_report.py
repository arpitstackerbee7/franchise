import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": "Style",
            "fieldname": "style",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180,
        },
        {
            "label": "Purchase Receipts Qty",
            "fieldname": "purchase_qty",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Dispatch",
            "fieldname": "dispatch_qty",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Sales",
            "fieldname": "sales_qty",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Stock at Warehouse",
            "fieldname": "warehouse_stock",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Stock at SIS Counter",
            "fieldname": "sis_stock",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Total Stock(Wharehouse + SIS Counter)",
            "fieldname": "total_stock",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Stock In Date",
            "fieldname": "stock_in_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Avg Stock Carrying Days at SIS",
            "fieldname": "avg_stock_carrying_days",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "No. of Counter",
            "fieldname": "no_of_counter",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": "Daily Planned Sale (1% of Average Carrying Days at SIS)",
            "fieldname": "daily_planned_sale",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Actual Sale Through %",
            "fieldname": "actual_sale_through",
            "fieldtype": "int",
            "width": 80,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 150,
        }
    ]


def get_data(filters):

    filters = filters or {}

    items = frappe.get_all(
        "Item",
        fields=[
            "item_code",
            "custom_barcode_code"
        ],
        filters={
            "disabled": 0
        },
        order_by="custom_barcode_code asc, item_code asc"
    )

    data = []

    previous_style = None

    for item in items:

        style = (item.custom_barcode_code or "").strip()

        # Purchase Receipt Qty
        # purchase_qty = frappe.db.sql("""
        #     SELECT COALESCE(SUM(pri.qty),0)
        #     FROM `tabPurchase Receipt Item` pri
        #     INNER JOIN `tabPurchase Receipt` pr
        #         ON pr.name = pri.parent
        #     WHERE
        #         pr.docstatus = 1
        #         AND pr.company = %s
        #         AND pri.item_code = %s
        #         AND pr.posting_date BETWEEN %s AND %s
        # """, (
        #     "TZU Lifestyle Private Limited",
        #     item.item_code,
        #     filters.get("from_date"),
        #     filters.get("to_date")
        # ))[0][0]
        purchase_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(pri.qty),0)
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr
                ON pr.name = pri.parent
            WHERE
                pr.docstatus = 1
                AND pr.company = %s
                AND pri.item_code = %s
                AND pr.posting_date BETWEEN %s AND %s
        """, (
            "TZU Lifestyle Private Limited",
            item.item_code,
            filters.get("from_date"),
            filters.get("to_date")
        ))[0][0]

        # 🔥 ADD THIS FILTER
        if not purchase_qty or purchase_qty == 0:
            continue
        

        # Dispatch Qty (Sales Invoice -> Internal Customer)
        dispatch_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(sii.qty), 0)
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            INNER JOIN `tabCustomer` c
                ON c.name = si.customer
            WHERE
                si.docstatus = 1
                AND si.company = %s
                AND c.is_internal_customer = 1
                AND sii.item_code = %s
                AND si.posting_date BETWEEN %s AND %s
        """, (
            "TZU Lifestyle Private Limited",
            item.item_code,
            filters.get("from_date"),
            filters.get("to_date")
        ))[0][0]
        
        # Sales Qty (Counter -> Retail Delivery Note)
        sales_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(dni.qty), 0)
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn
                ON dn.name = dni.parent
            INNER JOIN `tabCustomer` retail
                ON retail.name = dn.customer
            WHERE
                dn.docstatus = 1
                AND IFNULL(retail.is_internal_customer, 0) = 0
                AND dni.item_code = %s
                AND dn.posting_date BETWEEN %s AND %s
        """, (
            item.item_code,
            filters.get("from_date"),
            filters.get("to_date")
        ))[0][0]
        
        # Stock at Warehouse (All TZU Warehouses)
        warehouse_stock = frappe.db.sql("""
            SELECT COALESCE(SUM(b.actual_qty), 0)
            FROM `tabBin` b
            INNER JOIN `tabWarehouse` w
                ON w.name = b.warehouse
            WHERE
                b.item_code = %s
                AND w.company = %s
                AND IFNULL(w.disabled, 0) = 0
        """, (
            item.item_code,
            "TZU Lifestyle Private Limited"
        ))[0][0]

        # Stock at SIS Counter
        sis_stock = frappe.db.sql("""
            SELECT COALESCE(SUM(b.actual_qty), 0)
            FROM `tabBin` b
            INNER JOIN `tabWarehouse` w
                ON w.name = b.warehouse
            WHERE
                b.item_code = %s
                AND w.company IN (
                    SELECT DISTINCT represents_company
                    FROM `tabCustomer`
                    WHERE IFNULL(is_internal_customer, 0) = 1
                )
                AND IFNULL(w.disabled, 0) = 0
        """, (
            item.item_code,
        ))[0][0]

        # Stock In Date (Latest Purchase Receipt Date)
        stock_in_date = frappe.db.sql("""
            SELECT MAX(pr.posting_date)
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr
                ON pr.name = pri.parent
            WHERE
                pr.docstatus = 1
                AND pr.company = %s
                AND pri.item_code = %s
        """, (
            "TZU Lifestyle Private Limited",
            item.item_code
        ))[0][0]

        # Avg Stock Carrying Days at SIS
        counter_dates = frappe.db.sql("""
            SELECT
                MAX(si.posting_date) as last_dispatch_date
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            INNER JOIN `tabCustomer` c
                ON c.name = si.customer
            WHERE
                si.docstatus = 1
                AND si.company = %s
                AND c.is_internal_customer = 1
                AND sii.item_code = %s
            GROUP BY si.customer
        """, (
            "TZU Lifestyle Private Limited",
            item.item_code
        ), as_dict=True)

        avg_stock_carrying_days = 0

        if counter_dates:

            total_days = 0
            total_counter = 0

            report_to_date = getdate(filters.get("to_date"))

            for d in counter_dates:

                if d.last_dispatch_date:

                    last_date = getdate(d.last_dispatch_date)

                    days = (report_to_date - last_date).days

                    total_days += days
                    total_counter += 1

            if total_counter:
                avg_stock_carrying_days = round(
                    total_days / total_counter,
                    2
                )

        # No. of Counter (Unique Internal Customers)
        no_of_counter = frappe.db.sql("""
            SELECT COUNT(DISTINCT si.customer)
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            INNER JOIN `tabCustomer` c
                ON c.name = si.customer
            WHERE
                si.docstatus = 1
                AND si.company = %s
                AND IFNULL(c.is_internal_customer, 0) = 1
                AND sii.item_code = %s
                AND si.posting_date BETWEEN %s AND %s
        """, (
            "TZU Lifestyle Private Limited",
            item.item_code,
            filters.get("from_date"),
            filters.get("to_date")
        ))[0][0]


        actual_sale_through = 0

        if dispatch_qty:
            actual_sale_through = (sales_qty or 0) / dispatch_qty * 100

        actual_sale_through = ((sales_qty or 0) / dispatch_qty * 100) if dispatch_qty else 0
        daily_planned_sale = (avg_stock_carrying_days or 0) * (no_of_counter or 0) * 0.01

        status = "RED"
        if actual_sale_through >= daily_planned_sale:
            status = "GREEN"
        elif actual_sale_through >= (daily_planned_sale * 0.5):
            status = "YELLOW"

        row = {
            "style": style,
            "item_code": item.item_code,
            "purchase_qty": purchase_qty,
            "dispatch_qty": dispatch_qty,
            "sales_qty": sales_qty,
            "warehouse_stock": warehouse_stock,
            "sis_stock": sis_stock,
            "total_stock": warehouse_stock + sis_stock,
            "stock_in_date": stock_in_date,
            "avg_stock_carrying_days": avg_stock_carrying_days,
            "no_of_counter": no_of_counter,
            "daily_planned_sale": (avg_stock_carrying_days or 0) * (no_of_counter or 0) * 0.01,
            "actual_sale_through": ((sales_qty or 0) / dispatch_qty * 100) if dispatch_qty else 0,
            "status": status
        }
        # Style blank ho to skip
        if style:
            data.append(row)

      # ----------------------------------
    # Grouping Start
    # ----------------------------------

    final_data = []
    style_rows = []
    current_style = None
    previous_style = None

    data.sort(
        key=lambda x: (
            x.get("style") or "",
            x.get("item_code") or ""
        )
    )

    # for row in data:

    #     style = row.get("style")

    #     if current_style is None:
    #         current_style = style

    #     if current_style != style:

    #         final_data.extend(style_rows)
    #         add_style_total(
    #             final_data,
    #             style_rows,
    #             current_style
    #         )

    #         style_rows = []
    #         current_style = style

    #     if style != previous_style:
    #         previous_style = style
    #     else:
    #         row["style"] = ""

    #     style_rows.append(row)
    for row in data:

        style = row["style"]

        if current_style is None:
            current_style = style

        if current_style != style:

            final_data.extend(style_rows)
            add_style_total(final_data, style_rows, current_style)

            style_rows = []
            current_style = style
            previous_style = None

        # style sirf first row me
        if style == previous_style:
            row["style"] = ""
        else:
            previous_style = style

        style_rows.append(row)

    # Last Style Total

    if style_rows:
        final_data.extend(style_rows)
        add_style_total(
            final_data,
            style_rows,
            current_style
        )

    return final_data


def add_style_total(final_data, style_rows, style):
    purchase_qty = sum(r.get("purchase_qty") or 0 for r in style_rows)
    dispatch_qty = sum(r.get("dispatch_qty") or 0 for r in style_rows)
    sales_qty = sum(r.get("sales_qty") or 0 for r in style_rows)

    warehouse_stock = sum(r.get("warehouse_stock") or 0 for r in style_rows)
    sis_stock = sum(r.get("sis_stock") or 0 for r in style_rows)
    total_stock = sum(r.get("total_stock") or 0 for r in style_rows)

    avg_stock_carrying_days = round(
        sum(r.get("avg_stock_carrying_days") or 0 for r in style_rows)
        / len(style_rows),
        2
    ) if style_rows else 0

    no_of_counter = round(
        (
            sum(r["no_of_counter"] or 0 for r in style_rows)
            / len(style_rows)
        )
    ) if style_rows else 0

    green = sum(1 for r in style_rows if r["status"] == "GREEN")
    yellow = sum(1 for r in style_rows if r["status"] == "YELLOW")
    red = sum(1 for r in style_rows if r["status"] == "RED")

    if green >= yellow and green >= red:
        total_status = "GREEN"
    elif yellow >= green and yellow >= red:
        total_status = "YELLOW"
    else:
        total_status = "RED"

    daily_planned_sale = round(
        avg_stock_carrying_days * no_of_counter * 0.01,
        2
    )

    actual_sale_through = round(
        (sales_qty / dispatch_qty) * 100,
        2
    ) if dispatch_qty else 0

    # final_data.extend(style_rows)

    final_data.append({
        "style": f"{style} Total",
        "item_code": "",
        "purchase_qty": purchase_qty,
        "dispatch_qty": dispatch_qty,
        "sales_qty": sales_qty,
        "warehouse_stock": warehouse_stock,
        "sis_stock": sis_stock,
        "total_stock": total_stock,
        "stock_in_date": None,
        "avg_stock_carrying_days": avg_stock_carrying_days,
        "no_of_counter": no_of_counter,
        "daily_planned_sale": daily_planned_sale,
        "actual_sale_through": actual_sale_through,
        "status": total_status,
        "is_total": 1
    })

def get_status(actual_sale_through, daily_planned_sale):
    if actual_sale_through >= daily_planned_sale:
        return "GREEN"
    elif actual_sale_through >= (daily_planned_sale * 0.5):
        return "YELLOW"
    else:
        return "RED"