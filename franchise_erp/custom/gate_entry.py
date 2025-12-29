import frappe
from frappe.model.document import Document

def on_submit(doc, method):
    if not doc.incoming_logistics:
        frappe.throw("Incoming Logistics is required")

    il_doc = frappe.get_doc("Incoming Logistics", doc.incoming_logistics)
    if not il_doc:
        frappe.throw("Invalid Incoming Logistics reference")

    # Update fields
    il_doc.status = "Received"
    il_doc.gate_entry_no = doc.name
    il_doc.save()
    il_doc.reload()  # Reload to ensure cache is updated


def on_cancel(doc, method):
    if doc.incoming_logistics:
        il_doc = frappe.get_doc("Incoming Logistics", doc.incoming_logistics)
        if il_doc:
            il_doc.status = "Issued"
            il_doc.gate_entry_no = None
            il_doc.save()
            il_doc.reload()
