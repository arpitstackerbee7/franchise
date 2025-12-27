# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class IncomingLogistics(Document):

    def on_submit(self):
        self.create_gate_entry_box_barcodes()

    def create_gate_entry_box_barcodes(self):
        qty = int(self.received_qty or 0)
        if qty <= 0:
            return

        # Prevent duplicate creation
        existing = frappe.db.count(
            "Gate Entry Box Barcode",
            {"incoming_logistics_no": self.name}
        )
        if existing:
            return

        # Ensure the child table exists
        if not hasattr(self, "gate_entry_boxes"):
            self.gate_entry_boxes = []

        for i in range(qty):
            box_no = i + 1                      # 1,2,3...
            total = qty                        # total boxes


            # 01, 02, 03 formatting
            box_no_str = str(box_no).zfill(2)

            # IL-01/10 format
            box_barcode_name = f"IL-{box_no_str}"
            total_box_barcode = total
            # Create Gate Entry Box Barcode
            frappe.get_doc({
                "doctype": "Gate Entry Box Barcode",
                "incoming_logistics_no": self.name,
                "box_barcode": box_barcode_name,
                "total_barcode": total_box_barcode,
                "status": "Pending"
            }).insert(ignore_permissions=True)

            # Append to child table with the generated barcode
            # self.append("gate_entry_boxes", {
            #     "gate_entry_box": box_barcode_name  # store generated box_barcode here
            # })

        # Save parent document to persist child table
        self.save(ignore_permissions=True)

