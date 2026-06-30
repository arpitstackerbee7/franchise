# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


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
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Party Name", "fieldname": "party_name", "fieldtype": "Data", "width": 180},
        {"label": "Party City", "fieldname": "party_city", "fieldtype": "Data", "width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Image", "fieldname": "image", "fieldtype": "Data", "width": 120},
        {"label": "Barcode", "fieldname": "barcode", "fieldtype": "Data", "width": 160},
        {"label": "HSN", "fieldname": "hsn", "fieldtype": "Data", "width": 100},
        {"label": "Division", "fieldname": "division", "fieldtype": "Data", "width": 120},
        {"label": "Silhouette", "fieldname": "silhouette", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"label": "Brand", "fieldname": "brand", "fieldtype": "Data", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Standard Buying", "fieldname": "standard_buying", "fieldtype": "Currency", "width": 120},
        {"label": "WSP", "fieldname": "wsp", "fieldtype": "Currency", "width": 100},
        {"label": "MRP", "fieldname": "mrp", "fieldtype": "Currency", "width": 100},
        {"label": "RSP", "fieldname": "rsp", "fieldtype": "Currency", "width": 100},
        {"label": "STD", "fieldname": "std", "fieldtype": "Currency", "width": 100},
        {"label": "Standard Selling", "fieldname": "standard_selling", "fieldtype": "Currency", "width": 120},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": "Closing Stock Quantity", "fieldname": "closing_stock_qty", "fieldtype": "Float", "width": 120},
        {"label": "Last Stock Inward Date", "fieldname": "last_inward_date", "fieldtype": "Date", "width": 140},
    ]


def get_data(filters):

    if not filters:
        filters = frappe._dict()

    filters.setdefault("company", "")
    filters.setdefault("supplier", "")
    filters.setdefault("item_code", "")
    filters.setdefault("barcode", "")
    
    filters.setdefault("from_date", "2000-01-01")
    filters.setdefault("to_date", frappe.utils.today())

    # IMPORTANT
    # Stock Balance report internally uses "to_date"
    # and expects item_code as list if passed

    sb_filters = frappe._dict({
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    })

    if filters.get("item_code"):
        sb_filters.item_code = [filters.get("item_code")]

    # ERPNext Core Logic
    stock_columns, stock_data = stock_balance_execute(sb_filters)

    final_data = []

    for row in stock_data:

        item_code = row.get("item_code")
        warehouse = row.get("warehouse")
        company = row.get("company")
        qty = row.get("bal_qty", 0)

        # Skip zero qty
        if round(float(qty or 0), 3) == 0:
            continue

        
        # Item Master
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

        # Use Item's image field first, fallback to File doctype
        image = item.image if item and item.image else None

        if not image:
            image = frappe.db.get_value(
                "File",
                {
                    "attached_to_doctype": "Item",
                    "attached_to_name": item_code
                },
                "file_url"
            )
         
                

        # Barcode
        barcode = frappe.db.get_value(
            "Item Barcode",
            {"parent": item_code},
            "barcode",
        ) or item_code

        

        # Supplier Details

        supplier = ""
        supplier_name = ""
        party_city = ""

        # 1. Try latest Purchase Receipt supplier
        supplier_data = frappe.db.sql(
            """
            SELECT
                pr.supplier,
                pr.supplier_name
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pr.name = pri.parent
            WHERE
                pri.item_code = %s
                AND pr.docstatus = 1
            ORDER BY
                pr.posting_date DESC,
                pr.posting_time DESC
            LIMIT 1
            """,
            (item_code,),
            as_dict=1,
        )

        if supplier_data:

            supplier = supplier_data[0].supplier

            supplier_name = (
                supplier_data[0].supplier_name
                or supplier
            )

        else:

            # 2. Fallback → Item Default supplier
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

                supplier_name = frappe.db.get_value(
                    "Supplier",
                    supplier,
                    "supplier_name",
                ) or supplier

        # 3. Fetch city if supplier exists
        if supplier:

            city_data = frappe.db.sql(
                """
                SELECT addr.city
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

        # Supplier Filter
        if filters.get("supplier") and supplier != filters.get("supplier"):
            continue

        # Barcode Filter
        if filters.get("barcode"):

            if (
                filters.get("barcode").lower() not in str(barcode).lower()
                and filters.get("barcode").lower() not in item_code.lower()
            ):
                continue

 

        # Item Groups
        division = frappe.db.get_value(
            "Item Group",
            item.item_group,
            "item_group_name",
        )

        silhouette = frappe.db.get_value(
            "Item Group",
            item.custom_silvet,
            "item_group_name",
        )

        department = frappe.db.get_value(
            "Item Group",
            item.custom_departments,
            "item_group_name",
        )

        # Prices
        prices = frappe.db.sql(
            """
            SELECT
                price_list,
                price_list_rate
            FROM `tabItem Price`
            WHERE item_code = %s
            """,
            item_code,
            as_dict=1,
        )

        price_map = {}

        for p in prices:
            price_map[p.price_list] = p.price_list_rate

        # Last Stock Inward Date
        last_inward_date = frappe.db.sql(
            """
            SELECT MAX(posting_date)
            FROM `tabStock Ledger Entry`
            WHERE
                item_code = %s
                AND warehouse = %s
                AND actual_qty > 0
                AND is_cancelled = 0
                AND posting_date <= %s
            """,
            (item_code, warehouse, filters.get("to_date")),
        )

        last_inward_date = (
            last_inward_date[0][0]
            if last_inward_date and last_inward_date[0]
            else None
        )

        final_data.append([
            company,
            supplier_name,
            party_city,
            item_code,
            image or "",
            barcode,
            item.gst_hsn_code if item else "",
            division,
            silhouette,
            department,
            warehouse,
            item.brand if item else "",
            item.item_name if item else "",
            price_map.get("Standard Buying", 0),
            price_map.get("WSP", 0),
            price_map.get("MRP", 0),
            price_map.get("RSP", 0),
            price_map.get("STD", 0),
            price_map.get("Standard Selling", 0),
            item.stock_uom if item else "",
            round(qty, 2),
            last_inward_date,
        ])

    return final_data