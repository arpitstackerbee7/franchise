# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class BulkPurchaseReturn(Document):

    def validate(self):
        self.validate_supplier()
        self.validate_qty()

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

    def on_submit(self):

        receipts = {}

        for row in self.items:
            receipts.setdefault(row.purchase_receipt, []).append(row)

        for pr, items in receipts.items():

            return_doc = frappe.new_doc("Purchase Receipt")
            return_doc.is_return = 1
            return_doc.return_against = pr
            return_doc.supplier = self.supplier
            return_doc.company = self.company

            for row in items:

                pr_item = frappe.get_doc("Purchase Receipt Item", row.purchase_receipt_item)

                serials = row.serial_nos.strip() if row.serial_nos else ""

                return_doc.append("items", {
                    "item_code": row.item_code,
                    "qty": -row.qty,
                    "returned_qty": row.qty,
                    "warehouse": row.warehouse,
                    "rate": row.rate,
                    "serial_no": serials,

                    # Safe PO assignment
                    "purchase_order": pr_item.purchase_order or "",
                    "purchase_order_item": pr_item.purchase_order_item or "",
                    "purchase_receipt_item": row.purchase_receipt_item
                })

            return_doc.insert()

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
            0 AS return_qty
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
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

        # serials received in original PR
        pr_serials = []
        if pr_item.serial_no:
            pr_serials = pr_item.serial_no.split("\n")

        # serials already returned via Purchase Return
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

        # available serials
        available_serials = list(set(pr_serials) - set(returned_list))

        result.append({
            "name": pr_item.name,
            "purchase_receipt": pr_item.parent,
            "item_code": pr_item.item_code,
            "item_name": pr_item.item_name,
            "warehouse": pr_item.warehouse,
            "uom": pr_item.uom,
            "stock_uom": pr_item.stock_uom,
            "conversion_factor": pr_item.conversion_factor,
            "rate": pr_item.rate,
            "qty": d.get("return_qty"),
            "returnable_quantity": d.get("returnable_qty"),
            "available_serial_nos": "\n".join(sorted(available_serials))
        })

    return result