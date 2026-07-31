# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.report.stock_balance.stock_balance import (
    execute as stock_balance_execute,
)


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Company",
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150,
        },
        {
            "label": "Party Name",
            "fieldname": "party_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Party City",
            "fieldname": "party_city",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120,
        },
        {
            "label": "Opening Stock",
            "fieldname": "opening_stock_qty",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": "Image",
            "fieldname": "image",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Barcode",
            "fieldname": "barcode",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "HSN",
            "fieldname": "hsn",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Division",
            "fieldname": "division",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Silhouette",
            "fieldname": "silhouette",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Warehouse",
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180,
        },
        {
            "label": "Brand",
            "fieldname": "brand",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Item Name",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Standard Buying",
            "fieldname": "standard_buying",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "WSP",
            "fieldname": "wsp",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": "MRP",
            "fieldname": "mrp",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": "RSP",
            "fieldname": "rsp",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": "STD",
            "fieldname": "std",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": "Standard Selling",
            "fieldname": "standard_selling",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "UOM",
            "fieldname": "uom",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": "Closing Stock Quantity",
            "fieldname": "closing_stock_qty",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": "Last Stock Inward Date",
            "fieldname": "last_inward_date",
            "fieldtype": "Date",
            "width": 140,
        },
    ]


def get_data(filters):
    columns = get_columns()

    if not filters:
        filters = frappe._dict()

    filters.setdefault("company", "")
    filters.setdefault("supplier", "")
    filters.setdefault("item_code", "")
    filters.setdefault("barcode", "")

    filters.setdefault("from_date", "2000-01-01")
    filters.setdefault("to_date", frappe.utils.today())

    sb_filters = frappe._dict({
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    })

    if filters.get("item_code"):
        sb_filters.item_code = [filters.get("item_code")]

    stock_columns, stock_data = stock_balance_execute(sb_filters)

    final_data = []

    for row in stock_data:

        item_code = row.get("item_code")
        warehouse = row.get("warehouse")
        company = row.get("company")

        opening_qty = row.get("opening_qty", 0) or 0
        qty = row.get("bal_qty", 0) or 0

        # Skip zero closing stock
        if round(float(qty or 0), 3) == 0:
            continue

        # ---------------------------------------------------------
        # Item Master
        # ---------------------------------------------------------

        item = frappe.db.get_value(
            "Item",
            item_code,
            [
                "item_name",
                "brand",
                "gst_hsn_code",
                "stock_uom",
                "item_group",
                "custom_silvet",
                "custom_departments",
                "image",
            ],
            as_dict=1,
        )

        # ---------------------------------------------------------
        # Image
        # ---------------------------------------------------------

        image = item.image if item and item.image else None

        if not image:
            image = frappe.db.get_value(
                "File",
                {
                    "attached_to_doctype": "Item",
                    "attached_to_name": item_code,
                },
                "file_url",
            )

        # ---------------------------------------------------------
        # Barcode
        # ---------------------------------------------------------

        barcode = frappe.db.get_value(
            "Item Barcode",
            {"parent": item_code},
            "barcode",
        ) or item_code

        # ---------------------------------------------------------
        # Supplier Details
        # ---------------------------------------------------------

        supplier = ""
        supplier_name = ""
        party_city = ""
        last_inward_date = None

        supplier_data = frappe.db.sql(
            """
            SELECT
                pr.supplier,
                pr.supplier_name,
                pr.posting_date,
                addr.city
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pri.parent = pr.name
            LEFT JOIN `tabDynamic Link` dl
                ON dl.link_doctype = 'Supplier'
                AND dl.link_name = pr.supplier
            LEFT JOIN `tabAddress` addr
                ON addr.name = dl.parent
            WHERE
                pri.item_code = %s
                AND pr.docstatus = 1
            ORDER BY
                pr.posting_date DESC,
                pr.creation DESC
            LIMIT 1
            """,
            (item_code,),
            as_dict=True,
        )

        if supplier_data:
            supplier = supplier_data[0].supplier
            supplier_name = supplier_data[0].supplier_name or supplier
            party_city = supplier_data[0].city or ""
            last_inward_date = supplier_data[0].posting_date

        else:
            item_default = frappe.db.get_value(
                "Item Default",
                {
                    "parent": item_code,
                    "company": company,
                },
                ["default_supplier"],
                as_dict=1,
            )

            if item_default and item_default.default_supplier:
                supplier = item_default.default_supplier

                supplier_name = (
                    frappe.db.get_value(
                        "Supplier",
                        supplier,
                        "supplier_name",
                    )
                    or supplier
                )

                city_data = frappe.db.sql(
                    """
                    SELECT
                        addr.city
                    FROM `tabAddress` addr
                    INNER JOIN `tabDynamic Link` dl
                        ON dl.parent = addr.name
                    WHERE
                        dl.link_doctype = 'Supplier'
                        AND dl.link_name = %s
                    LIMIT 1
                    """,
                    (supplier,),
                    as_dict=1,
                )

                if city_data:
                    party_city = city_data[0].city or ""

        # ---------------------------------------------------------
        # Supplier Filter
        # ---------------------------------------------------------

        if filters.get("supplier") and supplier != filters.get("supplier"):
            continue

        # ---------------------------------------------------------
        # Barcode Filter
        # ---------------------------------------------------------

        if filters.get("barcode"):

            search_barcode = filters.get("barcode").lower()

            if (
                search_barcode not in str(barcode).lower()
                and search_barcode not in item_code.lower()
            ):
                continue

        # ---------------------------------------------------------
        # Item Groups
        # ---------------------------------------------------------

        division = ""

        if item and item.item_group:
            division = frappe.db.get_value(
                "Item Group",
                item.item_group,
                "item_group_name",
            ) or ""

        silhouette = ""

        if item and item.custom_silvet:
            silhouette = frappe.db.get_value(
                "Item Group",
                item.custom_silvet,
                "item_group_name",
            ) or ""

        department = ""

        if item and item.custom_departments:
            department = frappe.db.get_value(
                "Item Group",
                item.custom_departments,
                "item_group_name",
            ) or ""

        # ---------------------------------------------------------
        # Prices
        # ---------------------------------------------------------

        prices = frappe.db.sql(
            """
            SELECT
                price_list,
                price_list_rate
            FROM `tabItem Price`
            WHERE
                item_code = %s
            """,
            (item_code,),
            as_dict=1,
        )

        price_map = {}

        for p in prices:
            price_map[p.price_list] = p.price_list_rate

        # ---------------------------------------------------------
        # Final Data
        #
        # IMPORTANT:
        # Order must exactly match get_columns()
        # ---------------------------------------------------------

        final_data.append([
            company,                                  # Company
            supplier_name,                            # Party Name
            party_city,                               # Party City
            item_code,                                # Item Code
            round(float(opening_qty or 0), 2),        # Opening Stock
            image or "",                              # Image
            barcode,                                  # Barcode
            item.gst_hsn_code if item else "",        # HSN
            division,                                 # Division
            silhouette,                               # Silhouette
            department,                               # Department
            warehouse,                                # Warehouse
            item.brand if item else "",               # Brand
            item.item_name if item else "",           # Item Name
            price_map.get("Standard Buying", 0),      # Standard Buying
            price_map.get("WSP", 0),                  # WSP
            price_map.get("MRP", 0),                  # MRP
            price_map.get("RSP", 0),                  # RSP
            price_map.get("STD", 0),                  # STD
            price_map.get("Standard Selling", 0),     # Standard Selling
            item.stock_uom if item else "",            # UOM
            round(float(qty or 0), 2),                # Closing Stock
            last_inward_date,                         # Last Stock Inward Date
        ])

    # ---------------------------------------------------------
    # Total Row
    # ---------------------------------------------------------

    if final_data:

        field_index = {
            col["fieldname"]: idx
            for idx, col in enumerate(columns)
        }

        total_row = [""] * len(columns)
        total_row[field_index["party_name"]] = "Total"

        numeric_fields = [
            "opening_stock_qty",
            "standard_buying",
            "wsp",
            "mrp",
            "rsp",
            "std",
            "standard_selling",
            "closing_stock_qty",
        ]

        for field in numeric_fields:

            col_idx = field_index[field]

            total_row[col_idx] = round(
                sum(
                    float(row[col_idx] or 0)
                    for row in final_data
                    
                ),
                2,
            )

        final_data.append(total_row)

    return final_data
