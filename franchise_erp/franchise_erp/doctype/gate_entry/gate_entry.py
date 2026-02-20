# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class GateEntry(Document):
            
    def on_submit(self):
        self.status = "Submitted"
        self.db_update()  # <<<<< ADD THIS LINE

        if not self.incoming_logistics:
            frappe.throw("Incoming Logistics is required")

        il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
        il_doc.gate_entry_no = self.name
        il_doc.status = "Received" 
        il_doc.save(ignore_permissions=True)

    def on_cancel(self):
        self.status = "Cancelled"
        self.db_update()  # <<<<< ADD THIS LINE

        if not self.incoming_logistics:
            return

        il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
        il_doc.status = "Issued"
        il_doc.gate_entry_no = None
        il_doc.save(ignore_permissions=True)

# fetch box barcode list
# @frappe.whitelist()
# def get_data_for_gate_entry(incoming_logistics):
#     il = frappe.get_doc("Incoming Logistics", incoming_logistics)

#     return {
#         # -------- Header Fields --------
#         "lr_quantity": il.lr_quantity,
#          "type": il.type,
#           "lr_quantity": il.lr_quantity,
#         "document_no": il.lr_document_no,
#         "declaration_amount": il.declaration_amount,
#         "qty_as_per_invoice":il.received_qty,

#         # -------- Purchase Orders --------
#         "purchase_orders": [
#             {
#                 "purchase_order": row.purchase_order
#             }
#             for row in il.purchase_ids
#         ],

#         # -------- Box Barcodes --------
#         "box_barcodes": [
#             {
#                 "box_barcode": row.box_barcode,
#                 "incoming_logistics_no": row.incoming_logistics_no,
#                 "status": row.status
#             }
#             for row in il.gate_entry_box_barcode
#         ]
#     }
import frappe

@frappe.whitelist()
def get_data_for_gate_entry(incoming_logistics):

    il = frappe.get_doc("Incoming Logistics", incoming_logistics)

    # -------------------------------------------------
    # 🔹 Detect party based on Incoming Logistics Type
    # -------------------------------------------------
    party_type = None
    party = None

    if il.type:
        type_doc = frappe.get_doc("Incoming Logistics Type", il.type)

        if getattr(type_doc, "is_supplier", 0):
            party_type = "Supplier"
            party = il.consignor

        elif getattr(type_doc, "is_customer", 0):
            party_type = "Customer"
            party = il.customer or il.consignor_customer

    # -------------------------------------------------
    # 🔹 Build response
    # -------------------------------------------------
    return {
        # -------- Header Fields --------
        "incoming_logistics": il.name,
        "type": il.type,
        "lr_quantity": il.lr_quantity,
        "document_no": il.lr_document_no,
        "declaration_amount": il.declaration_amount,
        "qty_as_per_invoice": il.received_qty,

        # -------- Party Logic --------
        "party_type": party_type,   # Supplier / Customer
        "party": party,

        # -------- References (🔥 KEY MATCH FIX) --------
        "purchase_orders": [
            {
                "reference_doctype": row.source_doctype,
                "reference_name": row.source_name
            }
            for row in il.references
        ],

        # -------- Box Barcodes --------
        "box_barcodes": [
            {
                "box_barcode": row.box_barcode,
                "incoming_logistics_no": row.incoming_logistics_no,
                "status": row.status
            }
            for row in il.gate_entry_box_barcode
        ]
    }

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


# @frappe.whitelist()
# def create_purchase_receipt(gate_entry):
#     gate_entry_doc = frappe.get_doc("Gate Entry", gate_entry)

#     if not gate_entry_doc.purchase_order:
#         frappe.throw("Purchase Order is not linked in Gate Entry")

#     def update_item(source, target, source_parent):
#         target.qty = 0
#         target.received_qty = 0
#         target.stock_qty = 0
#         target.serial_no = ""
#         return target

#     pr = get_mapped_doc(
#         "Purchase Order",
#         gate_entry_doc.purchase_order,
#         {
#             "Purchase Order": {
#                 "doctype": "Purchase Receipt",
#                 "field_map": {"name": "purchase_order"}
#             },
#             "Purchase Order Item": {
#                 "doctype": "Purchase Receipt Item",
#                 "field_map": {
#                     "name": "purchase_order_item",
#                     "parent": "purchase_order",
#                 },
#                 "postprocess": update_item,
#             }
#         }
#     )

#     # Gate Entry linking
#     pr.custom_gate_entry = gate_entry_doc.name
#     pr.posting_date = gate_entry_doc.date
#     pr.set_posting_time = 1
#     pr.supplier = gate_entry_doc.consignor
#     pr.company = gate_entry_doc.owner_site

#     # 🔥 VERY IMPORTANT
#     pr.name = None
#     pr.__islocal = 1

#     return pr.as_dict()


@frappe.whitelist()
def get_gate_entry_with_pos(supplier=None):
    filters = {"docstatus": 1}
    if supplier:
        filters["consignor"] = supplier

    gate_entries = frappe.get_all(
        "Gate Entry",
        filters=filters,
        fields=["name", "owner_site"]
    )

    result = []

    for ge in gate_entries:
        ge_doc = frappe.get_doc("Gate Entry", ge.name)
        # Check if Purchase Orders exist in the child table
        if ge_doc.get("purchase_ids"):
            for po in ge_doc.get("purchase_ids"):
                result.append({
                    "gate_entry": ge.name,
                    "purchase_order": po.purchase_order,
                    "owner_site": ge.owner_site
                })

    return result


# @frappe.whitelist()
# def get_po_items_from_gate_entry(gate_entry):

#     ge = frappe.get_doc("Gate Entry", gate_entry)

#     po_list = [
#         row.purchase_order
#         for row in ge.purchase_ids
#         if row.purchase_order
#     ]

#     if not po_list:
#         return []

#     po_items = frappe.get_all(
#         "Purchase Order Item",
#         filters={
#             "parent": ["in", po_list]
#         },
#         fields=[
#             "name",
#             "parent as purchase_order",
#             "item_code",
#             "item_name",
#             "stock_uom",
#             "uom",
#             "conversion_factor",
#             "rate",
#             "warehouse"
#         ]
#     )

#     return po_items




@frappe.whitelist()
def make_pr_from_gate_entry(gate_entry):
    import erpnext.buying.doctype.purchase_order.purchase_order as po

    ge = frappe.get_doc("Gate Entry", gate_entry)

    po_list = list(set(
        row.purchase_order for row in ge.purchase_ids if row.purchase_order
    ))

    if not po_list:
        frappe.throw("No Purchase Order linked with Gate Entry")

    pr = None

    for po_name in po_list:
        mapped_pr = po.make_purchase_receipt(po_name)

        if not pr:
            pr = mapped_pr
        else:
            for item in mapped_pr.items:
                pr.append("items", item)

    # 🔗 LINK GATE ENTRY AT DOCUMENT LEVEL
    pr.custom_bulk_gate_entry = gate_entry

    # 🔗 LINK GATE ENTRY AT ITEM LEVEL
    for item in pr.items:
        item.custom_bulk_gate_entry = gate_entry

        # (These are already mapped by ERP, but safe check)
        item.purchase_order = item.purchase_order
        item.purchase_order_item = item.purchase_order_item

    # 🔥 Recalculate taxes & totals
    pr.run_method("calculate_taxes_and_totals")

    return pr

# @frappe.whitelist()
# def get_pending_gate_entries(supplier):
#     result = []

#     gate_entries = frappe.get_all(
#         "Gate Entry",
#         filters={
#             "consignor": supplier,
#             "docstatus": 1
#         },
#         fields=["name", "quantity_as_per_invoice"]
#     )

#     for ge in gate_entries:
#         # total received qty from Purchase Receipt
#         received_qty = frappe.db.sql("""
#             SELECT IFNULL(SUM(pri.qty), 0)
#             FROM `tabPurchase Receipt Item` pri
#             WHERE pri.custom_bulk_gate_entry = %s
#               AND pri.docstatus < 2
#         """, ge.name)[0][0]

#         # 🔑 show only if pending qty exists
#         if received_qty < ge.quantity_as_per_invoice:
#             result.append({
#                 "gate_entry": ge.name,
#                 "pending_qty": ge.quantity_as_per_invoice - received_qty
#             })

#     return result

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_pending_gate_entries(supplier):
    result = []

    gate_entries = frappe.get_all(
        "Gate Entry",
        filters={
            "consignor": supplier,
            "docstatus": 1
        },
        fields=["name", "quantity_as_per_invoice"]
    )

    for ge in gate_entries:
        # total received qty from Purchase Receipt
        received_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(pri.qty), 0)
            FROM `tabPurchase Receipt Item` pri
            WHERE pri.custom_bulk_gate_entry = %s
              AND pri.docstatus < 2
        """, ge.name)[0][0]

        received_qty = flt(received_qty)
        invoice_qty = flt(ge.quantity_as_per_invoice)

        # 🔑 show only if pending qty exists
        if received_qty < invoice_qty:
            result.append({
                "gate_entry": ge.name,
                "pending_qty": invoice_qty - received_qty
            })

    return result


def validate(self):
    if not self.references or len(self.references) == 0:
        frappe.throw("At least one Reference is required before saving.")
