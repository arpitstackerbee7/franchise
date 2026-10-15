
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
            "width": 200
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
            "label": "Bal Value",
            "fieldname": "bal_value",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": "Out Value",
            "fieldname": "out_value",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": "Styles",
            "fieldname": "styles",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": "SellThru Pct",
            "fieldname": "sell_thru_pct",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "label": "Avg Aging of Balance",
            "fieldname": "avg_aging",
            "fieldtype": "Float",
            "width": 160
        }
    ]


def get_data(filters):
    data = []

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

        # Purchase Receipt totals
        pr = frappe.db.sql("""
            SELECT
                COALESCE(SUM(pri.qty), 0) AS in_qty,
                COALESCE(SUM(pri.base_net_amount), 0) AS in_value,
                COUNT(
                    DISTINCT NULLIF(TRIM(i.custom_barcode_code), '')
                ) AS styles
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pri.parent = pr.name
            LEFT JOIN `tabItem` i
                ON i.name = pri.item_code
            WHERE
                pr.docstatus = 1
                AND pr.company = %s
                AND pr.posting_date BETWEEN %s AND %s
        """, (
            company,
            filters.from_date,
            filters.to_date
        ), as_dict=True)[0]

        # Delivery Note totals
        dn = frappe.db.sql("""
            SELECT
                COALESCE(SUM(dni.qty), 0) AS out_qty,
                COALESCE(SUM(dni.base_net_amount), 0) AS out_value
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
        ), as_dict=True)[0]

        # Inward and outward quantities/values cannot be negative.
        in_qty = max(pr.in_qty or 0, 0)
        out_qty = max(dn.out_qty or 0, 0)
        in_value = max(pr.in_value or 0, 0)
        out_value = max(dn.out_value or 0, 0)

        # Balance quantity CAN be negative.
        bal_qty = in_qty - out_qty

        # Balance value should not be negative.
        bal_value = max(in_value - out_value, 0)

        # Average aging based on item-wise remaining quantities.
        # Approximate calculation, not FIFO stock aging.
        aging = frappe.db.sql("""
            SELECT
                COALESCE(
                    SUM(x.remaining_qty * x.age_days)
                    / NULLIF(SUM(x.remaining_qty), 0),
                    0
                ) AS avg_aging
            FROM (
                SELECT
                    p.item_code,
                    GREATEST(
                        p.in_qty - COALESCE(d.out_qty, 0), 0
                    ) AS remaining_qty,
                    DATEDIFF(%s, p.last_pr_date) AS age_days
                FROM (
                    SELECT
                        pri.item_code,
                        SUM(pri.qty) AS in_qty,
                        MAX(pr.posting_date) AS last_pr_date
                    FROM `tabPurchase Receipt` pr
                    INNER JOIN `tabPurchase Receipt Item` pri
                        ON pri.parent = pr.name
                    WHERE
                        pr.docstatus = 1
                        AND pr.company = %s
                        AND pr.posting_date BETWEEN %s AND %s
                    GROUP BY pri.item_code
                ) p
                LEFT JOIN (
                    SELECT
                        dni.item_code,
                        SUM(dni.qty) AS out_qty
                    FROM `tabDelivery Note` dn
                    INNER JOIN `tabDelivery Note Item` dni
                        ON dni.parent = dn.name
                    WHERE
                        dn.docstatus = 1
                        AND dn.company = %s
                        AND dn.posting_date BETWEEN %s AND %s
                    GROUP BY dni.item_code
                ) d
                    ON d.item_code = p.item_code
            ) x
            WHERE x.remaining_qty > 0
        """, (
            filters.to_date,
            company,
            filters.from_date,
            filters.to_date,
            company,
            filters.from_date,
            filters.to_date
        ), as_dict=True)[0]

        # Skip stores without inward or outward activity.
        if not in_qty and not out_qty:
            continue

        # Sell Through Percentage
        sell_thru_pct = (
            (out_qty / in_qty) * 100
            if in_qty > 0 else 0
        )

        data.append({
            "store_name": store.store_name,
            "in_qty": in_qty,
            "out_qty": out_qty,
            "bal_qty": bal_qty,
            "bal_value": bal_value,
            "out_value": out_value,
            "styles": pr.styles or 0,
            "sell_thru_pct": sell_thru_pct,
            "avg_aging": round(aging.avg_aging or 0, 2)
        })

    return data
