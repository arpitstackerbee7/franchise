import frappe
from frappe.model.document import Document


class GateOut(Document):

    def on_update(self):
        self.update_gate_out_flag()

    def update_gate_out_flag(self):
        barcodes = {
            row.box_barcode.strip()
            for row in self.gate_out_box_barcode
            if row.box_barcode
        }

        frappe.msgprint(f"Barcodes Found: {barcodes}")

        if not barcodes:
            frappe.msgprint("No barcodes found ❌")
            return

        frappe.db.sql("""
            UPDATE `tabOutgoing Logistics`
            SET is_gate_out = 1
            WHERE name IN %(barcodes)s
        """, {"barcodes": tuple(barcodes)})

        frappe.db.commit()

        frappe.msgprint("Update Done ✅")




@frappe.whitelist()
def get_pending_outgoing_logistics():
    
    # ✅ All submitted outgoing logistics
    all_logs = frappe.get_all(
        "Outgoing Logistics",
        filters={"docstatus": 1},
        fields=["name"]
    )

    # ✅ Already used in Gate Out
    used_logs = frappe.get_all(
        "Gate Out Box Barcode",
        fields=["box_barcode"]
    )

    used_names = {d.box_barcode for d in used_logs}

    # ✅ Filter pending
    pending = [d for d in all_logs if d.name not in used_names]

    return pending