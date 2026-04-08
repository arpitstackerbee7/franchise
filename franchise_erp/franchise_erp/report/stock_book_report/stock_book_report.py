# Copyright (c) 2024, Franchise ERP and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        "Company:Link/Company:150",
        "Party Name:Data:150",
        "Party City:Data:120",
        "Item Code:Link/Item:120",
        "Barcode:Data:160",
        "HSN:Data:100",
        "Division:Data:120",
        "Silhouette:Data:120", 
        "Department:Data:120",
        "Item Name:Data:150",   
        "Standard Rate:Currency:100",
        "WSP:Currency:100",
        "MRP:Currency:100",
        "RSP:Currency:100",
        "UOM:Data:80",
        "Closing Stock Quantity:Float:120",
        "Last Stock Inward Date:Date:140"
    ]

# def get_data(filters):
#     if not filters:
#         filters = frappe._dict()
    
#     filters.setdefault("company", "")
#     filters.setdefault("supplier", "")
#     filters.setdefault("item_code", "")
#     filters.setdefault("barcode", "")

#     sql_query = """
#         SELECT
#             pr.company AS "Company:Link/Company:150",
#             pr.supplier_name AS "Party Name:Data:150",
#             addr.city AS "Party City:Data:120",
#             pri.item_code AS "Item Code:Link/Item:120",
#             IFNULL(NULLIF(pri.serial_no, ''), pri.item_code) AS "Barcode:Data:160",
#             item.gst_hsn_code AS "HSN:Data:100",
#             item.item_group AS "Division:Data:120",
#             item.custom_silvet AS "Silhouette:Data:120",
#             REPLACE(item.custom_departments, 'All Item Groups-', '') AS "Department:Data:120",
#             item.item_name AS "Item Name:Data:150",
#             IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'STD' LIMIT 1), 0) AS "Standard Rate:Currency:100",
#             IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'WSP' LIMIT 1), 0) AS "WSP:Currency:100",
#             IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'MRP' LIMIT 1), 0) AS "MRP:Currency:100",
#             IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'RSP' LIMIT 1), 0) AS "RSP:Currency:100",
#             item.stock_uom AS "UOM:Data:80",
#             (SELECT SUM(actual_qty) 
#              FROM `tabBin` 
#              WHERE item_code = item.name 
#              AND warehouse IN (SELECT name FROM `tabWarehouse` WHERE company = pr.company)) AS "Closing Stock Quantity:Float:120",
#             (SELECT MAX(posting_date) 
#              FROM `tabStock Ledger Entry` 
#              WHERE item_code = item.name 
#              AND actual_qty > 0 
#              AND is_cancelled = 0
#              AND company = pr.company) AS "Last Stock Inward Date:Date:140"
#         FROM
#             `tabPurchase Receipt` pr
#         INNER JOIN
#             `tabPurchase Receipt Item` pri ON pr.name = pri.parent
#         INNER JOIN
#             `tabItem` item ON pri.item_code = item.name
#         LEFT JOIN
#             `tabDynamic Link` dl ON dl.link_name = pr.supplier AND dl.link_doctype = 'Supplier' AND dl.parenttype = 'Address'
#         LEFT JOIN
#             `tabAddress` addr ON dl.parent = addr.name
#         WHERE
#             pr.docstatus = 1
#             AND (pr.company = %(company)s OR %(company)s IS NULL OR %(company)s = '')
#             AND (pr.supplier = %(supplier)s OR %(supplier)s IS NULL OR %(supplier)s = '')
#             AND (pri.item_code = %(item_code)s OR %(item_code)s IS NULL OR %(item_code)s = '')
#             AND (
#                 pri.serial_no LIKE CONCAT('%%', %(barcode)s, '%%') 
#                 OR pri.barcode LIKE CONCAT('%%', %(barcode)s, '%%') 
#                 OR pri.item_code LIKE CONCAT('%%', %(barcode)s, '%%')
#                 OR %(barcode)s IS NULL 
#                 OR %(barcode)s = ''
#             )
#         GROUP BY
#             pri.item_code, pr.company
#         ORDER BY
#             pr.company, pri.item_code
#     """
#     return frappe.db.sql(sql_query, filters, as_list=1)






def get_data(filters):
	if not filters:
		filters = frappe._dict()
	
	filters.setdefault("company", "")
	filters.setdefault("supplier", "")
	filters.setdefault("item_code", "")
	filters.setdefault("barcode", "")

	sql_query = """
		SELECT
			pr.company AS "Company:Link/Company:150",
            pr.supplier_name AS "Party Name:Data:150",
            addr.city AS "Party City:Data:120",
            pri.item_code AS "Item Code:Link/Item:120",
            IFNULL(NULLIF(pri.serial_no, ''), pri.item_code) AS "Barcode:Data:160",
            item.gst_hsn_code AS "HSN:Data:100",
            item.item_group AS "Division:Data:120",
            item.custom_silvet AS "Silhouette:Data:120",
            REPLACE(item.custom_departments, 'All Item Groups-', '') AS "Department:Data:120",
            item.item_name AS "Item Name:Data:150",
	
			IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'STD' LIMIT 1), 0) AS "Standard Rate:Currency:100",
			IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'WSP' LIMIT 1), 0) AS "WSP:Currency:100",
			IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'MRP' LIMIT 1), 0) AS "MRP:Currency:100",
			IFNULL((SELECT rate FROM `tabItem Price Row` WHERE parent = item.name AND price_list = 'RSP' LIMIT 1), 0) AS "RSP:Currency:100",
			item.stock_uom AS "UOM:Data:80",
			
			
			(SELECT SUM(actual_qty) 
			 FROM `tabBin` 
			 WHERE item_code = item.name 
			 AND warehouse IN (SELECT name FROM `tabWarehouse` WHERE company = pr.company)) AS "Closing Stock Quantity:Float:120",
			
			
			(SELECT MAX(pr_sub.posting_date) 
			 FROM `tabPurchase Receipt` pr_sub
			 INNER JOIN `tabPurchase Receipt Item` pri_sub ON pr_sub.name = pri_sub.parent
			 WHERE pri_sub.item_code = item.name 
			 AND pr_sub.docstatus = 1 
			 AND pr_sub.supplier = pr.supplier 
			 AND pr_sub.company = pr.company) AS "Last Stock Inward Date:Date:140"
			 
		FROM
			`tabPurchase Receipt` pr
		INNER JOIN
			`tabPurchase Receipt Item` pri ON pr.name = pri.parent
		INNER JOIN
			`tabItem` item ON pri.item_code = item.name
		LEFT JOIN
			`tabDynamic Link` dl ON dl.link_name = pr.supplier AND dl.link_doctype = 'Supplier' AND dl.parenttype = 'Address'
		LEFT JOIN
			`tabAddress` addr ON dl.parent = addr.name
		WHERE
			pr.docstatus = 1
			AND (pr.company = %(company)s OR %(company)s IS NULL OR %(company)s = '')
			AND (pr.supplier = %(supplier)s OR %(supplier)s IS NULL OR %(supplier)s = '')
			AND (pri.item_code = %(item_code)s OR %(item_code)s IS NULL OR %(item_code)s = '')
			AND (
				pri.serial_no LIKE CONCAT('%%', %(barcode)s, '%%') 
				OR pri.barcode LIKE CONCAT('%%', %(barcode)s, '%%') 
				OR pri.item_code LIKE CONCAT('%%', %(barcode)s, '%%')
				OR %(barcode)s IS NULL 
				OR %(barcode)s = ''
			)
		GROUP BY
			pri.item_code, pr.supplier, pr.company
		ORDER BY
			pr.company, pr.supplier, pri.item_code
	"""
	return frappe.db.sql(sql_query, filters, as_list=1)