
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("SIS Counter Sale"),
            "fieldname": "sis_counter_sale",
            "fieldtype": "Link",
            "options": "Delivery Note",
            "width": 180,
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150,
        },
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 130,
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 70,
        },
        {
            "label": _("MRP"),
            "fieldname": "mrp",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": _("INV Base Value"),
            "fieldname": "inv_base_value",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Input GST Value"),
            "fieldname": "input_gst_value",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Collectable Amount"),
            "fieldname": "collectable_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Receipts"),
            "fieldname": "receipts",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": _("GST Amount"),
            "fieldname": "gst_amount",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": _("Receipts without GST"),
            "fieldname": "receipts_without_gst",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Commission Rate (%)"),
            "fieldname": "commission_rate",
            "fieldtype": "Percent",
            "width": 150,
        },
        {
            "label": _("Commission Amount"),
            "fieldname": "commission_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    dn_items = frappe.db.sql(
        """
        SELECT
            dni.parent                  AS sis_counter_sale,
            dn.posting_date             AS date,
            dn.customer                 AS customer,
            dni.item_code               AS item_code,
            dni.qty                     AS qty,
            dni.rate                    AS mrp,
            dni.base_net_amount         AS item_net_amount,
            dn.net_total                AS dn_net_total,
            dn.grand_total              AS dn_grand_total,
            dn.name                     AS dn_name
        FROM
            `tabDelivery Note Item` dni
        INNER JOIN
            `tabDelivery Note` dn ON dn.name = dni.parent
        WHERE
            dn.docstatus IN (0, 1)
            {conditions}
        ORDER BY
            dn.posting_date, dni.parent, dni.idx
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    if not dn_items:
        return []

    gst_map     = get_gst_map(filters)
    receipt_map = get_receipt_map(filters)

    # Collect unique customers and fetch commission rate from Customer master
    customer_names = list({row.customer for row in dn_items if row.customer})
    customer_map   = get_customer_commission_map(customer_names)

    data   = []
    totals = {
        "qty":                 0,
        "mrp":                 0,
        "inv_base_value":      0,
        "input_gst_value":     0,
        "collectable_amount":  0,
        "receipts":            0,
        "gst_amount":          0,
        "receipts_without_gst": 0,
        "commission_amount":   0,
    }

    for row in dn_items:
        dn_name        = row.dn_name
        dn_net_total   = flt(row.dn_net_total)
        dn_grand_total = flt(row.dn_grand_total)
        item_net       = flt(row.item_net_amount)

        # Proportional GST for this line item
        total_dn_gst = flt(gst_map.get(dn_name, 0))
        if dn_net_total:
            item_gst = round((item_net / dn_net_total) * total_dn_gst, 2)
        else:
            item_gst = 0.0

        inv_base_value       = item_net
        input_gst_value      = item_gst
        collectable_amount   = round(inv_base_value + input_gst_value, 2)
        receipts             = flt(receipt_map.get(dn_name, dn_grand_total))
        gst_amount           = item_gst
        receipts_without_gst = round(receipts - gst_amount, 2)

        # Fetch commission_rate from Customer master
        # custom_commission_rate is a percent value e.g. 2.0 means 2%
        customer_info   = customer_map.get(row.customer, {})
        commission_rate = flt(customer_info.get("custom_commission_rate", 0))

        # Commission amount = (commission_rate / 100) * receipts_without_gst
        if commission_rate:
            commission_amount = round(
                (commission_rate / 100) * receipts_without_gst, 2
            )
        else:
            commission_amount = 0.0

        data_row = {
            "sis_counter_sale":      row.sis_counter_sale,
            "date":                  row.date,
            "customer":              row.customer,
            "item_code":             row.item_code,
            "qty":                   flt(row.qty),
            "mrp":                   flt(row.mrp),
            "inv_base_value":        inv_base_value,
            "input_gst_value":       input_gst_value,
            "collectable_amount":    collectable_amount,
            "receipts":              receipts,
            "gst_amount":            gst_amount,
            "receipts_without_gst":  receipts_without_gst,
            "commission_rate":       commission_rate,
            "commission_amount":     commission_amount,
        }

        for key in totals:
            totals[key] += flt(data_row.get(key, 0))

        data.append(data_row)

    # Total row
    data.append({
        "sis_counter_sale":      "",
        "date":                  None,
        "customer":              "",
        "item_code":             "TOTAL",
        "qty":                   round(totals["qty"], 2),
        "mrp":                   round(totals["mrp"], 2),
        "inv_base_value":        round(totals["inv_base_value"], 2),
        "input_gst_value":       round(totals["input_gst_value"], 2),
        "collectable_amount":    round(totals["collectable_amount"], 2),
        "receipts":              round(totals["receipts"], 2),
        "gst_amount":            round(totals["gst_amount"], 2),
        "receipts_without_gst":  round(totals["receipts_without_gst"], 2),
        "commission_rate":       None,
        "commission_amount":     round(totals["commission_amount"], 2),
    })

    return data


def get_customer_commission_map(customer_names):
    """
    Fetches custom_commission_rate from tabCustomer
    for all customers in a single query.

    Returns:
        {
            "Amit Collection": {
                "name": "Amit Collection",
                "custom_commission_rate": 2.0
            },
            ...
        }
    """
    if not customer_names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            name,
            custom_commission_rate
        FROM
            `tabCustomer`
        WHERE
            name IN %(customer_names)s
        """,
        {"customer_names": tuple(customer_names)},
        as_dict=True,
    )
    return {r.name: r for r in rows}


def get_gst_map(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append("dn.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("dn.posting_date <= %(to_date)s")
    if filters.get("company"):
        conditions.append("dn.company = %(company)s")

    where_clause = "AND " + " AND ".join(conditions) if conditions else ""

    rows = frappe.db.sql(
        """
        SELECT
            stc.parent               AS dn_name,
            SUM(stc.base_tax_amount) AS total_gst
        FROM
            `tabSales Taxes and Charges` stc
        INNER JOIN
            `tabDelivery Note` dn ON dn.name = stc.parent
        WHERE
            dn.docstatus IN (0, 1)
            AND (
                stc.account_head LIKE '%%CGST%%'
                OR stc.account_head LIKE '%%SGST%%'
                OR stc.account_head LIKE '%%IGST%%'
            )
            {where_clause}
        GROUP BY
            stc.parent
        """.format(where_clause=where_clause),
        filters,
        as_dict=True,
    )
    return {r.dn_name: flt(r.total_gst) for r in rows}


def get_receipt_map(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append("pe.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pe.posting_date <= %(to_date)s")
    if filters.get("company"):
        conditions.append("pe.company = %(company)s")

    where_clause = "AND " + " AND ".join(conditions) if conditions else ""

    rows = frappe.db.sql(
        """
        SELECT
            per.reference_name        AS dn_name,
            SUM(per.allocated_amount) AS total_received
        FROM
            `tabPayment Entry Reference` per
        INNER JOIN
            `tabPayment Entry` pe ON pe.name = per.parent
        WHERE
            per.reference_doctype = 'Delivery Note'
            AND pe.docstatus = 1
            {where_clause}
        GROUP BY
            per.reference_name
        """.format(where_clause=where_clause),
        filters,
        as_dict=True,
    )
    return {r.dn_name: flt(r.total_received) for r in rows}


def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append("dn.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("dn.posting_date <= %(to_date)s")
    if filters.get("customer"):
        conditions.append("dn.customer = %(customer)s")
    if filters.get("company"):
        conditions.append("dn.company = %(company)s")
    return "AND " + " AND ".join(conditions) if conditions else ""