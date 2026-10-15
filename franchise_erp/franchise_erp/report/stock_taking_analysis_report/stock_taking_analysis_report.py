import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    frappe.throw("EXECUTE HIT")
    # Sanitize incoming filter variations (None vs empty string "")
    clean_filters = {}
    if filters and isinstance(filters, dict):
        for k, v in filters.items():
            if v is not None and str(v).strip() != "":
                clean_filters[k] = v

    columns = get_columns(clean_filters)
    data = get_data(clean_filters)

    # =========================================================
    # RE-CALCULATE DYNAMIC TOTALS
    # =========================================================
    total_book_stock = 0
    total_physical_stock = 0
    total_difference = 0
    total_stock_adj_qty = 0
    total_mrp = 0
    total_wsp = 0
    total_std = 0

    # Ensure no duplicate totals exist in data context
    clean_data = [d for d in data if d.get("stock_taking") != "TOTAL"]

    for d in clean_data:
        total_book_stock += flt(d.get("book_stock"))
        total_physical_stock += flt(d.get("physical_stock"))
        total_difference += flt(d.get("difference"))
        total_stock_adj_qty += flt(d.get("stock_adj_qty"))
        total_mrp += flt(d.get("mrp"))
        total_wsp += flt(d.get("wsp"))
        total_std += flt(d.get("std"))

    # Append fresh summary data row
    clean_data.append({
        "stock_taking": "TOTAL",
        "mrp": total_mrp,
        "wsp": total_wsp,
        "std": total_std,
        "book_stock": total_book_stock,
        "physical_stock": total_physical_stock,
        "difference": total_difference,
        "stock_adj_qty": total_stock_adj_qty
    })

    return columns, clean_data


def get_columns(filters=None):
    columns = [
        {"label": "Stock Taking", "fieldname": "stock_taking", "fieldtype": "Link", "options": "Stock Taking", "width": 180},
        {"label": "Book Stock", "fieldname": "book_stock", "fieldtype": "Float", "width": 120},

        {"label": "Owner Site", "fieldname": "owner_site", "fieldtype": "Data", "width": 180},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Brand Name", "fieldname": "brand_name", "fieldtype": "Data", "width": 180},
        {"label": "MRP", "fieldname": "mrp", "fieldtype": "Currency", "width": 120},
        {"label": "STD", "fieldname": "std", "fieldtype": "Currency", "width": 120},
        {"label": "WSP", "fieldname": "wsp", "fieldtype": "Currency", "width": 120},
        {"label": "Silhouette", "fieldname": "silhouette", "fieldtype": "Data", "width": 150},
        {"label": "Division", "fieldname": "division", "fieldtype": "Data", "width": 150},
        {"label": "Stock Adj Date", "fieldname": "stock_adj_date", "fieldtype": "Date", "width": 120},
        {"label": "Plan Date", "fieldname": "plan_date", "fieldtype": "Date", "width": 120},
        {"label": "Plan Description", "fieldname": "plan_description", "fieldtype": "Data", "width": 220},
        {"label": "Count Of Pcs", "fieldname": "category1", "fieldtype": "Data", "width": 120},
        {"label": "Top Fabric", "fieldname": "category2", "fieldtype": "Data", "width": 120},
        {"label": "Color", "fieldname": "category3", "fieldtype": "Data", "width": 120},
        {"label": "Sup Design No", "fieldname": "category4", "fieldtype": "Data", "width": 120},
        {"label": "Size", "fieldname": "category5", "fieldtype": "Data", "width": 120},
        {"label": "Block", "fieldname": "category6", "fieldtype": "Data", "width": 120},
        {"label": "Physical Stock", "fieldname": "physical_stock", "fieldtype": "Float", "width": 120},
        {"label": "Difference", "fieldname": "difference", "fieldtype": "Float", "width": 120},
        {"label": "Stock Adj Qty", "fieldname": "stock_adj_qty", "fieldtype": "Float", "width": 120},
        {"label": "Stock Point", "fieldname": "stock_point", "fieldtype": "Link", "options": "Warehouse", "width": 180}
    ]
    return columns


def get_data(filters):
    cond_p1 = ["1=1"]
    cond_p2 = ["1=1"]
    values = {}

    # =========================================================
    # PARSING ACTIVE FILTERS
    # =========================================================
    if filters.get("stock_taking"):
        cond_p1.append("st.name = %(stock_taking)s")
        cond_p2.append("st.name = %(stock_taking)s")
        values["stock_taking"] = filters.get("stock_taking")

    if filters.get("company"):
        cond_p1.append("st.company = %(company)s")
        cond_p2.append("st.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("from_date"):
        cond_p1.append("st.plan_date >= %(from_date)s")
        cond_p2.append("st.plan_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        cond_p1.append("st.plan_date <= %(to_date)s")
        cond_p2.append("st.plan_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("status"):
        status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        if filters.get("status") in status_map:
            cond_p1.append("st.docstatus = %(docstatus)s")
            cond_p2.append("st.docstatus = %(docstatus)s")
            values["docstatus"] = status_map.get(filters.get("status"))

    if filters.get("item_code"):
        cond_p1.append("sed.item_code = %(item_code)s")
        cond_p2.append("sti.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")

    if filters.get("warehouse"):
        cond_p1.append("(sed.s_warehouse = %(warehouse)s OR sed.t_warehouse = %(warehouse)s)")
        cond_p2.append("sti.warehouse = %(warehouse)s")
        values["warehouse"] = filters.get("warehouse")

    where_p1 = " AND ".join(cond_p1)
    where_p2 = " AND ".join(cond_p2)

    # =========================================================
    # CORE DATABASE EXECUTION (GROUPED BY ITEM + WAREHOUSE)
    # =========================================================
    return frappe.db.sql(f"""
        /* PART 1: UNIFIED TRANSACTION ITEMS */
        SELECT
            st.name AS stock_taking,
            st.company AS owner_site,
            CASE
                WHEN st.docstatus = 0 THEN 'Draft'
                WHEN st.docstatus = 1 THEN 'Submitted'
                WHEN st.docstatus = 2 THEN 'Cancelled'
            END AS status,
            sed.item_code AS item_code,
            MAX(i.brand) AS brand_name,
            MAX(ip_mrp.price_list_rate) AS mrp,
            MAX(ip_std.price_list_rate) AS std,
            MAX(ip_wsp.price_list_rate) AS wsp,
            MAX(i.custom_silvet) AS silhouette,
            MAX(i.item_group) AS division,
            MAX(se.posting_date) AS stock_adj_date,
            st.plan_date,
            st.remark AS plan_description,
            MAX(i.custom_count_of_pcs) AS category1,
            MAX(i.custom_top_fabrics) AS category2,
            MAX(i.custom_colour_name) AS category3,
            MAX(i.custom_sup_design_no) AS category4,
            MAX(i.custom_size) AS category5,
            MAX(i.custom_block) AS category6,
            COALESCE(sed.s_warehouse, sed.t_warehouse, sti.warehouse) AS stock_point,
            SUM(CASE
                WHEN se.stock_entry_type = 'Material Issue' THEN -ABS(COALESCE(sed.qty, 0))
                WHEN se.stock_entry_type = 'Material Receipt' THEN ABS(COALESCE(sed.qty, 0))
                ELSE 0
            END) AS stock_adj_qty,
            MAX(COALESCE((
                SELECT b.actual_qty FROM `tabBin` b 
                WHERE b.item_code = sed.item_code 
                  AND b.warehouse = COALESCE(sed.s_warehouse, sed.t_warehouse, sti.warehouse) 
                LIMIT 1
            ), 0)) - SUM(CASE
                WHEN se.stock_entry_type = 'Material Issue' THEN -ABS(COALESCE(sed.qty, 0))
                WHEN se.stock_entry_type = 'Material Receipt' THEN ABS(COALESCE(sed.qty, 0))
                ELSE 0
            END) AS book_stock,
            SUM(COALESCE(sti.physical_count, 0)) AS physical_stock,
            (SUM(COALESCE(sti.physical_count, 0)) - (MAX(COALESCE((
                SELECT b.actual_qty FROM `tabBin` b 
                WHERE b.item_code = sed.item_code 
                  AND b.warehouse = COALESCE(sed.s_warehouse, sed.t_warehouse, sti.warehouse) 
                LIMIT 1
            ), 0)) - SUM(CASE
                WHEN se.stock_entry_type = 'Material Issue' THEN -ABS(COALESCE(sed.qty, 0))
                WHEN se.stock_entry_type = 'Material Receipt' THEN ABS(COALESCE(sed.qty, 0))
                ELSE 0
            END))) AS difference
        FROM `tabStock Taking` st
        INNER JOIN `tabStock Entry` se ON se.custom_stock_taking = st.name AND se.docstatus IN (0, 1)
        INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        LEFT JOIN `tabStock taking Items` sti ON sti.parent = st.name AND sti.item_code = sed.item_code
            AND (sti.warehouse = sed.s_warehouse OR sti.warehouse = sed.t_warehouse)
        LEFT JOIN `tabItem` i ON i.name = sed.item_code
        LEFT JOIN `tabItem Price` ip_mrp ON ip_mrp.item_code = sed.item_code AND ip_mrp.price_list = 'MRP'
        LEFT JOIN `tabItem Price` ip_std ON ip_std.item_code = sed.item_code AND ip_std.price_list = 'STD'
        LEFT JOIN `tabItem Price` ip_wsp ON ip_wsp.item_code = sed.item_code AND ip_wsp.price_list = 'WSP'
        WHERE {where_p1}
        GROUP BY st.name, sed.item_code, COALESCE(sed.s_warehouse, sed.t_warehouse, sti.warehouse)

        UNION ALL

        /* PART 2: UNADJUSTED REMAINING ITEMS */
        SELECT
            st.name AS stock_taking,
            st.company AS owner_site,
            CASE
                WHEN st.docstatus = 0 THEN 'Draft'
                WHEN st.docstatus = 1 THEN 'Submitted'
                WHEN st.docstatus = 2 THEN 'Cancelled'
            END AS status,
            sti.item_code AS item_code,
            MAX(i.brand) AS brand_name,
            MAX(ip_mrp.price_list_rate) AS mrp,
            MAX(ip_std.price_list_rate) AS std,
            MAX(ip_wsp.price_list_rate) AS wsp,
            MAX(i.custom_silvet) AS silhouette,
            MAX(i.item_group) AS division,
            NULL AS stock_adj_date,
            st.plan_date,
            st.remark AS plan_description,
            MAX(i.custom_count_of_pcs) AS category1,
            MAX(i.custom_top_fabrics) AS category2,
            MAX(i.custom_colour_name) AS category3,
            MAX(i.custom_sup_design_no) AS category4,
            MAX(i.custom_size) AS category5,
            MAX(i.custom_block) AS category6,
            sti.warehouse AS stock_point,
            0 AS stock_adj_qty,
            MAX(COALESCE((
                SELECT b.actual_qty FROM `tabBin` b WHERE b.item_code = sti.item_code AND b.warehouse = sti.warehouse LIMIT 1
            ), 0)) AS book_stock,
            SUM(COALESCE(sti.physical_count, 0)) AS physical_stock,
            (SUM(COALESCE(sti.physical_count, 0)) - MAX(COALESCE((
                SELECT b.actual_qty FROM `tabBin` b WHERE b.item_code = sti.item_code AND b.warehouse = sti.warehouse LIMIT 1
            ), 0))) AS difference
        FROM `tabStock Taking` st
        INNER JOIN `tabStock taking Items` sti ON sti.parent = st.name
        LEFT JOIN `tabItem` i ON i.name = sti.item_code
        LEFT JOIN `tabItem Price` ip_mrp ON ip_mrp.item_code = sti.item_code AND ip_mrp.price_list = 'MRP'
        LEFT JOIN `tabItem Price` ip_std ON ip_std.item_code = sti.item_code AND ip_std.price_list = 'STD'
        LEFT JOIN `tabItem Price` ip_wsp ON ip_wsp.item_code = sti.item_code AND ip_wsp.price_list = 'WSP'
        WHERE {where_p2}
          AND NOT EXISTS (
              SELECT 1 FROM `tabStock Entry` se2
              INNER JOIN `tabStock Entry Detail` sed2 ON sed2.parent = se2.name
              WHERE se2.custom_stock_taking = st.name
                AND sed2.item_code = sti.item_code
                AND COALESCE(sed2.s_warehouse, sed2.t_warehouse) = sti.warehouse
          )
        GROUP BY st.name, sti.item_code, sti.warehouse
        ORDER BY stock_taking DESC, item_code ASC
    """, values, as_dict=1)