# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.utils import get_stock_balance
class BulkPurchaseReturn(Document):

    def validate(self):
        self.validate_supplier()
        self.validate_qty()
        self.validate_non_serialized_stock()

    def validate_supplier(self):
        for row in self.items:
            pr_supplier = frappe.db.get_value(
                "Purchase Receipt", row.purchase_receipt, "supplier"
            )

            if pr_supplier != self.supplier:
                frappe.throw(f"Supplier mismatch in row {row.idx}")

    def validate_qty(self):

        for row in self.items:

            received_qty = frappe.db.get_value(
                "Purchase Receipt Item",
                row.purchase_receipt_item,
                "qty"
            )

            if row.qty > received_qty:
                frappe.throw(
                    f"Return qty cannot exceed received qty in row {row.idx}"
                )

            # check if item is serialized
            has_serial_no = frappe.db.get_value(
                "Item",
                row.item_code,
                "has_serial_no"
            )

            if has_serial_no:

                serials = []

                if row.serial_nos:
                    serials = [s.strip() for s in row.serial_nos.split("\n") if s.strip()]

                if not serials:
                    frappe.throw(
                        f"Row {row.idx}: Serial Numbers are required for serialized item {row.item_code}"
                    )

                if len(serials) != row.qty:
                    frappe.throw(
                        f"Row {row.idx}: Qty must match number of Serial Numbers for item {row.item_code}"
                    )

    def validate_non_serialized_stock(self):

        for row in self.items:

            # 🔹 Skip serialized items
            has_serial_no = frappe.db.get_value("Item", row.item_code, "has_serial_no")
            if has_serial_no:
                continue

            # 🔹 Get current stock
            available_stock = get_stock_balance(
                row.item_code,
                row.warehouse
            )

            # 🔹 Compare with return qty
            if available_stock < row.qty:
                frappe.throw(
                    f"Row {row.idx}: Not enough stock for Item {row.item_code} "
                    f"in Warehouse {row.warehouse}. Available: {available_stock}, Required: {row.qty}"
                )


    def on_submit(self):

        self.db_set("status", "Queued")
        # 🚀 Enqueue background job
        frappe.enqueue(
            method="franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.process_bulk_purchase_return",
            docname=self.name,
            queue="long",
            timeout=600,
            job_name=f"Bulk Purchase Return {self.name}"
        )

        # 💬 User message
        frappe.msgprint(
            "Return documents are being created in the background."
        )

def process_bulk_purchase_return(docname):

    doc = frappe.get_doc("Bulk Purchase Return", docname)

    try: 

        receipts = {}
        doc.db_set("status", "In Progress")

        for row in doc.items:
            receipts.setdefault(row.purchase_receipt, []).append(row)

        # ✅ Prefetch
        pr_item_names = list(set([row.purchase_receipt_item for row in doc.items]))

        pr_items = frappe.get_all(
            "Purchase Receipt Item",
            filters={"name": ["in", pr_item_names]},
            fields=["name", "purchase_order", "purchase_order_item"]
        )

        pr_item_map = {d.name: d for d in pr_items}

        for pr, items in receipts.items():

            return_doc = make_return_doc("Purchase Receipt", pr)
            return_doc.custom_bulk_purchase_return = doc.name
            return_doc.items = []

            for row in items:

                pr_item = pr_item_map.get(row.purchase_receipt_item)

                serials = row.serial_nos.strip() if row.serial_nos else ""

                return_doc.append("items", {
                    "item_code": row.item_code,
                    "qty": -abs(row.qty),
                    "warehouse": row.warehouse,
                    "rate": row.rate,
                    "serial_no": serials,
                    "purchase_order": pr_item.purchase_order if pr_item else "",
                    "purchase_order_item": pr_item.purchase_order_item if pr_item else "",
                    "purchase_receipt_item": row.purchase_receipt_item
                })

            return_doc.set_missing_values()
            return_doc.calculate_taxes_and_totals()
            return_doc.insert(ignore_permissions=True)

        doc.db_set("status", "Completed")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Bulk Purchase Return Failed")

        doc.db_set("status", "Failed")


@frappe.whitelist()
def get_returnable_items(supplier, company, item_code=None):

    conditions = "AND pr.supplier = %(supplier)s AND pr.company = %(company)s"

    if item_code:
        conditions += " AND pri.item_code = %(item_code)s"

    items = frappe.db.sql(f"""
        SELECT
            pri.parent AS purchase_receipt,
            pri.name AS purchase_receipt_item,
            pri.item_code,
            pri.qty AS received_qty,
            pri.returned_qty,
            (pri.qty - pri.returned_qty) AS returnable_qty,
            0 AS return_qty,
            i.has_serial_no
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        LEFT JOIN `tabItem` i
            ON i.name = pri.item_code
        WHERE pr.docstatus = 1
        AND pr.is_return = 0
        AND pri.qty > IFNULL(pri.returned_qty,0)
        {conditions}
        ORDER BY pr.posting_date DESC
    """,
    {
        "supplier": supplier,
        "company": company,
        "item_code": item_code
    },
    as_dict=1)
    return items


@frappe.whitelist()
def get_pr_item_details(items):

    items = frappe.parse_json(items)
    result = []

    for d in items:

        pr_item = frappe.get_doc("Purchase Receipt Item", d.get("purchase_receipt_item"))
        item_doc = frappe.get_doc("Item", pr_item.item_code)

        is_serialized = item_doc.has_serial_no

        # original PR serials
        pr_serials = []
        if pr_item.serial_no:
            pr_serials = pr_item.serial_no.split("\n")

        # returned serials
        returned_serials = frappe.db.sql("""
            SELECT pri.serial_no
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr
            ON pri.parent = pr.name
            WHERE pr.is_return = 1
            AND pr.docstatus = 1
            AND pri.purchase_receipt_item = %s
        """, pr_item.name, as_dict=1)

        returned_list = []

        for r in returned_serials:
            if r.serial_no:
                returned_list.extend(r.serial_no.split("\n"))

        available_serials = list(set(pr_serials) - set(returned_list))

        scanned_serials = []

        if d.get("serial_nos"):
            scanned_serials = [s.strip() for s in d.get("serial_nos").split("\n") if s.strip()]

        # validation
        invalid_serials = list(set(scanned_serials) - set(available_serials))
        if invalid_serials:
            frappe.throw(
                f"Invalid Serial(s) for Item {pr_item.item_code}: {', '.join(invalid_serials)}"
            )

        # warehouse grouping
        warehouse_map = {}

        if is_serialized:

            for serial in scanned_serials:

                serial_doc = frappe.get_doc("Serial No", serial)
                wh = serial_doc.warehouse or pr_item.warehouse

                warehouse_map.setdefault(wh, []).append(serial)

            for wh, serial_list in warehouse_map.items():

                result.append({
                    "name": pr_item.name,
                    "purchase_receipt": pr_item.parent,
                    "purchase_receipt_item": pr_item.name,
                    "item_code": pr_item.item_code,
                    "item_name": pr_item.item_name,
                    "warehouse": wh,
                    "uom": pr_item.uom,
                    "stock_uom": pr_item.stock_uom,
                    "conversion_factor": pr_item.conversion_factor,
                    "rate": pr_item.rate,
                    "qty": len(serial_list),
                    "returnable_quantity": d.get("returnable_qty"),
                    "serial_nos": "\n".join(serial_list),
                    "available_serial_nos": "\n".join(available_serials)
                })

        else:

            qty = d.get("return_qty")
            wh = pr_item.warehouse

            warehouse_map.setdefault(wh, 0)
            warehouse_map[wh] += qty

            for wh, qty in warehouse_map.items():

                result.append({
                    "name": pr_item.name,
                    "purchase_receipt": pr_item.parent,
                    "purchase_receipt_item": pr_item.name,
                    "item_code": pr_item.item_code,
                    "item_name": pr_item.item_name,
                    "warehouse": wh,
                    "uom": pr_item.uom,
                    "stock_uom": pr_item.stock_uom,
                    "conversion_factor": pr_item.conversion_factor,
                    "rate": pr_item.rate,
                    "qty": qty,
                    "returnable_quantity": d.get("returnable_qty"),
                    "serial_nos": "",
                    "available_serial_nos": ""
                })

    return result

@frappe.whitelist()
def get_pr_from_serial(serial_no, company):

    # Find PR Item containing this serial
    pr_item = frappe.db.sql("""
        SELECT
            pri.name,
            pri.parent AS purchase_receipt,
            pri.item_code,
            pri.qty,
            pri.returned_qty
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE pr.docstatus = 1
        AND pr.company = %s
        AND pri.serial_no LIKE %s
        LIMIT 1
    """, (company, f"%{serial_no}%"), as_dict=True)

    if not pr_item:
        return None

    pr_item = pr_item[0]

    serial = frappe.get_doc("Serial No", serial_no)

    return {
        "purchase_receipt": pr_item.purchase_receipt,
        "purchase_receipt_item": pr_item.name,
        "item_code": pr_item.item_code,
        "serial_no": serial_no,
        "status": serial.status,
        "returnable_qty": 1,
        "returned_qty": pr_item.returned_qty or 0,
        "return_qty": 1
    }

@frappe.whitelist()
def submit_created_prs(docname):

    doc = frappe.get_doc("Bulk Purchase Return", docname)
    doc.db_set("submit_status", "Queued")

    frappe.enqueue(
        method="franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.process_submit_prs",
        docname=docname,
        queue="long",
        timeout=600,
        job_name=f"Submit PRs for {docname}"
    )

    return "Queued"

def process_submit_prs(docname):

    doc = frappe.get_doc("Bulk Purchase Return", docname)

    try:
        doc.db_set("submit_status", "In Progress")

        prs = frappe.get_all(
            "Purchase Receipt",
            filters={
                "custom_bulk_purchase_return": docname,
                "docstatus": 0
            },
            pluck="name"
        )

        for pr in prs:
            pr_doc = frappe.get_doc("Purchase Receipt", pr)
            pr_doc.flags.ignore_permissions = True
            pr_doc.submit()

        doc.db_set("submit_status", "Completed")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Submit PRs Failed")

        doc.db_set("submit_status", "Failed")


@frappe.whitelist()
def has_draft_return_prs(docname):

    exists = frappe.db.exists(
        "Purchase Receipt",
        {
            "custom_bulk_purchase_return": docname,
            "docstatus": 0
        }
    )

    return bool(exists)