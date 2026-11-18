import frappe
from frappe import _


def _check_po_submitted(po_names):
    for po in set(filter(None, po_names)):
        row = frappe.db.get_value("Purchase Order", po, ["docstatus", "workflow_state"], as_dict=True) or {}
        if row.get("docstatus") != 1 or (row.get("workflow_state") and row.workflow_state != "Approved"):
            frappe.throw(
                _("Purchase Order {0} approved/submit nahi hai. Job Work transaction se pehle PO Approved hona chahiye.").format(
                    frappe.bold(po)
                )
            )


def validate_sco_po_submitted(doc, method=None):
    _check_po_submitted([doc.get("purchase_order")])


def validate_scr_po_submitted(doc, method=None):
    pos = [row.get("purchase_order") for row in doc.get("items", [])]
    if doc.get("subcontracting_order"):
        pos.append(frappe.db.get_value("Subcontracting Order", doc.subcontracting_order, "purchase_order"))
    _check_po_submitted(pos)