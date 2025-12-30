# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GateEntry(Document):
    pass

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

# after scan update status in doctype and table both
import frappe

# @frappe.whitelist()
# def mark_box_barcode_received(incoming_logistics_no, box_barcode):
#     if not incoming_logistics_no or not box_barcode:
#         frappe.throw("Incoming Logistics No and Box Barcode are required")

#     # Find exact matching record
#     docname = frappe.db.get_value(
#         "Gate Entry Box Barcode",
#         {
#             "incoming_logistics_no": incoming_logistics_no,
#             "box_barcode": box_barcode
#         },
#         "name"
#     )

#     if not docname:
#         frappe.throw("Barcode does not belong to this Incoming Logistics")

#     current_status = frappe.db.get_value(
#         "Gate Entry Box Barcode",
#         docname,
#         "status"
#     )

#     if current_status == "Received":
#         frappe.throw("This box is already Received")

#     # Update status
#     frappe.db.set_value(
#         "Gate Entry Box Barcode",
#         docname,
#         "status",
#         "Received"
#     )

#     frappe.db.commit()

#     return "UPDATED"

#update status only for box barcode table
import frappe

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


import frappe
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def create_purchase_receipt(gate_entry):
    gate_entry_doc = frappe.get_doc("Gate Entry", gate_entry)

    if not gate_entry_doc.purchase_order:
        frappe.throw("Purchase Order is not linked in Gate Entry")

    # 🔥 Map Purchase Order → Purchase Receipt
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
                }
            }
        }
    )

    # 🔹 Custom Linking
    pr.custom_gate_entry = gate_entry_doc.name
    pr.posting_date = gate_entry_doc.date
    pr.set_posting_time = 1

    # Optional but useful
    pr.supplier = gate_entry_doc.consignor
    pr.company = gate_entry_doc.owner_site

    pr.insert(ignore_permissions=True)

    return pr.name
