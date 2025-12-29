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
def mark_box_barcode_received(box_barcode):
    if not box_barcode:
        frappe.throw("Barcode missing")

    # Check barcode exists
    docname = frappe.db.get_value(
        "Gate Entry Box Barcode",
        {"box_barcode": box_barcode},
        "name"
    )

    if not docname:
        frappe.throw("Invalid Box Barcode")

    current_status = frappe.db.get_value(
        "Gate Entry Box Barcode",
        docname,
        "status"
    )

    if current_status == "Received":
        frappe.throw("This box is already Received")

    # 🔥 DIRECT DB UPDATE (NO CACHE ISSUE)
    frappe.db.set_value(
        "Gate Entry Box Barcode",
        docname,
        "status",
        "Received"
    )

    frappe.db.commit()   # ⚠️ VERY IMPORTANT

    return "UPDATED"
