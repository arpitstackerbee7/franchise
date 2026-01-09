import frappe
from frappe.utils import flt
from frappe.utils import add_days
from frappe.utils import today

def apply_intercompany_gst(doc, method=None):

    if not doc.is_internal_supplier:
        return

    # -----------------------------
    # 1️⃣ GST % FROM ITEMS
    # -----------------------------
    gst_percent = 0
    for item in doc.items:
        if item.item_tax_template:
            if "5%" in item.item_tax_template:
                gst_percent = 5
            elif "12%" in item.item_tax_template:
                gst_percent = 12
            elif "18%" in item.item_tax_template:
                gst_percent = 18
        if gst_percent:
            break

    if not gst_percent:
        return

    # -----------------------------
    # 2️⃣ IN / OUT STATE
    # -----------------------------
    company_state = frappe.db.get_value(
        "Address", doc.billing_address, "state"
    )
    supplier_state = frappe.db.get_value(
        "Address", doc.supplier_address, "state"
    )

    is_in_state = company_state == supplier_state

    # -----------------------------
    # 3️⃣ COMPANY ABBR
    # -----------------------------
    abbr = frappe.db.get_value("Company", doc.company, "abbr")

    # -----------------------------
    # 4️⃣ SET PURCHASE TAX TEMPLATE
    # -----------------------------
    if is_in_state:
        doc.taxes_and_charges = f"Input GST In-state - {abbr}"
    else:
        doc.taxes_and_charges = f"Input GST Out-state - {abbr}"

    # -----------------------------
    # 5️⃣ FORCE TAX TABLE REBUILD
    # -----------------------------
    doc.set_taxes()
    doc.calculate_taxes_and_totals()

from frappe.utils import  getdate

def set_buffer_due_date(doc, method):
    if not doc.supplier or not doc.due_date:
        return

    buffer_days = frappe.db.get_value(
        "Supplier",
        doc.supplier,
        "custom_buffer_time_allowed"
    )

    if not buffer_days:
        return

    # Ensure date object
    due_date = getdate(doc.due_date)

    doc.custom_buffer_due_date = add_days(due_date, int(buffer_days))


@frappe.whitelist()
def create_pi_from_gate_entry(gate_entry):
    gate = frappe.get_doc("Gate Entry", gate_entry)

    if gate.docstatus != 1:
        frappe.throw("Gate Entry must be submitted")

    if not gate.consignor:
        frappe.throw("Consignor is mandatory")

    if not gate.transport_service_item:
        frappe.throw("Transport Service Item is missing")

    if not gate.incoming_logistics:
        frappe.throw("Incoming Logistics is missing")

    # Prevent duplicate PI (docstatus != 2)
    if frappe.db.exists(
        "Purchase Invoice",
        {
            "custom_gate_entry_": gate.name,
            "docstatus": ["!=", 2]
        }
    ):
        frappe.throw("Purchase Invoice already created for this Gate Entry")


    # Get rate from Incoming Logistics
    rate = frappe.db.get_value(
        "Incoming Logistics",
        gate.incoming_logistics,
        "rate"
    ) or 0

    # Create Purchase Invoice
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = gate.consignor
    pi.company = gate.owner_site
    pi.bill_date = today()

    # Link back (recommended)
    pi.custom_gate_entry_ = gate.name

    # Add item
    pi.append("items", {
        "item_code": gate.transport_service_item,
        "qty": 1,
        "rate": rate
    })

    pi.save()
    return pi.name