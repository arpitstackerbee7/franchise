import frappe
from frappe import _

def set_franchise_owner(doc, method):
    """
    Set franchise user as owner and add required permissions
    """
    if not doc.is_internal_supplier:
        return

    # Find Franchise User
    franchise_user = frappe.db.get_value(
        "User",
        {"franchise_company": doc.company, "enabled": 1},
        "name"
    )

    if not franchise_user:
        frappe.log_error(f"No franchise user found for company {doc.company}")
        return

    # Set Owner
    doc.db_set("owner", franchise_user)
    doc.db_set("modified_by", franchise_user)

    # Give User Company Permission
    add_permission_if_missing("Company", doc.company, franchise_user)

    # Give Supplier Permission
    if doc.supplier:
        add_permission_if_missing("Supplier", doc.supplier, franchise_user)

def add_permission_if_missing(doctype, value, user):
    """
    Adds User Permission if it doesn't already exist
    """
    exists = frappe.db.exists(
        "User Permission",
        {"user": user, "allow": doctype, "for_value": value}
    )
    if not exists:
        frappe.permissions.add_user_permission(
            doctype, value, user, ignore_permissions=True
        )

def remove_represents_company_in_return(doc, method):
    """
    Clear represents_company for return/debit invoices
    """
    if doc.is_return:
        # Use db_set to persist before submit
        doc.db_set("represents_company", None)





# @frappe.whitelist()
# def get_user_role_profiles(user):
#     role_profile = frappe.db.get_value("User", user, "role_profile_name")
#     return [role_profile] if role_profile else []
