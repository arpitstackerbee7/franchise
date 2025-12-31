# Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt
# import frappe
# from frappe.model.document import Document

# class IncomingLogistics(Document):

#     # Copyright (c) 2025, Franchise Erp and contributors
# # For license information, please see license.txt

import frappe
import random
from frappe.model.document import Document

class IncomingLogistics(Document):

    def before_submit(self):
        self.create_gate_entry_box_barcodes()

    # def create_gate_entry_box_barcodes(self):
    #     qty = int(self.lr_quantity or 0)

    #     if qty <= 0:
    #         return

    #     table_field = "gate_entry_box_barcode"

    #     # 🔒 Prevent duplicate creation
    #     if self.get(table_field):
    #         return

    #     box_series = frappe.db.get_single_value(
    #         "TZU Setting",
    #         "box_barcode_series"
    #     )

    #     if not box_series:
    #         frappe.throw("Box Barcode Series not configured in TZU Setting")

    #     padding = max(2, len(str(qty)))
    #     for i in range(qty):
    #         box_no = str(i + 1).zfill(padding)

    #         self.append("gate_entry_box_barcode", {
    #             "incoming_logistics_no": self.name,
    #             "box_barcode": f"{box_series}{box_no}",
    #             "total_barcode_qty": qty,
    #             "status": "Pending"
    #         })


  

    def create_gate_entry_box_barcodes(self):
        qty = int(self.lr_quantity or 0)

        if qty <= 0:
            return

        table_field = "gate_entry_box_barcode"

        # 🔒 DB level duplicate protection
        existing = frappe.db.count(
            "Gate Entry Box Barcode",
            {"incoming_logistics_no": self.name}
        )
        if existing > 0:
            return

        # 🔹 Get series from TZU Setting
        box_series = frappe.db.get_single_value(
            "TZU Setting",
            "box_barcode_series"
        )

        if not box_series:
            frappe.throw("Box Barcode Series not configured in TZU Setting")

        # 🔹 Padding logic
        random_5_digit = random.randint(10000, 99999)
        padding = max(2, len(str(qty)))

        for i in range(qty):
            box_no = str(i + 1).zfill(padding)

            self.append(table_field, {
                "incoming_logistics_no": self.name,
                "box_barcode": f"{box_series}-{random_5_digit}-{box_no}",
                "total_barcode_qty": qty,
                "status": "Pending"
            })