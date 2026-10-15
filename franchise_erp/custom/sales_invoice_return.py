import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.sales_and_purchase_return import make_return_doc


def create_return_delivery_notes_for_sales_invoice(sales_invoice):
    """
    Create Delivery Note returns automatically when a Return Sales Invoice
    is submitted.

    One Return Delivery Note is created per original Delivery Note.
    """

    if not sales_invoice.is_return:
        return

    # Group Sales Invoice items by original Delivery Note.
    delivery_note_items = {}

    for si_item in sales_invoice.items:
        if not si_item.delivery_note:
            continue

        if not si_item.dn_detail:
            continue

        return_qty = abs(flt(si_item.qty))

        if not return_qty:
            continue

        delivery_note_items.setdefault(
            si_item.delivery_note, []
        ).append(si_item)

    if not delivery_note_items:
        return

    for delivery_note_name, si_items in delivery_note_items.items():
        create_return_delivery_note(
            sales_invoice=sales_invoice,
            delivery_note_name=delivery_note_name,
            si_items=si_items,
        )


def create_return_delivery_note(
    sales_invoice,
    delivery_note_name,
    si_items,
):
    """
    Create one Return Delivery Note for one original Delivery Note.

    The standard ERPNext make_return_doc() is used so that:
    - return_against is correct
    - dn_detail is correct
    - return warehouse handling remains standard
    - serial/batch handling remains standard
    - already returned quantities are respected
    """

    delivery_note = frappe.get_doc(
        "Delivery Note",
        delivery_note_name,
    )

    if delivery_note.docstatus != 1:
        frappe.throw(
            _(
                "Delivery Note {0} must be submitted before creating a return."
            ).format(delivery_note_name)
        )

    # ---------------------------------------------------------
    # Build requested return quantities from the Return SI
    # ---------------------------------------------------------

    requested_qty = {}

    for si_item in si_items:
        if not si_item.dn_detail:
            continue

        qty = abs(flt(si_item.qty))

        if not qty:
            continue

        requested_qty[si_item.dn_detail] = (
            requested_qty.get(si_item.dn_detail, 0) + qty
        )

    if not requested_qty:
        return

    # ---------------------------------------------------------
    # Let ERPNext create the native Delivery Note return
    # ---------------------------------------------------------

    return_dn = make_return_doc(
        "Delivery Note",
        delivery_note_name,
    )

    if not return_dn:
        return

    # ---------------------------------------------------------
    # Keep only the rows which are actually being returned
    # through this Return Sales Invoice.
    # ---------------------------------------------------------

    kept_items = []

    for row in return_dn.items:
        if not row.dn_detail:
            continue

        qty_to_return = requested_qty.get(row.dn_detail)

        if not qty_to_return:
            continue

        # Native make_return_doc() creates negative qty.
        row.qty = -abs(flt(qty_to_return))

        if row.conversion_factor:
            row.stock_qty = row.qty * flt(row.conversion_factor)

        kept_items.append(row)

    # Replace mapped items with only the requested rows.
    return_dn.set("items", kept_items)

    if not return_dn.items:
        return

    # ---------------------------------------------------------
    # FIX:
    #
    # Keep parent Set Warehouse in sync with the warehouse
    # used by the returned item.
    #
    # Otherwise ERPNext can show the warehouse in the UI after
    # submission even though the saved parent value is None.
    # This makes the submitted document appear "Not Saved".
    # ---------------------------------------------------------

    return_warehouse = next(
        (
            item.warehouse
            for item in return_dn.items
            if item.warehouse
        ),
        None,
    )

    if return_warehouse:
        return_dn.set_warehouse = return_warehouse

    # ---------------------------------------------------------
    # Important:
    #
    # Do NOT copy serial_and_batch_bundle from the original DN.
    #
    # ERPNext's native return validation will handle the
    # return-side serial/batch stock transaction.
    # ---------------------------------------------------------

    return_dn.flags.ignore_permissions = True

    return_dn.insert(ignore_permissions=True)
    return_dn.submit()

    frappe.msgprint(
        _(
            "Return Delivery Note {0} created for Delivery Note {1}."
        ).format(
            return_dn.name,
            delivery_note_name,
        )
    )

    return return_dn