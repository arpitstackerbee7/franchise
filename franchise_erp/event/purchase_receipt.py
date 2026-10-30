import frappe
from frappe import _


def get_gate_entries(doc):
    """Gate Entry IDs from PR level and item level (bulk gate entry)."""
    ids = set()
    if doc.get("custom_gate_entry"):
        ids.add(doc.get("custom_gate_entry"))
    for row in doc.get("items") or []:
        if row.get("custom_bulk_gate_entry"):
            ids.add(row.get("custom_bulk_gate_entry"))
    return ids


def incoming_logistics_exists(gate_entry):
    """True if a non-cancelled Incoming Logistics is linked to this Gate Entry."""
    if not frappe.db.exists("Gate Entry", gate_entry):
        return False

    # 1. Gate Entry points to an Incoming Logistics
    il = frappe.db.get_value("Gate Entry", gate_entry, "incoming_logistics")
    if il and frappe.db.exists(
        "Incoming Logistics", {"name": il, "docstatus": ["!=", 2]}
    ):
        return True

    # 2. Incoming Logistics points back to the Gate Entry
    return bool(
        frappe.get_all(
            "Incoming Logistics",
            filters={"docstatus": ["!=", 2]},
            or_filters=[
                ["gate_entry_no", "=", gate_entry],
                ["select_gate_entry", "=", gate_entry],
            ],
            limit=1,
            pluck="name",
        )
    )


def validate_mandatory_links(doc, method=None):
    # Skip for return / debit note
    if doc.is_return:
        return

    missing = []

    # 1. Purchase Order (item table field)
    if not any(row.get("purchase_order") for row in doc.get("items") or []):
        missing.append(_("Purchase Order"))

    # 2. Gate Entry (PR level ya item level bulk gate entry)
    gate_entries = get_gate_entries(doc)
    if not gate_entries:
        missing.append(_("Gate Entry"))
    # 3. Incoming Logistics (har Gate Entry ke liye)
    elif not all(incoming_logistics_exists(ge) for ge in gate_entries):
        missing.append(_("Incoming Logistics"))

    if missing:
        frappe.throw(
            _("Purchase Receipt cannot be created or submitted without: {0}").format(
                ", ".join(missing)
            ),
            title=_("Mandatory Links Missing"),
        )