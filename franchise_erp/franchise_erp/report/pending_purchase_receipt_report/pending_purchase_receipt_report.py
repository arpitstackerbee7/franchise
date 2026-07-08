# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Source Site",
            "fieldname": "company",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": "Supplier",
            "fieldname": "supplier",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "GRC No. (Doc No.)",
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 180,
        },
        {
            "label": "GRC Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Qty",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": "Against PO Detail",
            "fieldname": "purchase_order",
            "fieldtype": "Data",
            "width": 220,
        },
    ]


def get_data(filters):
    filters = filters or {}

    conditions = ""

    if filters.get("company"):
        conditions += " AND pr.company = %(company)s"

    if filters.get("supplier"):
        conditions += " AND pr.supplier = %(supplier)s"

    if filters.get("from_date"):
        conditions += " AND pr.posting_date >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND pr.posting_date <= %(to_date)s"

    records = frappe.db.sql(
        f"""
        SELECT
            pr.company,
            pr.supplier,
            pr.name AS purchase_receipt,
            pr.posting_date,
            SUM(pri.qty) AS qty,
            pr.grand_total AS amount,
            GROUP_CONCAT(
                DISTINCT IFNULL(pri.purchase_order, '')
                SEPARATOR ', '
            ) AS purchase_order
        FROM `tabPurchase Receipt` pr
        INNER JOIN `tabPurchase Receipt Item` pri
            ON pri.parent = pr.name
        WHERE
            pr.docstatus = 1
            AND pr.per_billed < 100
            {conditions}
        GROUP BY
            pr.company,
            pr.supplier,
            pr.name,
            pr.posting_date,
            pr.grand_total
        ORDER BY
            pr.company,
            pr.supplier,
            pr.posting_date,
            pr.name
        """,
        filters,
        as_dict=True,
    )

    data = []

    current_company = None
    current_supplier = None

    company_qty = 0
    company_amount = 0

    grand_qty = 0
    grand_amount = 0

    for row in records:

        # Company Heading
        if current_company != row.company:

            if current_company:
                data.append({
                    "company": "",
                    "supplier": "<b>Site Total</b>",
                    "purchase_receipt": "",
                    "posting_date": "",
                    "qty": company_qty,
                    "amount": company_amount,
                    "purchase_order": ""
                })

            current_company = row.company
            current_supplier = None

            company_qty = 0
            company_amount = 0

            data.append({
                "company": f"<b>Source Site : {row.company}</b>",
                "supplier": "",
                "purchase_receipt": "",
                "posting_date": "",
                "qty": None,
                "amount": None,
                "purchase_order": ""
            })

        # Supplier Heading
        if current_supplier != row.supplier:

            current_supplier = row.supplier

            data.append({
                "company": "",
                "supplier": f"<b>{row.supplier}</b>",
                "purchase_receipt": "",
                "posting_date": "",
                "qty": None,
                "amount": None,
                "purchase_order": ""
            })

        # Purchase Receipt Row
        data.append({
            "company": "",
            "supplier": "",
            "purchase_receipt": row.purchase_receipt,
            "posting_date": row.posting_date,
            "qty": flt(row.qty),
            "amount": flt(row.amount),
            "purchase_order": row.purchase_order,
        })

        company_qty += flt(row.qty)
        company_amount += flt(row.amount)

        grand_qty += flt(row.qty)
        grand_amount += flt(row.amount)

    # Last Company Total
    if current_company:
        data.append({
            "company": "",
            "supplier": "<b>Site Total</b>",
            "purchase_receipt": "",
            "posting_date": "",
            "qty": company_qty,
            "amount": company_amount,
            "purchase_order": ""
        })

    # Grand Total
    data.append({
        "company": "",
        "supplier": "<b>Grand Total</b>",
        "purchase_receipt": "",
        "posting_date": "",
        "qty": grand_qty,
        "amount": grand_amount,
        "purchase_order": ""
    })

    return data