import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):

    columns = get_columns(filters)
    data = get_data(filters)

    # =========================
    # CUSTOM TOTALS
    # =========================
    total_book_stock = 0
    total_physical_stock = 0
    total_difference = 0
    total_stock_adj_qty = 0
    total_mrp = 0
    total_wsp = 0
    total_std = 0

    for d in data:

        total_book_stock += flt(d.get("book_stock"))
        total_physical_stock += flt(d.get("physical_stock"))
        total_difference += flt(d.get("difference"))
        total_stock_adj_qty += flt(d.get("stock_adj_qty"))

        total_mrp += flt(d.get("mrp"))
        total_wsp += flt(d.get("wsp"))
        total_std += flt(d.get("std"))

    # =========================
    # TOTAL ROW
    # =========================
    data.append({

        "stock_taking": "TOTAL",

        "mrp": total_mrp,
        "wsp": total_wsp,
        "std": total_std,
        "book_stock": total_book_stock,
        "physical_stock": total_physical_stock,
        "difference": total_difference,
        "stock_adj_qty": total_stock_adj_qty
    })

    return columns, data


def get_columns(filters=None):

    columns = [

        {
            "label": "Stock Taking",
            "fieldname": "stock_taking",
            "fieldtype": "Link",
            "options": "Stock Taking",
            "width": 180
        },

        {
            "label": "Owner Site",
            "fieldname": "owner_site",
            "fieldtype": "Data",
            "width": 180
        },
        {
        "label": "Status",
        "fieldname": "status",
        "fieldtype": "Data",
        "width": 120
        },

        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180
        }
    ]

    # ✅ Item Code ke turant baad
    if filters.get("show_serial_no"):
        columns.append({
            "label": "Serial No",
            "fieldname": "serial_no",
            "fieldtype": "HTML",
            "width": 400
        })

    columns.extend([
        {
            "label": "Brand Name",
            "fieldname": "brand_name",
            "fieldtype": "Data",
            "width": 180
        },


        {
            "label": "MRP",
            "fieldname": "mrp",
            "fieldtype": "Currency",
            "width": 120
        },

        {
            "label": "STD",
            "fieldname": "std",
            "fieldtype": "Currency",
            "width": 120
        },

        {
            "label": "WSP",
            "fieldname": "wsp",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": "Silhouette",
            "fieldname": "silhouette",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Division",
            "fieldname": "division",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": "Stock Adj Date",
            "fieldname": "stock_adj_date",
            "fieldtype": "Date",
            "width": 120
        },

        {
            "label": "Plan Date",
            "fieldname": "plan_date",
            "fieldtype": "Date",
            "width": 120
        },

        {
            "label": "Plan Description",
            "fieldname": "plan_description",
            "fieldtype": "Data",
            "width": 220
        },

        {
            "label": "Count Of Pcs",
            "fieldname": "category1",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Top Fabric",
            "fieldname": "category2",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Color",
            "fieldname": "category3",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Sup Design No",
            "fieldname": "category4",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Size",
            "fieldname": "category5",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Block",
            "fieldname": "category6",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Book Stock",
            "fieldname": "book_stock",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Physical Stock",
            "fieldname": "physical_stock",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Difference",
            "fieldname": "difference",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Stock Adj Qty",
            "fieldname": "stock_adj_qty",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Stock Point",
            "fieldname": "stock_point",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180
        }
    ])

    return columns

def get_data(filters):

    conditions = []
    values = {}

    # =========================
    # FILTERS
    # =========================

    if filters.get("company"):
        conditions.append(
            "st.company = %(company)s"
        )
        values["company"] = filters.get("company")

    if filters.get("stock_taking"):
        conditions.append("st.name = %(stock_taking)s")
        values["stock_taking"] = filters.get("stock_taking")

    if filters.get("item_code"):
        conditions.append("sti.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")

    if filters.get("warehouse"):
        conditions.append("sti.warehouse = %(warehouse)s")
        values["warehouse"] = filters.get("warehouse")

    if filters.get("from_date"):
        conditions.append("st.plan_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("st.plan_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("status"):

        status_map = {
            "Draft": 0,
            "Submitted": 1,
            "Cancelled": 2
        }

        conditions.append("st.docstatus=%(docstatus)s")
        values["docstatus"] = status_map.get(
            filters.get("status")
        )

    where_conditions = ""

    if conditions:
        where_conditions = " AND " + " AND ".join(conditions)

    # return frappe.db.sql(f"""

    # SELECT

    #     st.name as stock_taking,

    #     st.company as owner_site,

    #     CASE
    #         WHEN st.docstatus=0 THEN 'Draft'
    #         WHEN st.docstatus=1 THEN 'Submitted'
    #         WHEN st.docstatus=2 THEN 'Cancelled'
    #     END as status,

    #     sti.item_code,

    # sti.is_delivered_row,

    # GROUP_CONCAT(
    #     DISTINCT REPLACE(
    #         sti.serial_no,
    #         '\n',
    #         '<br>'
    #     )
    #     SEPARATOR '<br>'
    # ) as serial_no,

    #     i.brand as brand_name,

    #     ip_mrp.price_list_rate as mrp,
    #     ip_std.price_list_rate as std,
    #     ip_wsp.price_list_rate as wsp,

    #     i.item_group as division,
    #     i.custom_silvet as silhouette,

    #     se.posting_date as stock_adj_date,

    #     st.plan_date,
    #     st.remark as plan_description,

    #     i.custom_count_of_pcs as category1,
    #     i.custom_top_fabrics as category2,
    #     i.custom_colour_name as category3,
    #     i.custom_sup_design_no as category4,
    #     i.custom_size as category5,
    #     i.custom_block as category6,

    #     ABS(COALESCE(sti.inventory,0))
    #         as book_stock,

    #     COALESCE(sti.physical_count,0)
    #         as physical_stock,

    #     COALESCE(sti.difference,0)
    #         as difference,

    #     COALESCE(SUM(sed.qty),0)
    #         as stock_adj_qty,

    #     sti.warehouse as stock_point

    # FROM `tabStock Taking` st

    # INNER JOIN `tabStock taking Items` sti
    #     ON sti.parent=st.name

    # LEFT JOIN `tabStock Entry` se
    #     ON se.custom_stock_taking=st.name
    #     AND se.docstatus=1

    # LEFT JOIN `tabStock Entry Detail` sed
    #     ON sed.parent=se.name
    #     AND sed.item_code=sti.item_code
    #     AND (
    #         sed.s_warehouse=sti.warehouse
    #         OR
    #         sed.t_warehouse=sti.warehouse
    #     )

    # LEFT JOIN `tabItem` i
    #     ON i.name=sti.item_code

    # LEFT JOIN `tabItem Price` ip_mrp
    #     ON ip_mrp.item_code=sti.item_code
    #     AND ip_mrp.price_list='MRP'

    # LEFT JOIN `tabItem Price` ip_std
    #     ON ip_std.item_code=sti.item_code
    #     AND ip_std.price_list='STD'

    # LEFT JOIN `tabItem Price` ip_wsp
    #     ON ip_wsp.item_code=sti.item_code
    #     AND ip_wsp.price_list='WSP'

    # WHERE 1=1
    # {where_conditions}

    # GROUP BY
    # st.name,
    # sti.item_code,
    # sti.warehouse,
    # sti.is_delivered_row

    # ORDER BY
    #     st.creation DESC

    # """, values, as_dict=1)
    return frappe.db.sql(f"""

    /* =========================================================
    ✅ PART 1
    ALL ITEMS FROM MATERIAL ISSUE ENTRY
    ========================================================= */

    SELECT

        st.name as stock_taking,

        st.company as owner_site,

        CASE
            WHEN st.docstatus = 0 THEN 'Draft'
            WHEN st.docstatus = 1 THEN 'Submitted'
            WHEN st.docstatus = 2 THEN 'Cancelled'
        END as status,

        sed.item_code as item_code,

        GROUP_CONCAT(
            DISTINCT REPLACE(
                COALESCE(sti.serial_no, ''),
                '\n',
                '<br>'
            )
            SEPARATOR '<br>'
        ) as serial_no,

        i.brand as brand_name,

        MAX(ip_mrp.price_list_rate) as mrp,
        MAX(ip_std.price_list_rate) as std,
        MAX(ip_wsp.price_list_rate) as wsp,

        i.item_group as division,
        i.custom_silvet as silhouette,

        MAX(se.posting_date) as stock_adj_date,

        st.plan_date,
        st.remark as plan_description,

        i.custom_count_of_pcs as category1,
        i.custom_top_fabrics as category2,
        i.custom_colour_name as category3,
        i.custom_sup_design_no as category4,
        i.custom_size as category5,
        i.custom_block as category6,

        -- ✅ BOOK STOCK
        # ABS(COALESCE(bin.actual_qty, 0))
        #     as book_stock,
        (
            SELECT sle.qty_after_transaction
            FROM `tabStock Ledger Entry` sle
            WHERE sle.item_code = sed.item_code
            AND sle.warehouse = COALESCE(
                sti.warehouse,
                sed.s_warehouse,
                sed.t_warehouse
            )
            AND sle.is_cancelled = 0
            AND sle.posting_date <= COALESCE(
                st.plan_date,
                DATE(st.creation)
            )
            ORDER BY sle.posting_date DESC, sle.posting_time DESC
            LIMIT 1
        ) as book_stock,
                         

        -- ✅ PHYSICAL STOCK
        COALESCE(SUM(sti.physical_count), 0)
            as physical_stock,

        -- ✅ DIFFERENCE
        # (
        #     ABS(COALESCE(bin.actual_qty, 0))
        #     -
        #     COALESCE(SUM(sti.physical_count), 0)
        # ) as difference,
        (
    COALESCE((
        SELECT sle.qty_after_transaction
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = sed.item_code
        AND sle.warehouse = COALESCE(
            sti.warehouse,
            sed.s_warehouse,
            sed.t_warehouse
        )
        AND sle.is_cancelled = 0
        AND sle.posting_date <= COALESCE(
            st.plan_date,
            DATE(st.creation)
        )
        ORDER BY sle.posting_date DESC, sle.posting_time DESC
        LIMIT 1
    ), 0)
    -
    COALESCE(SUM(sti.physical_count), 0)
) as difference,

    #         (
    #     COALESCE((
    #         SELECT SUM(sed_mr.qty)

    #         FROM `tabStock Entry` se_mr

    #         INNER JOIN `tabStock Entry Detail` sed_mr
    #             ON sed_mr.parent = se_mr.name

    #         WHERE se_mr.custom_stock_taking = st.name
    #         AND se_mr.stock_entry_type = 'Material Receipt'
    #         AND se_mr.docstatus IN (0,1)

    #         AND sed_mr.item_code = sed.item_code

    #         AND (
    #             sed_mr.t_warehouse = COALESCE(
    #                 sti.warehouse,
    #                 sed.s_warehouse,
    #                 sed.t_warehouse
    #             )
    #         )

    #     ), 0)

    #     -

    #     COALESCE((
    #         SELECT SUM(sed_mi.qty)

    #         FROM `tabStock Entry` se_mi

    #         INNER JOIN `tabStock Entry Detail` sed_mi
    #             ON sed_mi.parent = se_mi.name

    #         WHERE se_mi.custom_stock_taking = st.name
    #         AND se_mi.stock_entry_type = 'Material Issue'
    #         AND se_mi.docstatus IN (0,1)

    #         AND sed_mi.item_code = sed.item_code

    #         AND (
    #             sed_mi.s_warehouse = COALESCE(
    #                 sti.warehouse,
    #                 sed.s_warehouse,
    #                 sed.t_warehouse
    #             )
    #         )

    #     ), 0)

    # ) as stock_adj_qty,
    
                         -COALESCE((
    SELECT sle.qty_after_transaction
    FROM `tabStock Ledger Entry` sle
    WHERE sle.item_code = sed.item_code
    AND sle.warehouse = COALESCE(
        sti.warehouse,
        sed.s_warehouse,
        sed.t_warehouse
    )
    AND sle.is_cancelled = 0
    AND sle.posting_date <= COALESCE(
        st.plan_date,
        DATE(st.creation)
    )
    ORDER BY sle.posting_date DESC, sle.posting_time DESC
    LIMIT 1
), 0) as stock_adj_qty,

        COALESCE(
            sti.warehouse,
            sed.s_warehouse,
            sed.t_warehouse
        ) as stock_point

    FROM `tabStock Taking` st

    INNER JOIN `tabStock Entry` se
        ON se.custom_stock_taking = st.name
        AND se.stock_entry_type = 'Material Issue'
        AND se.docstatus IN (0,1)

    INNER JOIN `tabStock Entry Detail` sed
        ON sed.parent = se.name

    LEFT JOIN `tabStock taking Items` sti
        ON sti.parent = st.name
        AND sti.item_code = sed.item_code
        AND (
            sti.warehouse = sed.s_warehouse
            OR sti.warehouse = sed.t_warehouse
        )

    # LEFT JOIN `tabBin` bin
    #     ON bin.item_code = sed.item_code
    #     AND bin.warehouse = COALESCE(
    #         sti.warehouse,
    #         sed.s_warehouse,
    #         sed.t_warehouse
    #     )

    LEFT JOIN `tabItem` i
        ON i.name = sed.item_code

    LEFT JOIN `tabItem Price` ip_mrp
        ON ip_mrp.item_code = sed.item_code
        AND ip_mrp.price_list = 'MRP'

    LEFT JOIN `tabItem Price` ip_std
        ON ip_std.item_code = sed.item_code
        AND ip_std.price_list = 'STD'

    LEFT JOIN `tabItem Price` ip_wsp
        ON ip_wsp.item_code = sed.item_code
        AND ip_wsp.price_list = 'WSP'

    WHERE 1=1
    {where_conditions}

    GROUP BY
        st.name,
        sed.item_code,
        stock_point


    UNION


    /* =========================================================
    ✅ PART 2
    SCANNED ITEMS WHICH ARE MISSING
    ========================================================= */

    SELECT

        st.name as stock_taking,

        st.company as owner_site,

        CASE
            WHEN st.docstatus = 0 THEN 'Draft'
            WHEN st.docstatus = 1 THEN 'Submitted'
            WHEN st.docstatus = 2 THEN 'Cancelled'
        END as status,

        sti.item_code as item_code,

        REPLACE(
            COALESCE(sti.serial_no, ''),
            '\n',
            '<br>'
        ) as serial_no,

        i.brand as brand_name,

        ip_mrp.price_list_rate as mrp,
        ip_std.price_list_rate as std,
        ip_wsp.price_list_rate as wsp,

        i.item_group as division,
        i.custom_silvet as silhouette,

        NULL as stock_adj_date,

        st.plan_date,
        st.remark as plan_description,

        i.custom_count_of_pcs as category1,
        i.custom_top_fabrics as category2,
        i.custom_colour_name as category3,
        i.custom_sup_design_no as category4,
        i.custom_size as category5,
        i.custom_block as category6,

        # ABS(COALESCE(bin.actual_qty, 0))
        #     as book_stock,
        (
            SELECT sle.qty_after_transaction
            FROM `tabStock Ledger Entry` sle
            WHERE sle.item_code = sti.item_code
            AND sle.warehouse = sti.warehouse
            AND sle.is_cancelled = 0
            AND sle.posting_date <= COALESCE(
                st.plan_date,
                DATE(st.creation)
            )
        ORDER BY sle.posting_date DESC, sle.posting_time DESC
        LIMIT 1
        ) as book_stock,


        COALESCE(sti.physical_count, 0)
            as physical_stock,

        # (
        #     ABS(COALESCE(bin.actual_qty, 0))
        #     -
        #     COALESCE(sti.physical_count, 0)
        # ) as difference,
        (
        COALESCE((
            SELECT sle.qty_after_transaction
            FROM `tabStock Ledger Entry` sle
            WHERE sle.item_code = sti.item_code
            AND sle.warehouse = sti.warehouse
            AND sle.is_cancelled = 0
            AND sle.posting_date <= COALESCE(
                st.plan_date,
                DATE(st.creation)
            )
            ORDER BY sle.posting_date DESC, sle.posting_time DESC
            LIMIT 1
            ), 0)
            -
            COALESCE(sti.physical_count, 0)
        ) as difference,

        #0 as stock_adj_qty,
        -COALESCE((
    SELECT sle.qty_after_transaction
    FROM `tabStock Ledger Entry` sle
    WHERE sle.item_code = sti.item_code
    AND sle.warehouse = sti.warehouse
    AND sle.is_cancelled = 0
    AND sle.posting_date <= COALESCE(
        st.plan_date,
        DATE(st.creation)
    )
    ORDER BY sle.posting_date DESC, sle.posting_time DESC
    LIMIT 1
), 0) as stock_adj_qty,

        sti.warehouse as stock_point

    FROM `tabStock Taking` st

    INNER JOIN `tabStock taking Items` sti
        ON sti.parent = st.name

    # LEFT JOIN `tabBin` bin
    #     ON bin.item_code = sti.item_code
    #     AND bin.warehouse = sti.warehouse

    LEFT JOIN `tabItem` i
        ON i.name = sti.item_code

    LEFT JOIN `tabItem Price` ip_mrp
        ON ip_mrp.item_code = sti.item_code
        AND ip_mrp.price_list = 'MRP'

    LEFT JOIN `tabItem Price` ip_std
        ON ip_std.item_code = sti.item_code
        AND ip_std.price_list = 'STD'

    LEFT JOIN `tabItem Price` ip_wsp
        ON ip_wsp.item_code = sti.item_code
        AND ip_wsp.price_list = 'WSP'

    WHERE 1=1
    {where_conditions}

    AND NOT EXISTS (

        SELECT 1

        FROM `tabStock Entry` se2

        INNER JOIN `tabStock Entry Detail` sed2
            ON sed2.parent = se2.name

        WHERE se2.custom_stock_taking = st.name
        AND se2.stock_entry_type = 'Material Issue'

        AND sed2.item_code = sti.item_code
    )

    ORDER BY
        stock_taking DESC,
        item_code ASC

    """, values, as_dict=1)