import frappe

def validate_supplier(doc, method):
    # If the Agent checkbox is ticked, then the Agent field should also be mandatory.
    if doc.custom_is_agent and not doc.custom_agent_supplier:
        frappe.throw("Please select Agent")

    # If the Transporter checkbox is ticked, then the Transporter field should also be mandatory.
    if doc.is_transporter and not doc.custom_transporter_supplier:
        frappe.throw("Please select Transporter")
