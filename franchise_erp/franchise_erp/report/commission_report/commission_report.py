
import frappe
from frappe import _
from frappe.utils import flt
from decimal import Decimal, ROUND_HALF_UP


def R2(val):
    try:
        val = Decimal(str(val))
    except:
        val = Decimal("0")
    return float(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("SIS Counter Sale"), "fieldname": "sis_counter_sale",
         "fieldtype": "Link", "options": "Delivery Note", "width": 180},
        {"label": _("Date"), "fieldname": "date",
         "fieldtype": "Date", "width": 100},
        {"label": _("Customer"), "fieldname": "customer",
         "fieldtype": "Data", "width": 180},
        {"label": _("Agent"), "fieldname": "agent",
         "fieldtype": "Data", "width": 150},
        {"label": _("Item"), "fieldname": "item_code",
         "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": _("Qty"), "fieldname": "qty",
         "fieldtype": "Float", "width": 70},
        {"label": _("MRP"), "fieldname": "mrp",
         "fieldtype": "Currency", "width": 100},
        {"label": _("INV Base Value"), "fieldname": "inv_base_value",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Input GST Value"), "fieldname": "input_gst_value",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Collectable Amount"), "fieldname": "collectable_amount",
         "fieldtype": "Currency", "width": 150},
        {"label": _("Receipts"), "fieldname": "receipts",
         "fieldtype": "Currency", "width": 110},
        {"label": _("GST Amount"), "fieldname": "gst_amount",
         "fieldtype": "Currency", "width": 110},
        {"label": _("Receipts without GST"), "fieldname": "receipts_without_gst",
         "fieldtype": "Currency", "width": 160},
        {"label": _("Commission Rate (%)"), "fieldname": "commission_rate",
         "fieldtype": "Percent", "width": 150},
        {"label": _("Commission Amount"), "fieldname": "commission_amount",
         "fieldtype": "Currency", "width": 150},
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
            dni.price_list_rate         AS price_list_rate,
            dni.discount_percentage     AS discount_percentage,
            dni.rate                    AS item_rate,
            dni.base_net_amount         AS item_net_amount,
            dn.net_total                AS dn_net_total,
            dn.grand_total              AS dn_grand_total,
            dn.name                     AS dn_name,
            dn.company                  AS dn_company
        FROM
            `tabDelivery Note Item` dni
        INNER JOIN
            `tabDelivery Note` dn ON dn.name = dni.parent
        WHERE
            dn.docstatus = 1
            {conditions}
        ORDER BY
            dn.posting_date, dni.parent, dni.idx
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    if not dn_items:
        return []

    # FIX 7: receipt_map has NO date filter — payments made outside the report
    # window (e.g. advance payments, late payments) are still correctly matched
    receipt_map = get_receipt_map_no_date_filter()
    gst_map     = get_gst_map(filters)

    customer_names    = list({row.customer for row in dn_items if row.customer})
    customer_map      = get_customer_commission_map(customer_names)

    dn_companies      = list({row.dn_company for row in dn_items if row.dn_company})
    company_agent_map = get_company_agent_map(dn_companies)
    sis_margin_map    = get_sis_margin_map(dn_companies)

    item_codes = list({row.item_code for row in dn_items if row.item_code})

    item_gst_map = {}
    for company in dn_companies:
        for item_code in item_codes:
            key = (item_code, company)
            rows = frappe.db.sql("""
                SELECT
                    pri.custom_single_item_rate AS single_item_rate,
                    pri.custom_single_item_input_gst_amount AS gst_amount
                FROM `tabPurchase Receipt Item` pri
                JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
                WHERE pri.item_code = %s AND pr.company = %s AND pr.docstatus = 1
                ORDER BY pr.posting_date DESC, pr.posting_time DESC, pri.creation DESC
                LIMIT 1
            """, (item_code, company), as_dict=True)
            if rows and rows[0].gst_amount:
                item_gst_map[key] = {
                    "gst_amount":       Decimal(str(rows[0].gst_amount or 0)),
                    "single_item_rate": Decimal(str(rows[0].single_item_rate or 0))
                }

    output_gst_rate_map = {
        company: get_output_gst_min_net_rate(company)
        for company in dn_companies
    }

    data   = []
    totals = {
        "qty":                  0,
        "mrp":                  0,
        "inv_base_value":       0,
        "input_gst_value":      0,
        "collectable_amount":   0,
        "receipts":             0,
        "gst_amount":           0,
        "receipts_without_gst": 0,
        "commission_amount":    0,
    }

    for row in dn_items:
        dn_name        = row.dn_name
        dn_net_total   = flt(row.dn_net_total)
        item_net       = flt(row.item_net_amount)

        qty             = flt(row.qty)
        price_list_rate = flt(row.price_list_rate) or abs(flt(row.item_rate))
        discount_pct    = flt(row.discount_percentage)
        item_rate       = flt(row.item_rate)

        # FIX 2: Skip zero-MRP items entirely — no commission to calculate
        if item_rate == 0 or price_list_rate == 0:
            continue

        # MRP = price_list_rate * qty  (negative for returns because qty<0)
        mrp = R2(price_list_rate * qty)

        sis_margin   = sis_margin_map.get(row.dn_company, {})
        fresh_margin = Decimal(str(sis_margin.get("fresh_margin", 28)))
        disc_margin  = Decimal(str(sis_margin.get("discounted_margin", 23)))
        margin_pct   = disc_margin if discount_pct > 0 else fresh_margin

        # Use abs(item_rate) for GST-rate threshold — returns have negative rate
        output_gst_min_net_rate = flt(output_gst_rate_map.get(row.dn_company, 2625))
        gst_rate = Decimal("0.05") if abs(item_rate) <= output_gst_min_net_rate else Decimal("0.18")

        # sale is negative for return DNs (item_rate > 0, qty < 0 in Frappe)
        sale   = Decimal(str(item_rate)) * Decimal(str(qty))
        ogst_v = (sale * gst_rate / (1 + gst_rate)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        net   = sale - ogst_v
        mar_v = (sale * margin_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        inv_base_value = float(
            (net - mar_v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        # Input GST: always stored as positive in Purchase Receipt.
        # For normal sales  → positive input_gst
        # For return sales  → positive input_gst (it's a recoverable credit)
        pr_gst              = item_gst_map.get((row.item_code, row.dn_company), {})
        gst_amount_per_item = pr_gst.get("gst_amount", Decimal("0"))

        if gst_amount_per_item == 0:
            # Fallback: compute from inv_base_value using abs so it stays positive
            item_gst = float(
                (abs(Decimal(str(inv_base_value))) * gst_rate).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )
        else:
            # Purchase-receipt GST is always stored positive; keep it positive
            item_gst = float(
                gst_amount_per_item.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

        input_gst_value    = item_gst
        collectable_amount = R2(inv_base_value + input_gst_value)

        if dn_name in receipt_map:
            total_receipts = flt(receipt_map.get(dn_name))
            if dn_net_total:
                receipts = R2((item_net / dn_net_total) * total_receipts)
            else:
                receipts = total_receipts
        else:
            # No payment found — use collectable amount as receipts
            receipts = collectable_amount

        gst_amount           = item_gst
        receipts_without_gst = R2(receipts - gst_amount)

        comp_info       = company_agent_map.get(row.dn_company, {})
        agent           = comp_info.get("custom_agent") or ""
        commission_rate = flt(comp_info.get("custom_commission_rate", 0))

        commission_amount = R2((commission_rate / 100) * receipts_without_gst) if commission_rate else 0.0

        data_row = {
            "sis_counter_sale":     row.sis_counter_sale,
            "date":                 row.date,
            "customer":             row.dn_company,
            "agent":                agent,
            "item_code":            row.item_code,
            "qty":                  qty,
            "mrp":                  mrp,
            "inv_base_value":       inv_base_value,
            "input_gst_value":      input_gst_value,
            "collectable_amount":   collectable_amount,
            "receipts":             receipts,
            "gst_amount":           gst_amount,
            "receipts_without_gst": receipts_without_gst,
            "commission_rate":      commission_rate,
            "commission_amount":    commission_amount,
        }

        for key in totals:
            totals[key] += flt(data_row.get(key, 0))

        data.append(data_row)

    # Total row — all numeric columns summed
    data.append({
        "sis_counter_sale":     "",
        "date":                 None,
        "customer":             "",
        "agent":                "",
        "item_code":            "TOTAL",
        "qty":                  R2(totals["qty"]),
        "mrp":                  R2(totals["mrp"]),
        "inv_base_value":       R2(totals["inv_base_value"]),
        "input_gst_value":      R2(totals["input_gst_value"]),
        "collectable_amount":   R2(totals["collectable_amount"]),
        "receipts":             R2(totals["receipts"]),
        "gst_amount":           R2(totals["gst_amount"]),
        "receipts_without_gst": R2(totals["receipts_without_gst"]),
        "commission_rate":      None,
        "commission_amount":    R2(totals["commission_amount"]),
    })

    return data


# ── helpers ────────────────────────────────────────────────────────────────

def get_customer_commission_map(customer_names):
    if not customer_names:
        return {}
    rows = frappe.db.sql(
        """
        SELECT name, custom_agent, custom_commission_rate
        FROM `tabCustomer`
        WHERE name IN %(customer_names)s
        """,
        {"customer_names": tuple(customer_names)},
        as_dict=True,
    )
    return {r.name: r for r in rows}


def get_sis_margin_map(company_names):
    if not company_names:
        return {}
    result = {}
    for company in company_names:
        rows = frappe.db.sql("""
            SELECT company, fresh_margin, discounted_margin
            FROM `tabSIS Configuration`
            WHERE REPLACE(LOWER(company), '-', '') LIKE %(like)s
            LIMIT 1
        """, {"like": "%" + company.lower().replace("-", "") + "%"}, as_dict=True)
        if rows:
            result[company] = rows[0]
    return result


def get_output_gst_min_net_rate(company):
    if not company:
        return 2625
    val = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        "output_gst_min_net_rate"
    )
    return flt(val) if val else 2625


def get_gst_map(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append("dn.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("dn.posting_date <= %(to_date)s")
    where_clause = "AND " + " AND ".join(conditions) if conditions else ""
    rows = frappe.db.sql(
        """
        SELECT
            stc.parent               AS dn_name,
            SUM(stc.base_tax_amount) AS total_gst
        FROM `tabSales Taxes and Charges` stc
        INNER JOIN `tabDelivery Note` dn ON dn.name = stc.parent
        WHERE
            dn.docstatus = 1
            AND (
                stc.account_head LIKE '%%CGST%%'
                OR stc.account_head LIKE '%%SGST%%'
                OR stc.account_head LIKE '%%IGST%%'
            )
            {where_clause}
        GROUP BY stc.parent
        """.format(where_clause=where_clause),
        filters,
        as_dict=True,
    )
    return {r.dn_name: flt(r.total_gst) for r in rows}


def get_receipt_map_no_date_filter():
    """
    Fetches ALL payments linked to Delivery Notes without any date restriction.

    Why no date filter: the original receipt_map filtered by payment posting_date,
    which caused payments made outside the report date window (advance payments or
    late payments) to be missed.  When missed, the code fell back to using
    collectable_amount as receipts, which is incorrect.
    """
    rows = frappe.db.sql(
        """
        SELECT
            per.reference_name        AS dn_name,
            SUM(per.allocated_amount) AS total_received
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE
            per.reference_doctype = 'Delivery Note'
            AND pe.docstatus = 1
        GROUP BY per.reference_name
        """,
        as_dict=True,
    )
    return {r.dn_name: flt(r.total_received) for r in rows}


def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append("dn.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("dn.posting_date <= %(to_date)s")
    # FIX 5: Single company filter — removed duplicate "customer" key that
    # also mapped to dn.company and caused conflicting WHERE clauses
    if filters.get("company"):
        conditions.append("dn.company = %(company)s")
    # FIX 6: Agent filter — apply REPLACE on BOTH sides so dash/case differences
    # between tabCompany and tabCustomer names are handled correctly
    if filters.get("agent"):
        conditions.append(
            "REPLACE(LOWER(dn.company), '-', '') IN ("
            "  SELECT REPLACE(LOWER(name), '-', '') FROM `tabCustomer`"
            "  WHERE custom_agent = %(agent)s"
            ")"
        )
    conditions.append("dn.company != 'TZU Lifestyle Private Limited'")
    return "AND " + " AND ".join(conditions) if conditions else ""


def get_company_agent_map(company_names):
    if not company_names:
        return {}
    result = {}
    for company in company_names:
        rows = frappe.db.sql("""
            SELECT name, custom_agent, custom_commission_rate
            FROM `tabCustomer`
            WHERE REPLACE(LOWER(name), '-', '') LIKE %(like)s
            LIMIT 1
        """, {"like": "%" + company.lower().replace("-", "") + "%"}, as_dict=True)
        if rows:
            result[company] = rows[0]
    return result


def get_item_input_gst_map(item_codes, company):
    if not item_codes:
        return {}
    result = {}
    for item_code in item_codes:
        rows = frappe.db.sql("""
            SELECT
                pri.custom_single_item_rate AS single_item_rate,
                pri.custom_single_item_input_gst_amount AS gst_amount
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE
                pri.item_code = %s
                AND pr.company = %s
                AND pr.docstatus = 1
            ORDER BY
                pr.posting_date DESC,
                pr.posting_time DESC,
                pri.creation DESC
            LIMIT 1
        """, (item_code, company), as_dict=True)
        if rows and rows[0].gst_amount:
            result[item_code] = {
                "gst_amount":       Decimal(str(rows[0].gst_amount or 0)),
                "single_item_rate": Decimal(str(rows[0].single_item_rate or 0))
            }
    return result