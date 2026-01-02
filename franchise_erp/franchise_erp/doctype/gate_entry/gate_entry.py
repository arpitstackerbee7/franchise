# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import frappe
from frappe.model.document import Document

class GateEntry(Document):

    def before_save(self):
        # 🔹 Document No set
        # if not self.document_no:
        #     self.document_no = self.name

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
        target.qty = 0
        target.received_qty = 0
        target.stock_qty = 0
        target.serial_no = ""
        return target

    pr = get_mapped_doc(
        "Purchase Order",
        gate_entry_doc.purchase_order,
        {
            "Purchase Order": {
                "doctype": "Purchase Receipt",
                "field_map": {"name": "purchase_order"}
            },
            "Purchase Order Item": {
                "doctype": "Purchase Receipt Item",
                "field_map": {
                    "name": "purchase_order_item",
                    "parent": "purchase_order",
                },
                "postprocess": update_item,
            }
        }
    )

    # Gate Entry linking
    pr.custom_gate_entry = gate_entry_doc.name
    pr.posting_date = gate_entry_doc.date
    pr.set_posting_time = 1
    pr.supplier = gate_entry_doc.consignor
    pr.company = gate_entry_doc.owner_site

    # 🔥 VERY IMPORTANT
    pr.name = None
    pr.__islocal = 1

    return pr.as_dict()

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_po_items_from_gate_entry(gate_entry_name):
    """
    Returns Purchase Order items linked to the Gate Entry,
    mapped to Purchase Receipt fields with qty set to 0.
    """
    ge = frappe.get_doc("Gate Entry", gate_entry_name)

    if not ge.purchase_order:
        frappe.throw(f"Gate Entry {ge.name} is not linked to any Purchase Order")

    # Fetch relevant fields from PO items
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"parent": ge.purchase_order},
        fields=[
            "item_code",
            "item_name",
            "schedule_date",
            "expected_delivery_date",
            "description",
            "qty",
            "uom",
            "price_list_rate",
            "last_purchase_rate",
            "rate",
            "amount",
            "gst_treatment",
            "custom_base_rate_new",
            "apply_tds",
            "taxable_value",
            "warehouse"
        ]
    )

    # Map PO items to PR items
    pr_items = []
    for item in po_items:
        pr_item = {
            "item_code": item.get("item_code"),
            "item_name": item.get("item_name"),
            "schedule_date": item.get("schedule_date"),
            "expected_delivery_date": item.get("expected_delivery_date"),
            "description": item.get("description"),
            "qty": 0,  # Set qty to 0 for PR
            "uom": item.get("uom"),
            "price_list_rate": item.get("price_list_rate"),
            "last_purchase_rate": item.get("last_purchase_rate"),
            "rate": item.get("rate"),
            "amount": item.get("amount"),
            "gst_treatment": item.get("gst_treatment"),
            "custom_base_rate_new": item.get("custom_base_rate_new"),
            "apply_tds": item.get("apply_tds"),
            "taxable_value": item.get("taxable_value"),
            "warehouse": item.get("warehouse"),
            "custom_bulk_gate_entry": ge.name,
            "purchase_order": ge.purchase_order
        }
        pr_items.append(pr_item)

    return pr_items
