# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from franchise_erp.utils.fy_naming import company_fy_autoname

class GateEntry(Document):

    def autoname(self):

        # 🔥 VERY IMPORTANT (bypass ERP validation)
        self.naming_series = None

        frappe.logger().info("Incoming Logistic autoname triggered")

        company_fy_autoname(self)
          
    # def on_submit(self):
    #     self.status = "Submitted"
    #     self.db_update()  # <<<<< ADD THIS LINE

    #     if not self.incoming_logistics:
    #         frappe.throw("Incoming Logistics is required")

    #     il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
    #     il_doc.gate_entry_no = self.name
    #     il_doc.status = "Received" 
    #     il_doc.save(ignore_permissions=True)

    # def on_cancel(self):
    #     self.status = "Cancelled"
    #     self.db_update()  # <<<<< ADD THIS LINE

    #     if not self.incoming_logistics:
    #         return

    #     il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
    #     il_doc.status = "Issued"
    #     il_doc.gate_entry_no = None
    #     il_doc.save(ignore_permissions=True)

    def on_submit(self):
        self.status = "Submitted"
        self.db_update()

        if not self.incoming_logistics:
            frappe.throw("Incoming Logistics is required")

        # --- PURANA LOGIC (Header update) ---
        il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
        il_doc.gate_entry_no = self.name
        il_doc.status = "Received" 
        il_doc.save(ignore_permissions=True)

        # --- NAYA LOGIC (Boxes status update only on Submit) ---
        for item in self.gate_entry_box_barcode:
            frappe.db.set_value("Gate Entry Box Barcode", 
                {"box_barcode": item.box_barcode, "parent": self.incoming_logistics, "parenttype": "Incoming Logistics"}, 
                "status", "Received")

    def on_cancel(self):
        self.status = "Cancelled"
        self.db_update()

        if self.incoming_logistics:
            # --- PURANA LOGIC (Header reset) ---
            il_doc = frappe.get_doc("Incoming Logistics", self.incoming_logistics)
            il_doc.status = "Issued"
            il_doc.gate_entry_no = None
            il_doc.save(ignore_permissions=True)

            # --- NAYA LOGIC (Boxes status reset) ---
            for item in self.gate_entry_box_barcode:
                frappe.db.set_value("Gate Entry Box Barcode", 
                    {"box_barcode": item.box_barcode, "parent": self.incoming_logistics, "parenttype": "Incoming Logistics"}, 
                    "status", "Pending")

    def on_trash(self):
        # 🔥 NAYA LOGIC: Draft delete hone par boxes ko release karein
        if self.incoming_logistics:
            for item in self.gate_entry_box_barcode:
                frappe.db.set_value("Gate Entry Box Barcode", 
                    {"box_barcode": item.box_barcode, "parent": self.incoming_logistics, "parenttype": "Incoming Logistics"}, 
                    "status", "Pending")

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

    party_type = None
    party = None

    if il.type:
        type_doc = frappe.get_doc("Incoming Logistics Type", il.type)

        # Supplier case
        if type_doc.is_supplier:
            party_type = "Supplier"
            if il.consignor:
                party = frappe.db.get_value("Supplier", il.consignor, "name")

        # Customer case
        elif type_doc.is_customer:
            party_type = "Customer"
            if il.consignor_customer:
                party = frappe.db.get_value("Customer", il.consignor_customer, "name")

    return {
        "incoming_logistics": il.name,
        "type": il.type,
        "lr_quantity": il.lr_quantity,
        "document_no": il.lr_document_no,
        "declaration_amount": il.declaration_amount,
        "qty_as_per_invoice": il.received_qty,

        "party_type": party_type,
        "party": party,

        "purchase_orders": [
            {
                "reference_doctype": row.source_doctype,
                "reference_name": row.source_name
            }
            for row in il.references
        ],

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
# @frappe.whitelist()
# def mark_box_barcode_received(box_barcode, incoming_logistics_no):

    if not box_barcode or not incoming_logistics_no:
        frappe.throw("Missing barcode or Incoming Logistics No")

    box_barcode = box_barcode.strip().upper()

    row = frappe.db.sql("""
        SELECT name, status
        FROM `tabGate Entry Box Barcode`
        WHERE UPPER(TRIM(box_barcode)) = %s
        AND incoming_logistics_no = %s
        LIMIT 1
    """, (box_barcode, incoming_logistics_no), as_dict=True)

    if not row:
        frappe.throw("Invalid Box Barcode")

    row = row[0]

    if row.status == "Received":
        frappe.throw("Box already Received")

    frappe.db.set_value(
        "Gate Entry Box Barcode",
        row.name,
        {
            "status": "Received",
            "scan_date_time": frappe.utils.now_datetime()
        }
    )

    return {
        "status": "Received",
        "box_barcode": box_barcode,
        "name": row.name
    }

@frappe.whitelist()
def mark_box_barcode_received(box_barcode, incoming_logistics_no):
    if not box_barcode or not incoming_logistics_no:
        frappe.throw("Missing barcode or Incoming Logistics No")

    barcode = box_barcode.strip().upper()

    row = frappe.db.sql("""
        SELECT name, status
        FROM `tabGate Entry Box Barcode`
        WHERE UPPER(TRIM(box_barcode)) = %s
        AND incoming_logistics_no = %s
        LIMIT 1
    """, (barcode, incoming_logistics_no), as_dict=True)

    if not row:
        frappe.throw("Invalid Box Barcode")

    row = row[0]
    
    # Validation: Check if already received in database
    if row.status == "Received":
        frappe.throw("Box already Received")

    # 🔥 NOTE: Database update removed from here to prevent early status change
    return {"status": "Success", "box_barcode": barcode}

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




# @frappe.whitelist()
# def make_pr_from_gate_entry(gate_entry):
#     import erpnext.buying.doctype.purchase_order.purchase_order as po

#     ge = frappe.get_doc("Gate Entry", gate_entry)

#     # po_list = list(set(
#     #     row.purchase_order for row in ge.purchase_ids if row.purchase_order
#     # ))

#     po_list = list(set(
#         row.purchase_order for row in ge.references if row.source_name
#     ))

#     if not po_list:
#         frappe.throw("No Purchase Order linked with Gate Entry")

#     pr = None

#     for po_name in po_list:
#         mapped_pr = po.make_purchase_receipt(po_name)

#         if not pr:
#             pr = mapped_pr
#         else:
#             for item in mapped_pr.items:
#                 pr.append("items", item)

#     # 🔗 LINK GATE ENTRY AT DOCUMENT LEVEL
#     pr.custom_bulk_gate_entry = gate_entry

#     # 🔗 LINK GATE ENTRY AT ITEM LEVEL
#     for item in pr.items:
#         item.custom_bulk_gate_entry = gate_entry

#         # (These are already mapped by ERP, but safe check)
#         item.purchase_order = item.purchase_order
#         item.purchase_order_item = item.purchase_order_item

#     # 🔥 Recalculate taxes & totals
#     pr.run_method("calculate_taxes_and_totals")

#     return pr
@frappe.whitelist()
def make_pr_from_gate_entries(gate_entries):
    import json
    import erpnext.buying.doctype.purchase_order.purchase_order as po

    # ✅ handle input
    if isinstance(gate_entries, str):
        try:
            gate_entries = json.loads(gate_entries)
        except:
            gate_entries = [gate_entries]

    if not isinstance(gate_entries, list):
        gate_entries = [gate_entries]

    if not gate_entries:
        frappe.throw("No Gate Entries selected")

    all_po_list = []
    po_gate_map = {}   # 🔥 PO → Gate Entry mapping

    # 🔁 STEP 1: collect PO + mapping
    for gate_entry in gate_entries:
        ge = frappe.get_doc("Gate Entry", gate_entry)

        for row in ge.references:
            if row.source_doctype == "Purchase Order" and row.source_name:

                po_name = row.source_name

                if po_name not in all_po_list:
                    all_po_list.append(po_name)

                # 🔥 map PO → Gate Entry
                po_gate_map[po_name] = gate_entry

    if not all_po_list:
        frappe.throw("No Purchase Orders linked")

    pr = None

    # 🔁 STEP 2: use ERPNext mapping
    for po_name in all_po_list:
        mapped_pr = po.make_purchase_receipt(po_name)

        if not pr:
            pr = mapped_pr

            # 🔥 FIX FIRST PR ITEMS
            for item in pr.items:
                item.custom_bulk_gate_entry = po_gate_map.get(item.purchase_order)

        else:
            for item in mapped_pr.items:
                item.idx = 0

                # 🔥 SET CORRECT GATE ENTRY PER ITEM
                item.custom_bulk_gate_entry = po_gate_map.get(po_name)

                pr.append("items", item)

    # 🔗 STEP 3: header level (multiple allowed)
    pr.custom_bulk_gate_entry = ", ".join(gate_entries)

    # 🔥 STEP 4: fix numbering
    for i, item in enumerate(pr.items, start=1):
        item.idx = i

    # 🔥 STEP 5: recalc
    pr.run_method("set_missing_values")
    pr.run_method("calculate_taxes_and_totals")

    return pr
# @frappe.whitelist()
# def make_pr_from_gate_entry(gate_entry):
#     import erpnext.buying.doctype.purchase_order.purchase_order as po

#     ge = frappe.get_doc("Gate Entry", gate_entry)

#     # ✅ Collect unique Purchase Orders from references table
#     po_list = list(set(
#         row.source_name
#         for row in ge.references
#         if row.source_doctype == "Purchase Order" and row.source_name
#     ))

#     if not po_list:
#         frappe.throw("No Purchase Order linked with Gate Entry")

#     pr = None

#     for po_name in po_list:
#         mapped_pr = po.make_purchase_receipt(po_name)

#         if not pr:
#             pr = mapped_pr
#         else:
#             for item in mapped_pr.items:
#                 pr.append("items", item)

#     # 🔗 LINK GATE ENTRY AT DOCUMENT LEVEL
#     pr.custom_bulk_gate_entry = gate_entry

#     # 🔗 LINK GATE ENTRY AT ITEM LEVEL
#     for item in pr.items:
#         item.custom_bulk_gate_entry = gate_entry

#         # safe-guard (already mapped by ERPNext)
#         item.purchase_order = item.purchase_order
#         item.purchase_order_item = item.purchase_order_item

#     # 🔥 Recalculate taxes & totals
#     pr.run_method("calculate_taxes_and_totals")

#     return pr



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

@frappe.whitelist()
def get_gate_entries_match_from_pi(supplier):

    # 🔥 Step 1: Incoming Logistics filter (MAIN FIX HERE)
    incoming = frappe.get_all(
        "Incoming Logistics",
        filters={
            "to_pay": "Yes",
            "transporter": supplier,
            "gate_entry_no": ["!=", ""]   # ✅ FIX APPLIED HERE
        },
        fields=["name", "transporter", "total_amount"]
    )

    if not incoming:
        return []

    logistics_map = {d.name: d for d in incoming}
    valid_logistics = list(logistics_map.keys())

    # 🔥 Step 2: Already used Gate Entries
    used_gate_entries = frappe.db.sql("""
        SELECT DISTINCT pii.custom_gate_entry
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
        AND pi.supplier = %s
        AND pii.custom_gate_entry IS NOT NULL
        AND pii.custom_gate_entry != ''
    """, (supplier,), as_dict=1)

    used_list = [d.custom_gate_entry for d in used_gate_entries]

    # 🔥 Step 3: Gate Entry filter
    filters = {
        "docstatus": 1,
        "incoming_logistics": ["in", valid_logistics]
    }

    if used_list:
        filters["name"] = ["not in", used_list]

    gate_entries = frappe.get_all(
        "Gate Entry",
        filters=filters,
        fields=[
            "name",
            "incoming_logistics",
            "transport_service_item",
            "consignor"
        ]
    )

    # 🔥 Attach transporter + total_amount
    for d in gate_entries:
        logistics = logistics_map.get(d["incoming_logistics"])
        d["transporter"] = logistics.transporter if logistics else ""
        d["total_amount"] = logistics.total_amount if logistics else 0

    return gate_entries