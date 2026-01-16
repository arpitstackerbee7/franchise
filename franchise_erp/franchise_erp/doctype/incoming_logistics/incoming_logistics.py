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
    def validate(self):
        self.validate_unique_lr_per_transporter()
        self.validate_unique_invoice_per_consignor()


    def on_submit(self):
        # Loop through all linked Purchase Orders
        for po_link in self.purchase_ids:
            if not po_link.purchase_order:
                continue

            # Get the Purchase Order document
            po = frappe.get_doc("Purchase Order", po_link.purchase_order)

            # Loop through items in PO and map Incoming Logistics ID
            for po_item in po.items:
                po_item.custom_incoming_logistic = self.name

            # Save the PO with updated field
            po.save(ignore_permissions=True)

    # def validate(self):

    #     self.validate_unique_lr_per_transporter()

    #     if not self.purchase_ids or not self.received_qty:
    #         return

    #     total_po_qty = 0
    #     po_details = []

    #     # 🔹 Sum ALL PO item qty
    #     for row in self.purchase_ids:
    #         if not row.purchase_order:
    #             continue

    #         po = frappe.get_doc("Purchase Order", row.purchase_order)
    #         po_qty = sum(flt(item.qty) for item in po.items)

    #         total_po_qty += po_qty
    #         po_details.append(f"{row.purchase_order} → {po_qty}")

    #     # 🔹 ONLY current document received qty
    #     current_received = flt(self.received_qty)

    #     # ❌ Validation
    #     if current_received > total_po_qty:
    #         frappe.throw(
    #             f"""
    #             ❌ <b>Received Qty Invalid</b><br><br>

    #             <b>Purchase Order Qty:</b><br>
    #             {'<br>'.join(po_details)}<br><br>

    #             <b>Total PO Qty:</b> {total_po_qty}<br>
    #             <b>Entered Received Qty:</b> {current_received}<br><br>

    #             """
    #         )


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
        if not self.transporter or not self.lr_document_no:
            return

        duplicate = frappe.db.exists(
            "Incoming Logistics",
            {
                "transporter": self.transporter,
                "lr_document_no": self.lr_document_no,
                "name": ["!=", self.name],
                "docstatus": ["<", 2]
            }
        )

        if duplicate:
            frappe.throw(
                title="Duplicate LR Document No",
                msg=(
                    f"LR Document No <b>{self.lr_document_no}</b> "
                    f"already exists for Transporter <b>{self.transporter}</b>."
                )
            )

    def validate_unique_invoice_per_consignor(self):
        if not self.consignor or not self.invoice_no:
            return

        duplicate = frappe.db.exists(
            "Incoming Logistics",
            {
                "consignor": self.consignor,
                "invoice_no": self.invoice_no,
                "name": ["!=", self.name],
                "docstatus": ["<", 2]
            }
        )

        if duplicate:
            frappe.throw(
                title="Duplicate Invoice No",
                msg=(
                    f"Invoice No <b>{self.invoice_no}</b> "
                    f"already exists for Consignor <b>{self.consignor}</b>."
                )
            )