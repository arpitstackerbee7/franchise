# Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt
# import frappe
# from frappe.model.document import Document

# class IncomingLogistics(Document):

#     # Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt

import frappe
from frappe.model.document import Document

class IncomingLogistics(Document):

    def before_submit(self):
        self.create_gate_entry_box_barcodes()

    def create_gate_entry_box_barcodes(self):
        qty = int(self.lr_quantity or 0)

        if qty <= 0:
            return

        table_field = "gate_entry_box_barcode"

        # 🔒 Prevent duplicate creation
        if self.get(table_field):
            return

        box_series = frappe.db.get_single_value(
            "TZU Setting",
            "box_barcode_series"
        )

        if not box_series:
            frappe.throw("Box Barcode Series not configured in TZU Setting")

        padding = max(2, len(str(qty)))

        for i in range(qty):
            box_no = str(i + 1).zfill(padding)

            row = self.append(table_field)
            row.incoming_logistics_no = self.name
            row.box_barcode = f"{box_series}{box_no}"
            row.total_barcode_qty = qty   # ✅ correct fieldname
            row.status = "Pending"


    # def on_submit(self):
    #     self.create_gate_entry_box_barcodes()

    # def create_gate_entry_box_barcodes(self): 
    #     qty = int(self.received_qty or 0)

    #     if qty <= 0:
    #         return

    #     # 🔒 Child table fieldname (IMPORTANT)
    #     table_field = "gate_entry_box_barcode"   # Incoming Logistics me jo fieldname hai

    #     # 🚫 Prevent duplicate creation
    #     if self.get(table_field):
    #         return

    #     for i in range(qty):
    #         box_no = str(i + 1).zfill(2)   # 01, 02, 03

    #         self.append(table_field, {
    #             "incoming_logistics_no": self.name,
    #             "box_barcode": f"IL-{box_no}",
    #             "total_barcode": qty,
    #             "status": "Pending"
    #         })

    #     # 🔥 on_submit ke andar ho to save call NAHI chahiye
