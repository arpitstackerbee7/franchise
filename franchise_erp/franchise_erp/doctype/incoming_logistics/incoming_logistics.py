# Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt
# import frappe
# from frappe.model.document import Document

# class IncomingLogistics(Document):

#     # Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt

import frappe
import random
from frappe.model.document import Document, flt

class IncomingLogistics(Document):

    def on_submit(self):
        # Loop through all linked Purchase Orders
        for po_link in self.purchase_order_id:
            if not po_link.purchase_order:
                continue

            # Get the Purchase Order document
            po = frappe.get_doc("Purchase Order", po_link.purchase_order)

            # Loop through items in PO and map Incoming Logistics ID
            for po_item in po.items:
                po_item.custom_incoming_logistic = self.name

            # Save the PO with updated field
            po.save(ignore_permissions=True)

    def validate(self):
    # Existing validation
        self.validate_unique_lr_per_transporter()

        # ❗ Purchase Order now comes from CHILD TABLE
        if not self.purchase_order_id or not self.received_qty:
            return

        # Collect unique Purchase Orders from child table
        purchase_orders = {
            row.purchase_order
            for row in self.purchase_order_id
            if row.purchase_order
        }

        # Safety check
        if not purchase_orders:
            return

        # Assumption: One PO per Incoming Logistics
        purchase_order = list(purchase_orders)[0]

        # 🔹 Fetch Purchase Order
        po = frappe.get_doc("Purchase Order", purchase_order)

        # 🔹 Total PO Quantity
        po_total_qty = sum(flt(item.qty) for item in po.items)

        # 🔹 Already received qty from PREVIOUS Incoming Logistics
        already_received = frappe.db.sql("""
            SELECT SUM(il.received_qty)
            FROM `tabIncoming Logistics` il
            INNER JOIN `tabPurchase Order ID` poi
                ON poi.parent = il.name
            WHERE poi.purchase_order = %s
            AND il.docstatus = 1
            AND il.name != %s
        """, (purchase_order, self.name))[0][0] or 0

        # 🔹 Total including current document
        total_received = already_received + flt(self.received_qty)

        # ❌ Validation
        if total_received > po_total_qty:
            frappe.throw(
                f"Received Qty ({total_received}) cannot be greater than "
                f"Purchase Order Qty ({po_total_qty})"
            )



    def before_submit(self):
        self.create_gate_entry_box_barcodes()
    def create_gate_entry_box_barcodes(self):
        qty = int(self.lr_quantity or 0)
        if qty <= 0:
            return

        # 🔒 Prevent duplicate creation
        existing = frappe.db.count(
            "Gate Entry Box Barcode",
            {"incoming_logistics_no": self.name}
        )
        if existing > 0:
            return

        # 🔹 Get prefix from TZU Setting (IG)
        prefix = frappe.db.get_single_value(
            "TZU Setting",
            "box_barcode_series"
        )

        if not prefix:
            frappe.throw("Box Barcode Series not configured in TZU Setting")

        # 🔹 Extract numeric part from Incoming Logistics name
        # TPL-IL-00125-2025-2026 → 00125
        try:
            series_no = self.name.split("-")[2]
        except Exception:
            frappe.throw("Invalid Incoming Logistics Naming Series")

        padding = max(2, len(str(qty)))

        for i in range(qty):
            box_no = str(i + 1).zfill(padding)

            self.append("gate_entry_box_barcode", {
                "incoming_logistics_no": self.name,
                "box_barcode": f"{prefix}-{series_no}-{box_no}",
                "total_barcode_qty": qty,
                "status": "Pending"
            })



    def validate_unique_lr_per_transporter(self):
        # Skip if values missing
        if not self.transporter or not self.lr_document_no:
            return

        duplicate = frappe.db.exists(
            "Incoming Logistics",
            {
                "transporter": self.transporter,
                "lr_document_no": self.lr_document_no,
                "name": ["!=", self.name],
                "docstatus": ["<", 2]   # Draft + Submitted
            }
        )

        if duplicate:
            frappe.throw(
                title="Duplicate LR Document No",
                msg=(
                    f"LR Document No <b>{self.lr_document_no}</b> "
                    f"already exists for Transporter <b>{self.transporter}</b>.<br><br>"
                    "Please use a different LR Document No."
                )
            )