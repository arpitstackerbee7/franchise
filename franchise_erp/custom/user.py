import frappe

def validate_company(doc, method):

    # setup wizard ke time validation skip
    if frappe.flags.in_install or frappe.flags.in_setup_wizard:
        return

    if not doc.company:
        frappe.throw("Company is mandatory")