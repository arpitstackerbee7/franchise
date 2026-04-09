import frappe
from frappe.model.document import Document

def validate_supplier(doc, method):
    # If the Agent checkbox is ticked, then the Agent field should also be mandatory.
    if doc.custom_is_agent and not doc.custom_agent_supplier:
        frappe.throw("Please select Agent")

    # If the Transporter checkbox is ticked, then the Transporter field should also be mandatory.
    if doc.is_transporter and not doc.custom_transporter:
        frappe.throw("Please select Transporter")


def create_supplier_warehouse(doc, method):
    
    if not doc.custom_is_jobber_warehouse:
        return

    if doc.custom_supplier_warehouse:
        return

    warehouse_name = doc.supplier_name
    company = doc.custom_company

    warehouse = frappe.db.exists("Warehouse", {
        "warehouse_name": warehouse_name,
        "company": company
    })

    if not warehouse:
        warehouse_doc = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": warehouse_name,
            "company": company,
            "parent_warehouse": f"All Warehouses - {frappe.get_cached_value('Company', company, 'abbr')}"
        })
        warehouse_doc.insert(ignore_permissions=True)
        warehouse = warehouse_doc.name

    # ✅ THIS LINE FIXES YOUR ISSUE
    doc.db_set("custom_supplier_warehouse", warehouse)






@frappe.whitelist()
def get_supplier_roles_for_not_show_counters():
    doc = frappe.get_doc('TZU Setting', 'TZU Setting')
    return [row.role for row in doc.all_counters_name_show_on_supplier]