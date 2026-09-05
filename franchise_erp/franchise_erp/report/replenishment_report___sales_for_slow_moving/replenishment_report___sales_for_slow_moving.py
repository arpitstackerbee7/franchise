import frappe
from frappe.utils import getdate, add_days, flt


COMPANY = "TZU Lifestyle Private Limited"

# Default threshold
SLOW_MOVING_THRESHOLD = 30


# ============================================================
# EXECUTE
# ============================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()

    data = get_data(filters)

    return columns, data


# ============================================================
# VALIDATE FILTERS
# ============================================================

def validate_filters(filters):

    if not filters.get("from_date"):
        frappe.throw("From Date is mandatory")

    if not filters.get("to_date"):
        frappe.throw("To Date is mandatory")

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    if from_date > to_date:
        frappe.throw(
            "From Date cannot be greater than To Date"
        )

    operator = filters.get(
        "stock_movement_operator"
    )

    movement_value = filters.get(
        "stock_movement_value"
    )

    if operator and movement_value in (None, ""):

        frappe.throw(
            "Please enter Stock Movement %"
        )


# ============================================================
# COLUMNS
# ============================================================

def get_columns():

    return [

        # ----------------------------------------------------
        # BASIC ITEM INFORMATION
        # ----------------------------------------------------

        {
            "label": "Style",
            "fieldname": "style",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "HSN/SAC",
            "fieldname": "hsn_sac",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Brand",
            "fieldname": "brand",
            "fieldtype": "Link",
            "options": "Brand",
            "width": 120
        },

        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180
        },

        {
            "label": "Item Name",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180
        },

        {
            "label": "Division / Item Group",
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 150
        },

        # ----------------------------------------------------
        # ALL ITEM ATTRIBUTES
        # ----------------------------------------------------

        {
            "label": "Count Of Pcs",
            "fieldname": "count_of_pcs",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Colour Name",
            "fieldname": "colour_name",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Season",
            "fieldname": "season",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Top Fabrics",
            "fieldname": "top_fabrics",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Top Lining",
            "fieldname": "top_lining",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Bottom Fabric",
            "fieldname": "bottom_fabric",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Bottom Lining",
            "fieldname": "bottom_lining",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Dupatta Fabric",
            "fieldname": "dupatta_fabric",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Dupatta Embalishment",
            "fieldname": "dupatta_embalishment",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": "Dupatta Width",
            "fieldname": "dupatta_width",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Block",
            "fieldname": "block",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Neck Line",
            "fieldname": "neck_line",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Sleeve Length",
            "fieldname": "sleeve_length",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Bottom Type",
            "fieldname": "bottom_type",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Bottom Length Outseam",
            "fieldname": "bottom_length_outseam",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Set Qty",
            "fieldname": "set_qty",
            "fieldtype": "Data",
            "width": 90
        },

        {
            "label": "Top Fabric Type",
            "fieldname": "top_fabric_type",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": "Top Embalishment",
            "fieldname": "top_embalishment",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Bottom Fabric Type",
            "fieldname": "bottom_fabric_type",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Bottom Embalishment",
            "fieldname": "bottom_embalishment",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Dupatta Fabric Type",
            "fieldname": "dupatta_fabric_type",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Dupatta Length",
            "fieldname": "dupatta_length",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Sup Design No.",
            "fieldname": "sup_design_no",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Size",
            "fieldname": "size",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Sleeves Type",
            "fieldname": "sleeves_type",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": "Top Length",
            "fieldname": "top_length",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Bottom Length Inseam",
            "fieldname": "bottom_length_inseam",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": "Waist",
            "fieldname": "waist",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": "Mfg. Date",
            "fieldname": "mfg_date",
            "fieldtype": "Date",
            "width": 110
        },

        {
            "label": "Silhouette",
            "fieldname": "silhouette",
            "fieldtype": "Data",
            "width": 110
        },

        {
            "label": "Departments",
            "fieldname": "departments",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": "Group Collection",
            "fieldname": "group_collection",
            "fieldtype": "Data",
            "width": 150
        },

        # ----------------------------------------------------
        # STOCK / SALES
        # ----------------------------------------------------

        {
            "label": "Stock In Date",
            "fieldname": "stock_in_date",
            "fieldtype": "Date",
            "width": 110
        },

        {
            "label": "Purchase Received Qty",
            "fieldname": "purchase_received_qty",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "Opening SIS Stock",
            "fieldname": "opening_sis_stock",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Stock Available",
            "fieldname": "stock_available",
            "fieldtype": "Float",
            "width": 120
        },

        {
            "label": "Sale Quantity",
            "fieldname": "sales_qty",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": "Stock at SIS Counter",
            "fieldname": "sis_stock",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "Stock Movement Qty",
            "fieldname": "stock_movement_qty",
            "fieldtype": "Float",
            "width": 130
        },

        {
            "label": "Stock Movement %",
            "fieldname": "stock_movement_percent",
            "fieldtype": "Percent",
            "width": 120
        },

        {
            "label": "Average Stock",
            "fieldname": "average_stock",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": "Average Stock Movement %",
            "fieldname": "average_stock_movement_percent",
            "fieldtype": "Percent",
            "width": 150
        },

        {
            "label": "Slow Moving",
            "fieldname": "slow_moving",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):

    # ========================================================
    # ITEM FILTERS
    # ========================================================

    item_filters = {
        "disabled": 0
    }

    if filters.get("brand"):
        item_filters["brand"] = filters.get("brand")

    if filters.get("item_code"):
        item_filters["name"] = filters.get("item_code")

    # ========================================================
    # ITEM FIELDS
    # ========================================================

    item_meta = frappe.get_meta("Item")

    item_fields = [
        "name",
        "item_name",
        "item_group",
        "brand",

        "custom_style",

        "custom_count_of_pcs",
        "custom_colour_name",
        "custom_season",
        "custom_top_fabrics",
        "custom_top_lining",
        "custom_bottom_fabric",
        "custom_bottom_lining",
        "custom_dupatta_fabric",
        "custom_dupatta_embalishment",
        "custom_dupatta_width",
        "custom_block",
        "custom_neck_line",
        "custom_sleeve_length",
        "custom_bottom_type",
        "custom_bottom_length_outseam",
        "custom_set_qty",
        "custom_top_fabric_type",
        "custom_top_embalishment",
        "custom_bottom_fabric_type",
        "custom_bottom_embalishment",
        "custom_dupatta_fabric_type",
        "custom_dupatta_length",
        "custom_sup_design_no",
        "custom_size",
        "custom_sleeves_type",
        "custom_top_length",
        "custom_bottom_length_inseam",
        "custom_waist",
        "custom_mfg_date",
        "custom_silhouette",
        "custom_departments",
        "custom_group_collection",

        "custom_division"
    ]

    # ========================================================
    # ONLY EXISTING ITEM FIELDS
    # ========================================================

    item_fields = [
        field
        for field in item_fields
        if field == "name" or item_meta.has_field(field)
    ]

    # HSN/SAC
    if item_meta.has_field("gst_hsn_code"):
        item_fields.append("gst_hsn_code")

    # ========================================================
    # ITEM LIMIT
    # ========================================================

    item_limit = flt(filters.get("item_limit"))

    if item_limit > 0:

        items = frappe.get_all(
            "Item",
            filters=item_filters,
            fields=item_fields,
            order_by="custom_barcode_code asc, item_code asc",
            limit_page_length=int(item_limit)
        )

    else:

        items = frappe.get_all(
            "Item",
            filters=item_filters,
            fields=item_fields,
            order_by="custom_barcode_code asc, item_code asc"
        )

    # ========================================================
    # DATE FILTERS
    # ========================================================

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    opening_date = add_days(from_date, -1)

    # ========================================================
    # RESULT DATA
    # ========================================================

    data = []

    # ========================================================
    # LOOP ITEMS
    # ========================================================

    for item in items:

        item_code = item.name

        # ----------------------------------------------------
        # STYLE FILTER
        # ----------------------------------------------------

        if filters.get("style"):

            style_value = (
                item.get("custom_style")
                or ""
            )

            if style_value != filters.get("style"):

                continue

        # ----------------------------------------------------
        # PURCHASE RECEIVED QTY
        # ----------------------------------------------------

        purchase_received_qty = get_purchase_received_qty(
            item_code,
            from_date,
            to_date
        )

        # ----------------------------------------------------
        # STOCK IN DATE
        # ----------------------------------------------------

        stock_in_date = get_stock_in_date(
            item_code,
            to_date
        )

        # ----------------------------------------------------
        # OPENING SIS STOCK
        # ----------------------------------------------------

        opening_sis_stock = get_sis_stock(
            item_code,
            opening_date
        )

        # ----------------------------------------------------
        # CURRENT SIS STOCK
        # ----------------------------------------------------

        sis_stock = get_sis_stock(
            item_code,
            to_date
        )

        # ----------------------------------------------------
        # SALES QTY
        # ----------------------------------------------------

        sales_qty = get_sales_qty(
            item_code,
            from_date,
            to_date
        )

        # ====================================================
        # STOCK CALCULATIONS
        # ====================================================

        stock_available = (
            opening_sis_stock
            + purchase_received_qty
        )

        stock_movement_qty = sales_qty

        if stock_available > 0:

            stock_movement_percent = (
                sales_qty
                / stock_available
                * 100
            )

        else:

            stock_movement_percent = 0

        # ----------------------------------------------------
        # AVERAGE STOCK
        # ----------------------------------------------------

        average_stock = (
            opening_sis_stock
            + sis_stock
        ) / 2

        # ----------------------------------------------------
        # AVERAGE STOCK MOVEMENT %
        # ----------------------------------------------------

        if average_stock > 0:

            average_stock_movement_percent = (
                sales_qty
                / average_stock
                * 100
            )

        else:

            average_stock_movement_percent = 0

        # ----------------------------------------------------
        # SLOW MOVING
        # ----------------------------------------------------

        if (
            stock_movement_percent
            < SLOW_MOVING_THRESHOLD
        ):

            slow_moving = "YES"

        else:

            slow_moving = "NO"

        # ====================================================
        # STOCK MOVEMENT FILTER
        # ====================================================

        operator = filters.get(
            "stock_movement_operator"
        )

        movement_value = flt(
            filters.get("stock_movement_value")
        )

        if operator:

            movement = flt(
                stock_movement_percent
            )

            condition = False

            if operator == "<":
                condition = movement < movement_value

            elif operator == "<=":
                condition = movement <= movement_value

            elif operator == "=":
                condition = movement == movement_value

            elif operator == ">=":
                condition = movement >= movement_value

            elif operator == ">":
                condition = movement > movement_value

            if not condition:
                continue

        # ====================================================
        # BUILD ROW
        # ====================================================

        row = {

            # ------------------------------------------------
            # ITEM INFORMATION
            # ------------------------------------------------

            "style": item.get(
                "custom_style"
            ),

            "hsn_sac": item.get(
                "gst_hsn_code"
            ),

            "brand": item.get(
                "brand"
            ),

            "item_code": item_code,

            "item_name": item.get(
                "item_name"
            ),

            "division": item.get(
                "custom_division"
            ),

            "item_group": item.get(
                "item_group"
            ),

            # ------------------------------------------------
            # ITEM ATTRIBUTES
            # ------------------------------------------------

            "count_of_pcs": item.get(
                "custom_count_of_pcs"
            ),

            "colour_name": item.get(
                "custom_colour_name"
            ),

            "season": item.get(
                "custom_season"
            ),

            "top_fabrics": item.get(
                "custom_top_fabrics"
            ),

            "top_lining": item.get(
                "custom_top_lining"
            ),

            "bottom_fabric": item.get(
                "custom_bottom_fabric"
            ),

            "bottom_lining": item.get(
                "custom_bottom_lining"
            ),

            "dupatta_fabric": item.get(
                "custom_dupatta_fabric"
            ),

            "dupatta_embalishment": item.get(
                "custom_dupatta_embalishment"
            ),

            "dupatta_width": item.get(
                "custom_dupatta_width"
            ),

            "block": item.get(
                "custom_block"
            ),

            "neck_line": item.get(
                "custom_neck_line"
            ),

            "sleeve_length": item.get(
                "custom_sleeve_length"
            ),

            "bottom_type": item.get(
                "custom_bottom_type"
            ),

            "bottom_length_outseam": item.get(
                "custom_bottom_length_outseam"
            ),

            "set_qty": item.get(
                "custom_set_qty"
            ),

            "top_fabric_type": item.get(
                "custom_top_fabric_type"
            ),

            "top_embalishment": item.get(
                "custom_top_embalishment"
            ),

            "bottom_fabric_type": item.get(
                "custom_bottom_fabric_type"
            ),

            "bottom_embalishment": item.get(
                "custom_bottom_embalishment"
            ),

            "dupatta_fabric_type": item.get(
                "custom_dupatta_fabric_type"
            ),

            "dupatta_length": item.get(
                "custom_dupatta_length"
            ),

            "sup_design_no": item.get(
                "custom_sup_design_no"
            ),

            "size": item.get(
                "custom_size"
            ),

            "sleeves_type": item.get(
                "custom_sleeves_type"
            ),

            "top_length": item.get(
                "custom_top_length"
            ),

            "bottom_length_inseam": item.get(
                "custom_bottom_length_inseam"
            ),

            "waist": item.get(
                "custom_waist"
            ),

            "mfg_date": item.get(
                "custom_mfg_date"
            ),

            "silhouette": item.get(
                "custom_silhouette"
            ),

            "departments": item.get(
                "custom_departments"
            ),

            "group_collection": item.get(
                "custom_group_collection"
            ),

            # ------------------------------------------------
            # STOCK / SALES
            # ------------------------------------------------

            "stock_in_date": stock_in_date,

            "purchase_received_qty": purchase_received_qty,

            "opening_sis_stock": opening_sis_stock,

            "stock_available": stock_available,

            "sales_qty": sales_qty,

            "sis_stock": sis_stock,

            "stock_movement_qty": stock_movement_qty,

            "stock_movement_percent": stock_movement_percent,

            "average_stock": average_stock,

            "average_stock_movement_percent": (
                average_stock_movement_percent
            ),

            "slow_moving": slow_moving
        }

        data.append(row)

        # ========================================================
    # SORTING
    # ========================================================

    sort_order = (
        filters.get("sort_order") or "DESC"
    ).upper()

    reverse_sort = sort_order == "DESC"

    def sort_key(row):

        # ----------------------------------------------------
        # STOCK IN DATE
        # ----------------------------------------------------

        stock_date = row.get("stock_in_date")

        if stock_date:

            try:
                date_value = str(
                    getdate(stock_date)
                )
            except Exception:
                date_value = "9999-12-31"

        else:
            date_value = "9999-12-31"

        # ----------------------------------------------------
        # ITEM CODE
        # ----------------------------------------------------

        item_code = str(
            row.get("item_code") or ""
        )

        # ----------------------------------------------------
        # SLOW MOVING
        # ----------------------------------------------------

        slow_moving_priority = (
            0
            if row.get("slow_moving") == "YES"
            else 1
        )

        return (
            slow_moving_priority,
            date_value,
            item_code
        )

    # ========================================================
    # SALE QTY = 0 ALWAYS FIRST
    # ========================================================

    zero_sales_rows = []
    other_rows = []

    for row in data:

        if flt(row.get("sales_qty")) == 0:

            zero_sales_rows.append(row)

        else:

            other_rows.append(row)

    # ========================================================
    # SORT EACH GROUP
    # ========================================================

    zero_sales_rows.sort(
        key=sort_key,
        reverse=reverse_sort
    )

    other_rows.sort(
        key=sort_key,
        reverse=reverse_sort
    )

    # ========================================================
    # FINAL DATA
    # ========================================================

    data = (
        zero_sales_rows
        + other_rows
    )

    return data



# ============================================================
# PURCHASE RECEIVED QTY
# ============================================================

def get_purchase_received_qty(
    item_code,
    from_date,
    to_date
):

    result = frappe.db.sql(
        """
        SELECT
            COALESCE(
                SUM(pri.qty),
                0
            )

        FROM `tabPurchase Receipt Item` pri

        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent

        WHERE
            pr.docstatus = 1

            AND pr.company = %s

            AND pri.item_code = %s

            AND pr.posting_date >= %s

            AND pr.posting_date <= %s
        """,
        (
            COMPANY,
            item_code,
            from_date,
            to_date
        )
    )

    if not result:
        return 0

    return flt(
        result[0][0]
    )


# ============================================================
# STOCK IN DATE
# ============================================================

def get_stock_in_date(
    item_code,
    to_date
):

    result = frappe.db.sql(
        """
        SELECT
            MIN(pr.posting_date)

        FROM `tabPurchase Receipt Item` pri

        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent

        WHERE
            pr.docstatus = 1

            AND pr.company = %s

            AND pri.item_code = %s

            AND pr.posting_date <= %s
        """,
        (
            COMPANY,
            item_code,
            to_date
        )
    )

    if not result:
        return None

    return result[0][0]


# ============================================================
# SALES QTY
# ============================================================

def get_sales_qty(
    item_code,
    from_date,
    to_date
):

    result = frappe.db.sql(
        """
        SELECT
            COALESCE(
                SUM(dni.qty),
                0
            )

        FROM `tabDelivery Note Item` dni

        INNER JOIN `tabDelivery Note` dn
            ON dn.name = dni.parent

        LEFT JOIN `tabCustomer` c
            ON c.name = dn.customer

        WHERE
            dn.docstatus = 1

            AND IFNULL(
                c.is_internal_customer,
                0
            ) = 0

            AND dni.item_code = %s

            AND dn.posting_date >= %s

            AND dn.posting_date <= %s
        """,
        (
            item_code,
            from_date,
            to_date
        )
    )

    if not result:
        return 0

    return flt(
        result[0][0]
    )


# ============================================================
# SIS STOCK
# ============================================================

def get_sis_stock(
    item_code,
    posting_date
):

    if not posting_date:
        return 0

    # --------------------------------------------------------
    # Get all warehouses that belong to companies represented
    # by Internal Customers.
    # --------------------------------------------------------

    sis_warehouses = frappe.db.sql(
        """
        SELECT DISTINCT
            w.name

        FROM `tabWarehouse` w

        INNER JOIN `tabCustomer` c
            ON c.represents_company = w.company

        WHERE
            IFNULL(
                c.is_internal_customer,
                0
            ) = 1

            AND c.represents_company IS NOT NULL

            AND IFNULL(
                w.disabled,
                0
            ) = 0
        """,
        as_list=True
    )

    if not sis_warehouses:
        return 0

    warehouse_names = [
        row[0]
        for row in sis_warehouses
        if row and row[0]
    ]

    if not warehouse_names:
        return 0

    # --------------------------------------------------------
    # Get latest stock ledger balance for each SIS warehouse
    # --------------------------------------------------------

    placeholders = ", ".join(
        ["%s"] * len(warehouse_names)
    )

    params = [
        item_code,
        posting_date
    ]

    params.extend(
        warehouse_names
    )

    params.append(
        item_code
    )

    query = f"""
        SELECT
            COALESCE(
                SUM(latest.qty_after_transaction),
                0
            )

        FROM (

            SELECT
                sle.warehouse,
                sle.qty_after_transaction

            FROM `tabStock Ledger Entry` sle

            INNER JOIN (

                SELECT
                    warehouse,

                    MAX(
                        CONCAT(
                            posting_date,
                            ' ',
                            LPAD(
                                posting_time,
                                8,
                                '0'
                            ),
                            ' ',
                            creation
                        )
                    ) AS latest_transaction

                FROM `tabStock Ledger Entry`

                WHERE
                    item_code = %s

                    AND posting_date <= %s

                    AND is_cancelled = 0

                    AND warehouse IN (
                        {placeholders}
                    )

                GROUP BY
                    warehouse

            ) latest

                ON latest.warehouse = sle.warehouse

                AND CONCAT(
                    sle.posting_date,
                    ' ',
                    LPAD(
                        sle.posting_time,
                        8,
                        '0'
                    ),
                    ' ',
                    sle.creation
                ) = latest.latest_transaction

            WHERE
                sle.item_code = %s

                AND sle.is_cancelled = 0

        ) latest
    """

    result = frappe.db.sql(
        query,
        tuple(params)
    )

    if not result:
        return 0

    return flt(
        result[0][0]
    )


# ============================================================
# STOCK MOVEMENT FILTER
# ============================================================

def apply_movement_filter(
    movement,
    operator,
    value
):

    if not operator:
        return True

    if value in (
        None,
        ""
    ):
        return True

    movement = flt(
        movement
    )

    value = flt(
        value
    )

    if operator == "<":
        return movement < value

    if operator == "<=":
        return movement <= value

    if operator == "=":
        return abs(
            movement - value
        ) < 0.000001

    if operator == ">=":
        return movement >= value

    if operator == ">":
        return movement > value

    return True