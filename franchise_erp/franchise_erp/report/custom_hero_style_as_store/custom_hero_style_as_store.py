
# Copyright (c) 2026, Franchise Erp and contributors

import frappe
from frappe.utils import getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("Please select From Date and To Date.")

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw("From Date cannot be after To Date.")

    return get_columns(), get_data(filters)


def get_columns():
    return [
        {
            "label": "Store Name",
            "fieldname": "store_name",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 220
        },
        {
            "label": "Style",
            "fieldname": "style",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "In Qty",
            "fieldname": "in_qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": "Out Qty",
            "fieldname": "out_qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": "Bal Qty",
            "fieldname": "bal_qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": "SellThru Pct",
            "fieldname": "sell_thru_pct",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "label": "Hero Style Revenue",
            "fieldname": "hero_style_revenue",
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "label": "Store Total Revenue",
            "fieldname": "store_total_revenue",
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "label": "Hero Style Share of Store Revenue Pct",
            "fieldname": "hero_style_share",
            "fieldtype": "Percent",
            "width": 220
        }
    ]


def get_data(filters):
    data = []

    # Each Customer is treated as a store.
    # Its represents_company is matched with PR/DN company.
    stores = frappe.db.sql("""
        SELECT
            c.name AS store_name,
            c.represents_company AS company
        FROM `tabCustomer` c
        WHERE IFNULL(c.represents_company, '') != ''
        ORDER BY c.name
    """, as_dict=True)

    for store in stores:
        company = store.company

        # Store's total revenue from submitted Delivery Notes.
        store_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(dni.base_net_amount), 0)
            FROM `tabDelivery Note` dn
            INNER JOIN `tabDelivery Note Item` dni
                ON dni.parent = dn.name
            WHERE
                dn.docstatus = 1
                AND dn.company = %s
                AND dn.posting_date BETWEEN %s AND %s
        """, (
            company,
            filters.from_date,
            filters.to_date
        ))[0][0] or 0

        # Aggregate PR quantity by style.
        purchase_rows = frappe.db.sql("""
            SELECT
                TRIM(i.custom_barcode_code) AS style,
                SUM(pri.qty) AS in_qty
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pri.parent = pr.name
            INNER JOIN `tabItem` i
                ON i.name = pri.item_code
            WHERE
                pr.docstatus = 1
                AND pr.company = %s
                AND pr.posting_date BETWEEN %s AND %s
                AND IFNULL(TRIM(i.custom_barcode_code), '') != ''
            GROUP BY TRIM(i.custom_barcode_code)
        """, (
            company,
            filters.from_date,
            filters.to_date
        ), as_dict=True)

        in_qty_by_style = {
            row.style: row.in_qty or 0
            for row in purchase_rows
        }

        # Aggregate DN quantity and revenue by style.
        sales_rows = frappe.db.sql("""
            SELECT
                TRIM(i.custom_barcode_code) AS style,
                SUM(dni.qty) AS out_qty,
                SUM(dni.base_net_amount) AS revenue
            FROM `tabDelivery Note` dn
            INNER JOIN `tabDelivery Note Item` dni
                ON dni.parent = dn.name
            INNER JOIN `tabItem` i
                ON i.name = dni.item_code
            WHERE
                dn.docstatus = 1
                AND dn.company = %s
                AND dn.posting_date BETWEEN %s AND %s
                AND IFNULL(TRIM(i.custom_barcode_code), '') != ''
            GROUP BY TRIM(i.custom_barcode_code)
            ORDER BY SUM(dni.qty) DESC, TRIM(i.custom_barcode_code) ASC
        """, (
            company,
            filters.from_date,
            filters.to_date
        ), as_dict=True)

        # Hero Style = style with the highest Out Qty.
        if not sales_rows:
            continue

        hero = sales_rows[0]

        style = hero.style
        in_qty = in_qty_by_style.get(style, 0)
        out_qty = hero.out_qty or 0
        hero_revenue = hero.revenue or 0

        # Keep displayed balance non-negative.
        bal_qty = max(in_qty - out_qty, 0)

        sell_thru_pct = (
            out_qty / in_qty * 100
            if in_qty > 0 else 0
        )

        hero_share = (
            hero_revenue / store_revenue * 100
            if store_revenue > 0 else 0
        )

        data.append({
            "store_name": store.store_name,
            "style": style,
            "in_qty": in_qty,
            "out_qty": out_qty,
            "bal_qty": bal_qty,
            "sell_thru_pct": sell_thru_pct,
            "hero_style_revenue": hero_revenue,
            "store_total_revenue": store_revenue,
            "hero_style_share": hero_share
        })

    # Sort stores by total revenue, highest first.
    data.sort(
        key=lambda row: row["store_total_revenue"],
        reverse=True
    )

    return data
