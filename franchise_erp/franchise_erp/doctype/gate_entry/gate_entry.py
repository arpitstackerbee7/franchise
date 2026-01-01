# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import frappe
from frappe.model.document import Document

class GateEntry(Document):

    def before_save(self):
        # 🔹 Document No set
        if not self.document_no:
            self.document_no = self.name

        # 🔹 Jab tak submit nahi hua
        if self.docstatus == 0:
            self.status = "Draft"

    def on_submit(self):
        # 🔹 Submit par status
        self.status = "Submitted"

        if not self.incoming_logistics:
            frappe.throw("Incoming Logistics is required")

        il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
        il_doc.status = "Received"
        il_doc.gate_entry_no = self.name
        il_doc.save(ignore_permissions=True)

    def on_cancel(self):
        # 🔹 Cancel par status
        self.status = "Cancelled"

        if not self.incoming_logistics:
            return

        il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
        il_doc.status = "Issued"
        il_doc.gate_entry_no = None
        il_doc.save(ignore_permissions=True)


# fetch box barcode list
@frappe.whitelist()
def get_box_barcodes_for_gate_entry(incoming_logistics):
    """
    Fetch box barcodes for selected Incoming Logistics
    """

    if not incoming_logistics:
        return []

    return frappe.get_all(
        "Gate Entry Box Barcode",
        filters={
            "incoming_logistics_no": incoming_logistics
        },
        fields=[
            "box_barcode",
            "incoming_logistics_no",
            "status"
        ]
    )

#update status only for box barcode table
@frappe.whitelist()
def mark_box_barcode_received(box_barcode, incoming_logistics_no):

    if not box_barcode or not incoming_logistics_no:
        frappe.throw("Missing barcode or Incoming Logistics No")

    # Find matching child row
    row = frappe.db.get_value(
        "Gate Entry Box Barcode",
        {
            "box_barcode": box_barcode,
            "incoming_logistics_no": incoming_logistics_no
        },
        ["name", "status"],
        as_dict=True
    )

    if not row:
        frappe.throw("Invalid Box Barcode")

    if row.status == "Received":
        frappe.throw("Box already Received")

    # Update status + scan datetime
    frappe.db.set_value(
        "Gate Entry Box Barcode",
        row.name,
        {
            "status": "Received",
            "scan_date_time": frappe.utils.now_datetime()
        }
    )

    frappe.db.commit()

    return "OK"


from frappe.model.mapper import get_mapped_doc
import frappe

@frappe.whitelist()
def create_purchase_receipt(gate_entry):
    gate_entry_doc = frappe.get_doc("Gate Entry", gate_entry)

    if not gate_entry_doc.purchase_order:
        frappe.throw("Purchase Order is not linked in Gate Entry")

    def update_item(source, target, source_parent):
        remaining_qty = (source.qty or 0) - (source.received_qty or 0)

        # ❌ Skip item if nothing left
        if remaining_qty <= 0:
            return None

        # ✅ Set qty
        target.qty = remaining_qty
        target.received_qty = remaining_qty
        target.stock_qty = remaining_qty * (source.conversion_factor or 1)

        # ✅ FIX SERIAL NO ISSUE
        if source.serial_no:
            serial_list = [
                s.strip() for s in source.serial_no.split("\n") if s.strip()
            ]

            # qty ke basis par serial_no trim karo
            target.serial_no = "\n".join(serial_list[:int(remaining_qty)])
        else:
            target.serial_no = None

    pr = get_mapped_doc(
        "Purchase Order",
        gate_entry_doc.purchase_order,
        {
            "Purchase Order": {
                "doctype": "Purchase Receipt",
                "field_map": {
                    "name": "purchase_order"
                }
            },
            "Purchase Order Item": {
                "doctype": "Purchase Receipt Item",
                "field_map": {
                    "name": "purchase_order_item",
                    "parent": "purchase_order"
                },
                "postprocess": update_item,
                "condition": lambda doc: (doc.qty or 0) > (doc.received_qty or 0)
            }
        }
    )

    # 🔗 Custom linking
    pr.custom_gate_entry = gate_entry_doc.name
    pr.posting_date = gate_entry_doc.date
    pr.set_posting_time = 1
    pr.supplier = gate_entry_doc.consignor
    pr.company = gate_entry_doc.owner_site

    pr.insert(ignore_permissions=True)
    return pr.name





