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
from franchise_erp.utils.fy_naming import company_fy_autoname
class IncomingLogistics(Document):
    
    def autoname(self):

        # 🔥 VERY IMPORTANT (bypass ERP validation)
        self.naming_series = None

        frappe.logger().info("Incoming Logistic autoname triggered")

        company_fy_autoname(self)
        
    def validate(self):
        self.validate_unique_lr_per_transporter()
        self.validate_unique_invoice_per_consignor()
                # Only on new document
        if not self.is_new():
            return

        # Admin bypass
        if frappe.session.user == "Administrator":
            return

        settings = frappe.get_single("TZU Setting")

        allowed_users = [
            row.user
            for row in settings.incoming_logistics_users
            if row.user
        ]

        current_user = frappe.session.user

        if current_user not in allowed_users:

            frappe.throw((
                "You are not authorized to create Incoming Logistics."
            ))


    # def on_submit(self):
    #     # Loop through all linked Purchase Orders
    #     for po_link in self.purchase_ids:
    #         if not po_link.purchase_order:
    #             continue

    #         # Get the Purchase Order document
    #         po = frappe.get_doc("Purchase Order", po_link.purchase_order)

    #         # Loop through items in PO and map Incoming Logistics ID
    #         for po_item in po.items:
    #             po_item.custom_incoming_logistic = self.name

    #         # Save the PO with updated field
    #         po.save(ignore_permissions=True)
   
    def on_submit(self):

     for row in self.references:

        if not row.source_doctype or not row.source_name:
            continue

        # =================================================
        # 🔹 TYPE: JOB RECEIPT
        # =================================================
        if self.type == "Job Receipt":

            if row.source_doctype == "Subcontracting Order":
                frappe.db.sql("""
                    UPDATE `tabSubcontracting Order Item`
                    SET custom_incoming_logistic = %s
                    WHERE parent = %s
                """, (self.name, row.source_name))

            elif row.source_doctype == "Subcontracting Receipt":
                frappe.db.sql("""
                    UPDATE `tabSubcontracting Receipt Item`
                    SET custom_incoming_logistic = %s
                    WHERE parent = %s
                """, (self.name, row.source_name))


        # =================================================
        # 🔹 TYPE: PURCHASE
        # =================================================
        elif self.type == "Purchase":

            if row.source_doctype == "Purchase Order":
                frappe.db.sql("""
                    UPDATE `tabPurchase Order Item`
                    SET custom_incoming_logistic = %s
                    WHERE parent = %s
                """, (self.name, row.source_name))


        # =================================================
        # 🔹 TYPE: SALES RETURN
        # =================================================
        elif self.type == "Sales Return":

            if row.source_doctype == "Sales Invoice":
                frappe.db.sql("""
                    UPDATE `tabSales Invoice Item`
                    SET custom_incoming_logistic = %s
                    WHERE parent = %s
                """, (self.name, row.source_name))


        # =================================================
        # 🔹 TYPE: TRANSFER IN
        # =================================================
        elif self.type == "Transfer In":

            if row.source_doctype == "Stock Entry":
                frappe.db.sql("""
                    UPDATE `tabStock Entry Detail`
                    SET custom_incoming_logistic = %s
                    WHERE parent = %s
                """, (self.name, row.source_name))

    # =====================================================
    # NEW LOGIC: GATE ENTRY UPDATE
    # =====================================================
        gate_entry = self.gate_entry_no

        if not gate_entry:
            frappe.throw("Gate Entry not found in Incoming Logistics")

        if not frappe.db.exists("Gate Entry", gate_entry):
            frappe.throw(f"Gate Entry not found: {gate_entry}")

        # 🔹 TZU Settings
        settings = frappe.get_single("TZU Setting")
        transport_item = settings.transport_service_item

        # 🔹 Parent update
        frappe.db.set_value("Gate Entry", gate_entry, {
            "owner_site": self.owner_site,                
            "type": self.type,
            "gate_entry": 'Yes',
            "date": self.date,
            "consignor": self.consignor,
            "site": self.site,
            "document_no": self.lr_document_no,
            "consignor_customer": self.consignor_customer,
            "incoming_logistics": self.name,
            "transport_service_item": transport_item,
            "document_date": self.lr_date,
            "status": self.status,
            "lr_entry_date": self.lr_date,
            "lr_quantity": self.lr_quantity,
            "declaration_amount": self.total_amount or 0,
            "quantity_as_per_invoice": self.received_qty,
            "remarks": self.remarks
        })

        # 🔹 Child delete
        frappe.db.sql("""
            DELETE FROM `tabOutgoing Logistics Reference`
            WHERE parent = %s
        """, (gate_entry,))

        # 🔹 Child insert
        for row in self.references:
            frappe.get_doc({
                "doctype": "Outgoing Logistics Reference",
                "parent": gate_entry,
                "parenttype": "Gate Entry",
                "parentfield": "references",
                "source_doctype": row.source_doctype,
                "source_name": row.source_name
            }).insert(ignore_permissions=True)
        
        for row in self.gate_entry_box_barcode:

            # ✅ Incoming Logistics child table update
            row.status = "Delivered"

            # ✅ Gate Entry child table update
            frappe.db.set_value(
                "Gate Entry Box Barcode",   # ⚠️ apna actual child table name check kar lena
                {
                    "parent": row.gate_entry,
                    "box_barcode": row.box_barcode
                },
                "status",
                "Delivered"
            )
        
    def before_submit(self):

        if not self.gate_entry_box_barcode:
            frappe.throw("Please scan at least one barcode")

        # ✅ First row gate entry
        first_gate_entry = self.gate_entry_box_barcode[0].gate_entry

        if not first_gate_entry:
            frappe.throw("Gate Entry not found in scanned data")

        # ✅ Set gate_entry_no field
        self.gate_entry_no = first_gate_entry

        # 🔍 Get total barcode count from Gate Entry
        total_barcodes = frappe.db.count(
            "Gate Entry Box Barcode",   # ⚠️ CHANGE if your child table name is different
            {
                "parent": first_gate_entry,
                "status": "Received"   # optional (agar sirf received count karna hai)
            }
        )

        # 🔍 Scanned count
        scanned_count = len(self.gate_entry_box_barcode)

        # ❌ Validation
        if scanned_count < total_barcodes:
            frappe.throw(
                f"❌ Please scan pending barcodes of Gate Entry {first_gate_entry} "
                f"({scanned_count}/{total_barcodes} scanned)"
            )
    
    def on_cancel(self):

        for row in self.gate_entry_box_barcode:

            # 🔄 Incoming Logistics child table
            row.status = "Received"

            # 🔄 Gate Entry child table
            frappe.db.set_value(
                "Gate Entry Box Barcode",
                {
                    "parent": row.gate_entry,
                    "box_barcode": row.box_barcode
                },
                "status",
                "Received"
            )
            
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


    # def before_submit(self):
    #     self.create_gate_entry_box_barcodes()

    # def create_gate_entry_box_barcodes(self):
    #     qty = int(self.lr_quantity or 0)
    #     if qty <= 0:
    #         return

    #     # 🔒 Prevent duplicate creation
    #     existing = frappe.db.count(
    #         "Gate Entry Box Barcode",
    #         {"incoming_logistics_no": self.name}
    #     )
    #     if existing > 0:
    #         return

    #     # 🔹 Get prefix from TZU Setting (IG)
    #     prefix = frappe.db.get_single_value(
    #         "TZU Setting",
    #         "box_barcode_series"
    #     )

    #     if not prefix:
    #         frappe.throw("Box Barcode Series not configured in TZU Setting")

    #     # 🔹 Extract numeric part from Incoming Logistics name
    #     # TPL-IL-00125-2025-2026 → 00125
    #     # try:
    #     #     series_no = self.name.split("/")[2]
    #     # except Exception:
    #     #     frappe.throw("Invalid Incoming Logistics Naming Series")
    #     import re

    #     try:
    #         name = self.name

    #         # ===============================
    #         # 🔥 CASE 1 → New FY format
    #         # IL/26-27/00005
    #         # ===============================
    #         if "/" in name:
    #             parts = name.split("/")
    #             series_no = parts[-1]          # 00005
    #             barcode_prefix = f"{parts[0]}" # IL

    #         # ===============================
    #         # 🔥 CASE 2 → Old format
    #         # TPL-IL-00088-2025-2026
    #         # ===============================
    #         else:
    #             parts = name.split("-")

    #             # TPL-IL-00088-2025-2026
    #             # index: 0   1   2
    #             series_no = parts[2]           # 00088
    #             barcode_prefix = parts[1]      # IL

    #     except Exception:
    #         frappe.throw("Invalid Incoming Logistics Naming Series")

    #     # padding = max(2, len(str(qty)))

    #     # for i in range(qty):
    #     #     box_no = str(i + 1).zfill(padding)

    #     #     self.append("gate_entry_box_barcode", {
    #     #         "incoming_logistics_no": self.name,
    #     #         "box_barcode": f"{prefix}-{series_no}-{box_no}",
    #     #         "total_barcode_qty": qty,
    #     #         "status": "Pending"
    #     #     })
    #     padding = max(2, len(str(qty)))

    #     for i in range(qty):
    #         box_no = str(i + 1).zfill(padding)

    #         self.append("gate_entry_box_barcode", {
    #             "incoming_logistics_no": self.name,
    #             "box_barcode": f"{prefix}-{series_no}-{box_no}",
    #             "total_barcode_qty": qty,
    #             "status": "Pending"
    #         })


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




@frappe.whitelist()
def get_used_source_ids(source_doctype):
    """
    Returns a list of source_names (IDs) already present in the 
    'Outgoing Logistics Reference' table.
    """
    used_ids = frappe.get_all("Outgoing Logistics Reference", 
        filters={
            "parenttype": "Incoming Logistics",
            "source_doctype": source_doctype,
            "docstatus": ["<", 2] # Cancelled documents ko filter se hata deta hai
        }, 
        pluck="source_name"
    )
    return list(set(used_ids))


def before_cancel(self):

    if self.select_gate_entry:

        # 🔹 link remove karo (main fix)
        self.db_set("select_gate_entry", None)

    if self.gate_entry_no:

        # 🔹 optional: Gate Entry se bhi unlink kar do
        frappe.db.set_value("Gate Entry", self.gate_entry_no, {
            "incoming_logistics": None,
        })


@frappe.whitelist()
def process_barcode(scan_barcode, existing_gate_entry=None):

    if not scan_barcode:
        frappe.throw("Please scan barcode")

    # 🔍 Find barcode in ANY Gate Entry
    result = frappe.db.sql("""
        SELECT 
            ge.name as gate_entry,
            gei.box_barcode,
            gei.status
        FROM `tabGate Entry` ge
        JOIN `tabGate Entry Box Barcode` gei ON ge.name = gei.parent
        WHERE gei.box_barcode = %s
        LIMIT 1
    """, (scan_barcode,), as_dict=1)

    if not result:
        frappe.throw("❌ Barcode not found in any Gate Entry")

    data = result[0]

    # ❌ Status check
    if data.status != "Received":
        frappe.throw(f"❌ This barcode is delivered. Check Gate Entry: {data.gate_entry}")

    # ❌ Gate Entry mismatch check
    if existing_gate_entry and existing_gate_entry != data.gate_entry:
        frappe.throw(f"❌ Gate Entry mismatch. Allowed: {existing_gate_entry}")

    return {
        "box_barcode": data.box_barcode,
        "status": data.status,
        "gate_entry": data.gate_entry,
        "scan_date_time": frappe.utils.now_datetime()
    }