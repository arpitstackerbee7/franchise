import frappe
from frappe import _
from frappe.utils import flt


# =========================================================
# COLUMNS
# =========================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# =========================================================
# VALIDATION
# =========================================================

def validate_filters(filters):

    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))

    if not filters.get("from_date"):
        frappe.throw(_("From Date is mandatory"))

    if not filters.get("to_date"):
        frappe.throw(_("To Date is mandatory"))

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    limit = cint_safe(filters.get("limit"))

    if limit <= 0:
        limit = 100

    if limit > 5000:
        limit = 5000

    filters.limit = limit

    if filters.get("order_direction") not in ["Ascending", "Descending"]:
        filters.order_direction = "Ascending"

    if filters.get("order_by") not in [
        "Brand",
        "Item Code",
        "Item Name",
        "Purchase Qty",
        "Purchase Value",
        "Sale Qty",
        "Sale Value",
        "Closing Qty",
        "Stock Value"
    ]:
        filters.order_by = "Brand"


# =========================================================
# COLUMNS
# =========================================================

def get_columns():

    return [

        # =================================================
        # ITEM MASTER
        # =================================================

        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },

        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180
        },

        {
            "label": _("Brand"),
            "fieldname": "brand",
            "fieldtype": "Link",
            "options": "Brand",
            "width": 120
        },

        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 150
        },

        {
            "label": _("Barcode"),
            "fieldname": "custom_barcode_code",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("GST HSN Code"),
            "fieldname": "gst_hsn_code",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Count Of Pcs"),
            "fieldname": "custom_count_of_pcs",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": _("Colour Name"),
            "fieldname": "custom_colour_name",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Season"),
            "fieldname": "custom_season",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": _("Top Fabrics"),
            "fieldname": "custom_top_fabrics",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Top Lining"),
            "fieldname": "custom_top_lining",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Bottom Fabric"),
            "fieldname": "custom_bottom_fabric",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Bottom Lining"),
            "fieldname": "custom_bottom_lining",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Dupatta Fabric"),
            "fieldname": "custom_dupatta_fabric",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Dupatta Embalishment"),
            "fieldname": "custom_dupatta_embalishment",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": _("Dupatta Width"),
            "fieldname": "custom_dupatta_width",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Block"),
            "fieldname": "custom_block",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": _("Neck Line"),
            "fieldname": "custom_neck_line",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Sleeve Length"),
            "fieldname": "custom_sleeve_length",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Bottom Type"),
            "fieldname": "custom_bottom_type",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Bottom Length Outseam"),
            "fieldname": "custom_bottom_length_outseam",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": _("Set Qty"),
            "fieldname": "custom_set_qty",
            "fieldtype": "Float",
            "width": 100
        },

        {
            "label": _("Top Fabric Type"),
            "fieldname": "custom_top_fabric_type",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": _("Top Embalishment"),
            "fieldname": "custom_top_embalishment",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": _("Bottom Fabric Type"),
            "fieldname": "custom_bottom_fabric_type",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": _("Bottom Embalishment"),
            "fieldname": "custom_bottom_embalishment",
            "fieldtype": "Data",
            "width": 140
        },

        {
            "label": _("Dupatta Fabric Type"),
            "fieldname": "custom_dupatta_fabric_type",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": _("Dupatta Length"),
            "fieldname": "custom_dupatta_length",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Sup Design No."),
            "fieldname": "custom_sup_design_no",
            "fieldtype": "Data",
            "width": 130
        },

        {
            "label": _("Size"),
            "fieldname": "custom_size",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": _("Sleeves Type"),
            "fieldname": "custom_sleeves_type",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Top Length"),
            "fieldname": "custom_top_length",
            "fieldtype": "Data",
            "width": 120
        },

        {
            "label": _("Bottom Length Inseam"),
            "fieldname": "custom_bottom_length_inseam",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": _("Waist"),
            "fieldname": "custom_waist",
            "fieldtype": "Data",
            "width": 100
        },

        {
            "label": _("Mfg. Date"),
            "fieldname": "custom_mfg_date",
            "fieldtype": "Date",
            "width": 110
        },

        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 100
        },

        
	    # =================================================
		# ITEM PRICE
		# =================================================

		{
			"label": _("MRP"),
			"fieldname": "mrp",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110
		},

		{
			"label": _("STD"),
			"fieldname": "std",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110
		},

		{
			"label": _("WSP"),
			"fieldname": "wsp",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110
		},
        # =================================================
        # STOCK
        # =================================================

        {
            "label": _("Opening Qty"),
            "fieldname": "opening_qty",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": _("Opening Value"),
            "fieldname": "opening_value",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },

        # =================================================
        # PURCHASE
        # =================================================

        {
            "label": _("Purchase Qty"),
            "fieldname": "purchase_qty",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": _("Purchase Value"),
            "fieldname": "purchase_value",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },

        # =================================================
        # SALES
        # =================================================

        {
            "label": _("Sale Qty"),
            "fieldname": "sale_qty",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": _("Sale Value"),
            "fieldname": "sale_value",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },

        # =================================================
        # CLOSING STOCK
        # =================================================

        {
            "label": _("Closing Qty"),
            "fieldname": "closing_qty",
            "fieldtype": "Float",
            "width": 110
        },

        {
            "label": _("Closing Value"),
            "fieldname": "closing_value",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },

        {
            "label": _("Stock Value"),
            "fieldname": "stock_value",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
       

    ]
# =========================================================
# MAIN DATA
# =========================================================

def get_data(filters):

    item_conditions = get_item_conditions(filters)

    item_data = frappe.db.sql(
		f"""
		SELECT
			i.name AS item_code,
			i.item_name,
			i.brand,
			i.item_group,
			i.description,

			i.custom_barcode_code,
			i.gst_hsn_code,
			i.custom_count_of_pcs,
			i.custom_colour_name,
			i.custom_season,
			i.custom_top_fabrics,
			i.custom_top_lining,
			i.custom_bottom_fabric,
			i.custom_bottom_lining,
			i.custom_dupatta_fabric,
			i.custom_dupatta_embalishment,
			i.custom_dupatta_width,
			i.custom_block,
			i.custom_neck_line,
			i.custom_sleeve_length,
			i.custom_bottom_type,
			i.custom_bottom_length_outseam,
			i.custom_set_qty,
			i.custom_top_fabric_type,
			i.custom_top_embalishment,
			i.custom_bottom_fabric_type,
			i.custom_bottom_embalishment,
			i.custom_dupatta_fabric_type,
			i.custom_dupatta_length,
			i.custom_sup_design_no,
			i.custom_size,
			i.custom_sleeves_type,
			i.custom_top_length,
			i.custom_bottom_length_inseam,
			i.custom_waist,
			i.custom_mfg_date,

			i.stock_uom,
			i.purchase_uom,
			i.sales_uom,
			i.is_stock_item,
			i.disabled,
			i.has_batch_no,
			i.has_serial_no

		FROM `tabItem` i

		WHERE
			1 = 1

			{item_conditions}

		ORDER BY
			i.brand,
			i.name
		""",
		filters,
		as_dict=True
	)

    if not item_data:
        return []

    item_codes = [d.item_code for d in item_data]
    item_prices = get_item_prices(item_codes)

    opening_stock = get_opening_stock(filters, item_codes)
    closing_stock = get_closing_stock(filters, item_codes)

    purchase_data = get_purchase_data(filters, item_codes)
    sales_data = get_sales_data(filters, item_codes)

    data = []

    for item in item_data:

        item_code = item.item_code

        opening = opening_stock.get(
            item_code,
            {
                "qty": 0,
                "value": 0
            }
        )

        closing = closing_stock.get(
            item_code,
            {
                "qty": 0,
                "value": 0,
                "valuation_rate": 0
            }
        )

        purchase = purchase_data.get(
            item_code,
            {
                "qty": 0,
                "value": 0
            }
        )
        
        prices = item_prices.get(
			item_code,
			{
				"mrp": 0,
				"std": 0,
				"wsp": 0
			}
		)

        sale = sales_data.get(
            item_code,
            {
                "qty": 0,
                "value": 0
            }
        )

        row = {

			# =================================================
			# ITEM MASTER
			# =================================================

			"item_code": item.item_code,
			"item_name": item.item_name,
			"brand": item.brand,
			"item_group": item.item_group,
			"description": item.description,

			"custom_barcode_code": item.custom_barcode_code,
			"gst_hsn_code": item.gst_hsn_code,
			"custom_count_of_pcs": flt(item.custom_count_of_pcs),
			"custom_colour_name": item.custom_colour_name,
			"custom_season": item.custom_season,

			"custom_top_fabrics": item.custom_top_fabrics,
			"custom_top_lining": item.custom_top_lining,
			"custom_bottom_fabric": item.custom_bottom_fabric,
			"custom_bottom_lining": item.custom_bottom_lining,

			"custom_dupatta_fabric": item.custom_dupatta_fabric,
			"custom_dupatta_embalishment": item.custom_dupatta_embalishment,
			"custom_dupatta_width": item.custom_dupatta_width,

			"custom_block": item.custom_block,
			"custom_neck_line": item.custom_neck_line,
			"custom_sleeve_length": item.custom_sleeve_length,

			"custom_bottom_type": item.custom_bottom_type,
			"custom_bottom_length_outseam": item.custom_bottom_length_outseam,

			"custom_set_qty": flt(item.custom_set_qty),

			"custom_top_fabric_type": item.custom_top_fabric_type,
			"custom_top_embalishment": item.custom_top_embalishment,

			"custom_bottom_fabric_type": item.custom_bottom_fabric_type,
			"custom_bottom_embalishment": item.custom_bottom_embalishment,

			"custom_dupatta_fabric_type": item.custom_dupatta_fabric_type,
			"custom_dupatta_length": item.custom_dupatta_length,

			"custom_sup_design_no": item.custom_sup_design_no,
			"custom_size": item.custom_size,
			"custom_sleeves_type": item.custom_sleeves_type,

			"custom_top_length": item.custom_top_length,
			"custom_bottom_length_inseam": item.custom_bottom_length_inseam,
			"custom_waist": item.custom_waist,

			"custom_mfg_date": item.custom_mfg_date,

			"stock_uom": item.stock_uom,
			"purchase_uom": item.purchase_uom,
			"sales_uom": item.sales_uom,

			"is_stock_item": item.is_stock_item,
			"disabled": item.disabled,
			"has_batch_no": item.has_batch_no,
			"has_serial_no": item.has_serial_no,

			# =================================================
			# ITEM PRICE
			# =================================================

			"mrp": flt(prices.get("mrp")),
			"std": flt(prices.get("std")),
			"wsp": flt(prices.get("wsp")),

			# =================================================
			# STOCK
			# =================================================

			"opening_qty": flt(opening.get("qty")),
			"opening_value": flt(opening.get("value")),

			# =================================================
			# PURCHASE
			# =================================================

			"purchase_qty": flt(purchase.get("qty")),
			"purchase_value": flt(purchase.get("value")),

			# =================================================
			# SALES
			# =================================================

			"sale_qty": flt(sale.get("qty")),
			"sale_value": flt(sale.get("value")),

			# =================================================
			# CLOSING
			# =================================================

			"closing_qty": flt(closing.get("qty")),
			"closing_value": flt(closing.get("value")),

			"valuation_rate": flt(
				closing.get("valuation_rate")
			),

			"stock_value": flt(
				closing.get("value")
			),

			"currency": get_company_currency(filters.company)
		}

        data.append(row)

    # -----------------------------------------------------
    # ORDER
    # -----------------------------------------------------

    data = sort_data(
        data,
        filters.get("order_by"),
        filters.get("order_direction")
    )

    # -----------------------------------------------------
    # LIMIT
    # -----------------------------------------------------

    limit = cint_safe(filters.get("limit"))

    if limit <= 0:
        limit = 100

    return data[:limit]



# =========================================================
# ITEM PRICES
# =========================================================

def get_item_prices(item_codes):

    if not item_codes:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            ip.item_code,
            ip.price_list,
            ip.price_list_rate,
            ip.valid_from,
            ip.valid_upto,
            ip.creation

        FROM `tabItem Price` ip

        WHERE
            ip.item_code IN %(item_codes)s

            AND ip.price_list IN (
                'MRP',
                'STD',
                'WSP'
            )

            AND (
                ip.valid_from IS NULL
                OR ip.valid_from <= CURDATE()
            )

            AND (
                ip.valid_upto IS NULL
                OR ip.valid_upto >= CURDATE()
            )

        ORDER BY
            ip.item_code,
            ip.price_list,
            ip.valid_from DESC,
            ip.creation DESC
        """,
        {
            "item_codes": tuple(item_codes)
        },
        as_dict=True
    )

    result = {}

    for row in rows:

        item_code = row.item_code

        if item_code not in result:
            result[item_code] = {
                "mrp": 0,
                "std": 0,
                "wsp": 0
            }

        price_list = row.price_list

        if price_list == "MRP":

            # First applicable record
            if not result[item_code]["mrp"]:
                result[item_code]["mrp"] = flt(
                    row.price_list_rate
                )

        elif price_list == "STD":

            if not result[item_code]["std"]:
                result[item_code]["std"] = flt(
                    row.price_list_rate
                )

        elif price_list == "WSP":

            if not result[item_code]["wsp"]:
                result[item_code]["wsp"] = flt(
                    row.price_list_rate
                )

    return result
# =========================================================
# ITEM CONDITIONS
# =========================================================

def get_item_conditions(filters):

    conditions = ""

    if filters.get("brand"):
        conditions += """
            AND i.brand = %(brand)s
        """

    if filters.get("item_group"):
        conditions += """
            AND i.item_group = %(item_group)s
        """

    if filters.get("item_code"):
        conditions += """
            AND i.name = %(item_code)s
        """

    return conditions


# =========================================================
# OPENING STOCK
# =========================================================

def get_opening_stock(filters, item_codes):

    if not item_codes:
        return {}

    conditions = [
        "sle.company = %(company)s",
        "sle.posting_date < %(from_date)s",
        "sle.is_cancelled = 0",
        "sle.item_code IN %(item_codes)s"
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "item_codes": tuple(item_codes)
    }

    if filters.get("warehouse"):
        conditions.append(
            """
            sle.warehouse = %(warehouse)s
            """
        )

        values["warehouse"] = filters.warehouse

    condition_string = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            sle.item_code,

            SUM(sle.actual_qty) AS qty,

            SUM(sle.stock_value_difference) AS value

        FROM `tabStock Ledger Entry` sle

        WHERE
            {condition_string}

        GROUP BY
            sle.item_code
        """,
        values,
        as_dict=True
    )

    result = {}

    for row in rows:

        result[row.item_code] = {
            "qty": flt(row.qty),
            "value": flt(row.value)
        }

    return result


# =========================================================
# CLOSING STOCK
# =========================================================

def get_closing_stock(filters, item_codes):

    if not item_codes:
        return {}

    conditions = [
        "sle.company = %(company)s",
        "sle.posting_date <= %(to_date)s",
        "sle.is_cancelled = 0",
        "sle.item_code IN %(item_codes)s"
    ]

    values = {
        "company": filters.company,
        "to_date": filters.to_date,
        "item_codes": tuple(item_codes)
    }

    if filters.get("warehouse"):
        conditions.append(
            """
            sle.warehouse = %(warehouse)s
            """
        )

        values["warehouse"] = filters.warehouse

    condition_string = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            sle.item_code,

            SUM(sle.actual_qty) AS qty,

            SUM(sle.stock_value_difference) AS value,

            (
                SELECT
                    sle2.valuation_rate

                FROM `tabStock Ledger Entry` sle2

                WHERE
                    sle2.item_code = sle.item_code

                    AND sle2.company = %(company)s

                    AND sle2.posting_date <= %(to_date)s

                    AND sle2.is_cancelled = 0

                    {get_warehouse_subcondition(filters)}

                ORDER BY
                    sle2.posting_date DESC,
                    sle2.posting_time DESC,
                    sle2.creation DESC

                LIMIT 1
            ) AS valuation_rate

        FROM `tabStock Ledger Entry` sle

        WHERE
            {condition_string}

        GROUP BY
            sle.item_code
        """,
        values,
        as_dict=True
    )

    result = {}

    for row in rows:

        result[row.item_code] = {
            "qty": flt(row.qty),
            "value": flt(row.value),
            "valuation_rate": flt(row.valuation_rate)
        }

    return result


# =========================================================
# WAREHOUSE SUB CONDITION
# =========================================================

def get_warehouse_subcondition(filters):

    if filters.get("warehouse"):
        return """
            AND sle2.warehouse = %(warehouse)s
        """

    return ""


# =========================================================
# PURCHASE DATA
# =========================================================

def get_purchase_data(filters, item_codes):

    if not item_codes:
        return {}

    conditions = [
        "pi.company = %(company)s",
        "pi.posting_date BETWEEN %(from_date)s AND %(to_date)s",
        "pi.docstatus = 1",
        "pii.item_code IN %(item_codes)s"
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
        "item_codes": tuple(item_codes)
    }

    if filters.get("supplier"):
        conditions.append(
            """
            pi.supplier = %(supplier)s
            """
        )

        values["supplier"] = filters.supplier

    if filters.get("warehouse"):
        conditions.append(
            """
            pii.warehouse = %(warehouse)s
            """
        )

        values["warehouse"] = filters.warehouse

    condition_string = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT

            pii.item_code,

            SUM(
                CASE
                    WHEN pi.is_return = 1
                    THEN -ABS(pii.stock_qty)
                    ELSE pii.stock_qty
                END
            ) AS qty,

            SUM(
                CASE
                    WHEN pi.is_return = 1
                    THEN -ABS(pii.base_net_amount)
                    ELSE pii.base_net_amount
                END
            ) AS value

        FROM `tabPurchase Invoice` pi

        INNER JOIN `tabPurchase Invoice Item` pii
            ON pii.parent = pi.name

        WHERE
            {condition_string}

        GROUP BY
            pii.item_code
        """,
        values,
        as_dict=True
    )

    result = {}

    for row in rows:

        result[row.item_code] = {
            "qty": flt(row.qty),
            "value": flt(row.value)
        }

    return result


# =========================================================
# SALES DATA
# =========================================================

def get_sales_data(filters, item_codes):

    if not item_codes:
        return {}

    conditions = [
        "si.company = %(company)s",
        "si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
        "si.docstatus = 1",
        "sii.item_code IN %(item_codes)s"
    ]

    values = {
        "company": filters.company,
        "from_date": filters.from_date,
        "to_date": filters.to_date,
        "item_codes": tuple(item_codes)
    }

    if filters.get("customer"):
        conditions.append(
            """
            si.customer = %(customer)s
            """
        )

        values["customer"] = filters.customer

    if filters.get("warehouse"):
        conditions.append(
            """
            sii.warehouse = %(warehouse)s
            """
        )

        values["warehouse"] = filters.warehouse

    condition_string = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT

            sii.item_code,

            SUM(
                CASE
                    WHEN si.is_return = 1
                    THEN -ABS(sii.stock_qty)
                    ELSE sii.stock_qty
                END
            ) AS qty,

            SUM(
                CASE
                    WHEN si.is_return = 1
                    THEN -ABS(sii.base_net_amount)
                    ELSE sii.base_net_amount
                END
            ) AS value

        FROM `tabSales Invoice` si

        INNER JOIN `tabSales Invoice Item` sii
            ON sii.parent = si.name

        WHERE
            {condition_string}

        GROUP BY
            sii.item_code
        """,
        values,
        as_dict=True
    )

    result = {}

    for row in rows:

        result[row.item_code] = {
            "qty": flt(row.qty),
            "value": flt(row.value)
        }

    return result


# =========================================================
# SORTING
# =========================================================

def sort_data(data, order_by, direction):

    field_map = {

        "Brand": "brand",

        "Item Code": "item_code",

        "Item Name": "item_name",

        "Purchase Qty": "purchase_qty",

        "Purchase Value": "purchase_value",

        "Sale Qty": "sale_qty",

        "Sale Value": "sale_value",

        "Closing Qty": "closing_qty",

        "Stock Value": "stock_value"
    }

    field = field_map.get(
        order_by,
        "brand"
    )

    reverse = direction == "Descending"

    try:

        return sorted(
            data,
            key=lambda x: (
                x.get(field) is None,
                x.get(field) or 0
                if field in [
                    "purchase_qty",
                    "purchase_value",
                    "sale_qty",
                    "sale_value",
                    "closing_qty",
                    "stock_value"
                ]
                else str(x.get(field) or "").lower()
            ),
            reverse=reverse
        )

    except Exception:
        return data


# =========================================================
# COMPANY CURRENCY
# =========================================================

def get_company_currency(company):

    if not company:
        return None

    return frappe.db.get_value(
        "Company",
        company,
        "default_currency"
    )


# =========================================================
# SAFE INT
# =========================================================

def cint_safe(value):

    try:
        return int(value or 0)

    except Exception:
        return 0