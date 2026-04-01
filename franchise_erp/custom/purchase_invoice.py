import frappe
from frappe.utils import flt
from frappe.utils import add_days
from frappe.utils import today



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


# @frappe.whitelist()
# def create_pi_from_gate_entry(gate_entry):
#     gate = frappe.get_doc("Gate Entry", gate_entry)

#     if gate.docstatus != 1:
#         frappe.throw("Gate Entry must be submitted")

#     if not gate.consignor:
#         frappe.throw("Consignor is mandatory")

#     if not gate.transport_service_item:
#         frappe.throw("Transport Service Item is missing")

#     if not gate.incoming_logistics:
#         frappe.throw("Incoming Logistics is missing")

#     # Prevent duplicate PI (docstatus != 2)
#     if frappe.db.exists(
#         "Purchase Invoice",
#         {
#             "custom_gate_entry_": gate.name,
#             "docstatus": ["!=", 2]
#         }
#     ):
#         frappe.throw("Purchase Invoice already created for this Gate Entry")


#     # Get rate from Incoming Logistics
#     rate = frappe.db.get_value(
#         "Incoming Logistics",
#         gate.incoming_logistics,
#         "rate"
#     ) or 0

#     # Create Purchase Invoice
#     pi = frappe.new_doc("Purchase Invoice")
#     pi.supplier = gate.consignor
#     pi.company = gate.owner_site
#     pi.bill_date = today()

#     # Link back (recommended)
#     pi.custom_gate_entry_ = gate.name

#     # Add item
#     pi.append("items", {
#         "item_code": gate.transport_service_item,
#         "qty": 1,
#         "rate": rate
#     })

#     pi.save()
#     return pi.name


@frappe.whitelist()
def create_pi_from_gate_entry(gate_entry):
    from frappe.utils import today
    from erpnext.accounts.party import get_party_account

    gate = frappe.get_doc("Gate Entry", gate_entry)

    if gate.docstatus != 1:
        frappe.throw("Gate Entry must be submitted")

    if not gate.consignor:
        frappe.throw("Consignor is mandatory")

    if not gate.incoming_logistics:
        frappe.throw("Incoming Logistics is missing")

    # Transport Item fallback
    transport_item = gate.transport_service_item or frappe.db.get_single_value(
        "TZU Setting",
        "transport_service_item"
    )

    if not transport_item:
        frappe.throw("Transport Service Item is missing")

    # Prevent duplicate PI
    if frappe.db.exists(
        "Purchase Invoice",
        {
            "custom_gate_entry_": gate.name,
            "docstatus": ["!=", 2]
        }
    ):
        frappe.throw("Purchase Invoice already created for this Gate Entry")

    # Get rate
    rate = frappe.db.get_value(
        "Incoming Logistics",
        gate.incoming_logistics,
        "rate"
    ) or 0

    # Payable Account
    payable_account = get_party_account(
        "Supplier",
        gate.consignor,
        gate.owner_site
    )

    if not payable_account:
        frappe.throw("Payable Account not found for Supplier")

    # Create PI (DRAFT)
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = gate.consignor
    pi.company = gate.owner_site
    pi.bill_date = today()
    pi.bill_no = "0"
    pi.credit_to = payable_account

    # Link back
    pi.custom_gate_entry_ = gate.name

    # Add item
    pi.append("items", {
        "item_code": transport_item,
        "qty": 1,
        "rate": rate
    })

    # Optional (recommended)
    pi.set_missing_values()
    pi.calculate_taxes_and_totals()

    # ✅ Only insert (DRAFT)
    pi.flags.ignore_mandatory = True   # bypass GST mandatory
    pi.insert(ignore_permissions=True)

    return pi.name

import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_supplier_stats(supplier, company):
    if not supplier or not company:
        return {
            "annual_billing": 0,
            "total_unpaid": 0
        }

    # Load supplier exactly like ERPNext form load
    supplier_doc = frappe.get_doc("Supplier", supplier)

    # __onload is populated ONLY after this
    supplier_doc.run_method("onload")

    dashboard_info = (
        supplier_doc.get("__onload", {})
        .get("dashboard_info", [])
    )

    annual_billing = 0
    total_unpaid = 0

    for row in dashboard_info:
        if row.get("company") == company:
            annual_billing = row.get("billing_this_year", 0)
            total_unpaid = row.get("total_unpaid", 0)
            break

    return {
        "annual_billing": flt(annual_billing),
        "total_unpaid": flt(total_unpaid)
    }




@frappe.whitelist()
def get_purchase_invoice_city(purchase_invoice):
    pr = frappe.get_doc("Purchase Invoice", purchase_invoice)

    # 1️⃣ Shipping Address (priority)
    if pr.shipping_address:
        city = frappe.db.get_value(
            "Address",
            pr.shipping_address,
            "custom_citytown"
        )
        if city:
            return city

    # 2️⃣ Billing Address (fallback)
    if pr.billing_address:
        city = frappe.db.get_value(
            "Address",
            pr.billing_address,
            "custom_citytown"
        )
        if city:
            return city

    return None