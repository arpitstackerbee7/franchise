import frappe
from helpdesk.api.doc import get_filterable_fields as core_get_filterable_fields


@frappe.whitelist()
def get_filterable_fields(
    doctype: str,
    show_customer_portal_fields: bool = False,
    ignore_team_restrictions: bool = False,
):
    # Admin / System Manager ke liye restriction ignore karo,
    # baaki agents ke liye core ka behaviour same rahega
    if doctype == "HD Ticket" and "System Manager" in frappe.get_roles():
        ignore_team_restrictions = True

    return core_get_filterable_fields(
        doctype,
        show_customer_portal_fields=show_customer_portal_fields,
        ignore_team_restrictions=ignore_team_restrictions,
    )