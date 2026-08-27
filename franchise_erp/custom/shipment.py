import frappe

def fix_address_issue(doc, method):

    # ❌ ALWAYS clear wrong field
    doc.delivery_address = None

    # ✅ ensure correct address link
    if not doc.delivery_address_name:
        frappe.throw("Please select Delivery Address (Address Link)")
        
        
@frappe.whitelist()
def get_delivery_address_contact(party_type, party_name):

    if not party_type or not party_name:
        return {
            "address": None,
            "contact": None
        }

    # ---------------------------------------------------------
    # VALIDATE PARTY TYPE
    # ---------------------------------------------------------

    if party_type not in ["Customer", "Supplier"]:
        frappe.throw(
            "Only Customer or Supplier is allowed."
        )

    # ---------------------------------------------------------
    # GET ADDRESS
    # ---------------------------------------------------------

    address = frappe.db.sql(
        """
        SELECT
            dl.parent
        FROM `tabDynamic Link` dl
        INNER JOIN `tabAddress` a
            ON a.name = dl.parent
        WHERE
            dl.parenttype = 'Address'
            AND dl.link_doctype = %s
            AND dl.link_name = %s
        ORDER BY
            a.is_primary_address DESC,
            a.is_shipping_address DESC,
            a.modified DESC
        LIMIT 1
        """,
        (party_type, party_name),
        as_dict=True
    )

    # ---------------------------------------------------------
    # GET CONTACT
    # ---------------------------------------------------------

    contact = frappe.db.sql(
        """
        SELECT
            dl.parent
        FROM `tabDynamic Link` dl
        INNER JOIN `tabContact` c
            ON c.name = dl.parent
        WHERE
            dl.parenttype = 'Contact'
            AND dl.link_doctype = %s
            AND dl.link_name = %s
        ORDER BY
            c.is_primary_contact DESC,
            c.modified DESC
        LIMIT 1
        """,
        (party_type, party_name),
        as_dict=True
    )

    return {
        "address": (
            address[0].parent
            if address
            else None
        ),

        "contact": (
            contact[0].parent
            if contact
            else None
        )
    }