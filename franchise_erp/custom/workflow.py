import frappe

def skip_hr_approval(doc, method=None):
    frappe.log_error(
        f"HOOK CALLED | {doc.name} | {doc.custom_employee_category} | {doc.workflow_state}",
        "Leave Workflow Debug")
    if (
        doc.custom_employee_category == "Company Employee"
        and doc.workflow_state == "Pending HR Approval"
    ):
        frappe.db.set_value(
            "Leave Application",
            doc.name,
            "workflow_state",
            "Approved",
            update_modified=False
        )