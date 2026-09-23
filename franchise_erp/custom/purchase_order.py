import frappe
from frappe.model.naming import make_autoname
from frappe.utils import flt


#sub-contracting me logic laga hai

def normalize_serials(value):
    """Convert newline-separated serials into a clean list."""
    if not value:
        return []

    return [
        serial.strip()
        for serial in value.split("\n")
        if serial.strip()
    ]


def is_serial_allocated_in_other_po(serial, current_po=None):
    """
    Check whether serial is already allocated in another Purchase Order.

    Current PO is excluded so that an existing PO's own serials
    are not treated as duplicates.
    """

    rows = frappe.db.sql(
        """
        SELECT
            poi.parent,
            poi.custom_generated_serials
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po
            ON po.name = poi.parent
        WHERE
            poi.custom_generated_serials IS NOT NULL
            AND poi.custom_generated_serials != ''
            AND po.docstatus IN (0, 1)
            AND poi.custom_generated_serials LIKE %s
            AND poi.parent != %s
        """,
        (
            f"%{serial}%",
            current_po or ""
        ),
        as_dict=True
    )

    for row in rows:
        serials = normalize_serials(row.custom_generated_serials)

        if serial in serials:
            return True

    return False


def is_serial_exists_in_serial_no(serial):
    """Check actual Serial No DocType."""
    return bool(
        frappe.db.exists(
            "Serial No",
            serial
        )
    )


def get_next_available_serial(
    series_prefix,
    allocated_serials=None,
    current_po=None
):
    """
    Generate a serial which is not already allocated anywhere.

    Checks:
    1. Serials generated during current execution
    2. Other Purchase Orders
    3. Actual Serial No DocType
    """

    if allocated_serials is None:
        allocated_serials = set()

    max_attempts = 10000

    for _ in range(max_attempts):

        serial = make_autoname(series_prefix)

        # -----------------------------------------------------
        # Already generated in current execution
        # -----------------------------------------------------

        if serial in allocated_serials:
            continue

        # -----------------------------------------------------
        # Already allocated in another Purchase Order
        # -----------------------------------------------------

        if is_serial_allocated_in_other_po(
            serial,
            current_po=current_po
        ):
            continue

        # -----------------------------------------------------
        # Already exists as actual Serial No
        # -----------------------------------------------------

        if is_serial_exists_in_serial_no(serial):
            continue

        return serial

    frappe.throw(
        f"""
        Unable to generate a unique serial number for series
        <b>{series_prefix}</b>.

        Please check the Serial No series and existing Purchase
        Order allocations.
        """
    )


def validate_existing_serials(
    serials,
    current_po,
    current_row_serials=None
):
    """
    Validate serials already present on the current PO item.

    Serial can belong to current PO itself.

    Serial cannot already belong to another PO.
    """

    current_row_serials = set(current_row_serials or [])

    valid_serials = []

    for serial in serials:

        serial = serial.strip()

        if not serial:
            continue

        # -----------------------------------------------------
        # Duplicate inside same row
        # -----------------------------------------------------

        if serial in valid_serials:
            continue

        # -----------------------------------------------------
        # If this serial belongs to another PO → reject
        # -----------------------------------------------------

        if is_serial_allocated_in_other_po(
            serial,
            current_po=current_po
        ):
            continue

        valid_serials.append(serial)

    return valid_serials


def generate_serials_on_po_submit(doc, method):
    """
    Generate / maintain serial numbers on Purchase Order submit.

    IMPORTANT:
    Actual Serial No documents are NOT created here.
    Generated serials are stored only in:
        Purchase Order Item.custom_generated_serials

    Actual Serial No creation happens later during GRN/Purchase Receipt.
    """

    # =========================================================
    # ALL SERIALS ALREADY PRESENT IN CURRENT PO
    # =========================================================

    allocated_serials = set()

    for row in doc.items:

        existing = normalize_serials(
            row.custom_generated_serials
        )

        allocated_serials.update(existing)

    # =========================================================
    # PROCESS EACH ITEM ROW
    # =========================================================

    for item in doc.items:

        existing_serials = normalize_serials(
            item.custom_generated_serials
        )

        # -----------------------------------------------------
        # Remove duplicates inside the current row
        # -----------------------------------------------------

        unique_existing = []

        for serial in existing_serials:

            if serial not in unique_existing:
                unique_existing.append(serial)

        existing_serials = unique_existing

        # =====================================================
        # NORMAL PO
        # =====================================================

        if not doc.is_subcontracted:

            item_info = frappe.db.get_value(
                "Item",
                item.item_code,
                [
                    "has_serial_no",
                    "serial_no_series"
                ],
                as_dict=True
            )

            if not item_info or not item_info.has_serial_no:
                continue

            series_prefix = (
                item_info.serial_no_series
                if item_info.serial_no_series
                else f"{item.item_code}-.#####"
            )

            qty_required = int(item.qty)

            # -------------------------------------------------
            # Validate existing copied / existing serials
            # -------------------------------------------------

            valid_existing = []

            for serial in existing_serials:

                if serial in valid_existing:
                    continue

                # Serial already allocated to another PO
                if is_serial_allocated_in_other_po(
                    serial,
                    current_po=doc.name
                ):
                    continue

                valid_existing.append(serial)

            serials_to_save = valid_existing[:qty_required]

            # -------------------------------------------------
            # Generate missing serials
            # -------------------------------------------------

            diff = qty_required - len(serials_to_save)

            for _ in range(max(0, diff)):

                serial = get_next_available_serial(
                    series_prefix,
                    allocated_serials=allocated_serials,
                    current_po=doc.name
                )

                serials_to_save.append(serial)

                allocated_serials.add(serial)

            # -------------------------------------------------
            # Rebuild allocation set
            # -------------------------------------------------

            allocated_serials.update(serials_to_save)

        # =====================================================
        # SUBCONTRACTED PO
        # =====================================================

        else:

            if not item.fg_item or not item.fg_item_qty:
                continue

            fg_item_info = frappe.db.get_value(
                "Item",
                item.fg_item,
                [
                    "has_serial_no",
                    "serial_no_series"
                ],
                as_dict=True
            )

            if not fg_item_info or not fg_item_info.has_serial_no:
                continue

            fg_series_prefix = (
                fg_item_info.serial_no_series
                if fg_item_info.serial_no_series
                else f"{item.fg_item}-.#####"
            )

            qty_required = int(item.fg_item_qty)

            # -------------------------------------------------
            # Validate copied/existing serials
            # -------------------------------------------------

            valid_existing = []

            for serial in existing_serials:

                if serial in valid_existing:
                    continue

                # -------------------------------------------------
                # IMPORTANT:
                #
                # If duplicate PO copied this serial from another PO,
                # it will be removed here.
                # -------------------------------------------------

                if is_serial_allocated_in_other_po(
                    serial,
                    current_po=doc.name
                ):
                    continue

                valid_existing.append(serial)

            # -------------------------------------------------
            # Keep only required quantity
            # -------------------------------------------------

            serials_to_save = valid_existing[:qty_required]

            # -------------------------------------------------
            # Generate missing serials
            # -------------------------------------------------

            diff = qty_required - len(serials_to_save)

            for _ in range(max(0, diff)):

                serial = get_next_available_serial(
                    fg_series_prefix,
                    allocated_serials=allocated_serials,
                    current_po=doc.name
                )

                serials_to_save.append(serial)

                allocated_serials.add(serial)

            # -------------------------------------------------
            # Rebuild allocation set
            # -------------------------------------------------

            allocated_serials.update(serials_to_save)

        # =====================================================
        # SAVE
        # =====================================================

        frappe.db.set_value(
            "Purchase Order Item",
            item.name,
            "custom_generated_serials",
            "\n".join(serials_to_save)
        )
        
        
def apply_purchase_term(doc, method):

    if not doc.custom_purchase_term:
        return

    term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

    # -------------------------------------------------
    # 🔥 If manual discount is already applied,
    # don't overwrite ERPNext's default discount.
    # -------------------------------------------------
    # if (
    #     doc.apply_discount_on
    #     and (
    #         float(doc.discount_amount or 0) > 0
    #         or float(doc.additional_discount_percentage or 0) > 0
    #     )
    # ):
    #     return
    # Agar Purchase Term change nahi hua aur user ne manual discount lagaya hai
    # tabhi skip karo
    if (
        not doc.has_value_changed("custom_purchase_term")
        and doc.apply_discount_on
        and (
            float(doc.discount_amount or 0) > 0
            or float(doc.additional_discount_percentage or 0) > 0
        )
    ):
        return

    # -------------------------------
    # 🔥 STEP 0: RESET ITEM DISTRIBUTED DISCOUNT
    # -------------------------------
    for item in doc.items:
        item.distributed_discount_amount = 0

    # -------------------------------
    # 🔥 RESET DOC LEVEL
    # -------------------------------
    doc.additional_discount_percentage = 0
    doc.discount_amount = 0
    doc.apply_discount_on = None

    doc.ignore_pricing_rule = 1

    total_flat_discount = 0.0
    header_discount_percent = 0.0

    # -------------------------------
    # 1️⃣ ITEM LEVEL (RATE DIFF)
    # -------------------------------
    for item in doc.items:

        base_rate = item.price_list_rate or item.rate
        adjusted_rate = base_rate

        for row in term.purchase_term_charges:
            if row.charge_type == "Rate Diff":
                adjusted_rate -= row.value

        item.rate = adjusted_rate

    # -------------------------------
    # 2️⃣ DOCUMENT LEVEL (DISCOUNT)
    # -------------------------------
    for row in term.purchase_term_charges:

        if row.charge_type == "Discount":

            if row.value_type == "Percentage":
                header_discount_percent += row.value

            elif row.value_type == "Amount":
                total_flat_discount += row.value

    # -------------------------------
    # 3️⃣ APPLY DISCOUNT
    # -------------------------------
    if header_discount_percent:
        doc.apply_discount_on = "Net Total"
        doc.additional_discount_percentage = header_discount_percent

    elif total_flat_discount:
        doc.apply_discount_on = "Net Total"
        doc.discount_amount = total_flat_discount

    # -----------------------------------
    # 🔥 FINAL RECALCULATION
    # -----------------------------------
    doc.run_method("calculate_taxes_and_totals")

@frappe.whitelist()
def get_gate_entry_with_po_child(doctype, txt, filters, page_length=20, start=0):
    """
    Returns Gate Entries for MultiSelectDialog
    """
    return frappe.db.sql("""
        SELECT
            ge.name AS name,
            IFNULL(ge.purchase_ids, '') AS purchase_ids,
            IFNULL(ge.purchase_order, '') AS purchase_order,
            IFNULL(ge.owner_site, '') AS owner_site
        FROM `tabGate Entry` ge
        WHERE ge.docstatus = 1
        AND ge.consignor = %(consignor)s
    """, filters, as_dict=True)


@frappe.whitelist()
def get_items_from_gate_entry(gate_entry_name):
    """
    Returns all items linked to a Gate Entry
    """
    items = frappe.db.get_all(
        'Gate Entry Item',
        filters={'parent': gate_entry_name},
        fields=['item_code', 'qty', 'purchase_order', 'purchase_order_item']
    )

    # Ensure all values are strings or numbers
    for item in items:
        item['item_code'] = item.get('item_code') or ''
        item['qty'] = item.get('qty') or 0
        item['purchase_order'] = item.get('purchase_order') or ''
        item['purchase_order_item'] = item.get('purchase_order_item') or ''

    return items


#service cost updated
@frappe.whitelist()
def update_po_cost_and_sco(docname, items):
    items = frappe.parse_json(items)

    doc = frappe.get_doc("Purchase Order", docname)

    # ✅ IMPORTANT FLAGS
    doc.flags.ignore_validate = True
    doc.flags.ignore_validate_update_after_submit = True
    doc.flags.ignore_pricing_rule = True
    doc.flags.ignore_validate_rate = True
    doc.flags.ignore_price_list = True

    item_map = {d.get("docname"): d for d in items}

    # -------------------------
    # UPDATE ITEMS
    # -------------------------
    for row in doc.items:
        if row.name in item_map:
            rate_val = item_map[row.name].get("rate")

            if rate_val is not None:
                rate_val = flt(rate_val)

                row.rate = rate_val
                row.price_list_rate = rate_val

                row.amount = flt(row.qty) * rate_val
                row.base_amount = row.amount
                row.net_amount = row.amount
                row.base_net_amount = row.amount

    # -------------------------
    # CALCULATE
    # -------------------------
    doc.run_method("calculate_taxes_and_totals")

    # -------------------------
    # 🔥 FORCE APPLY AGAIN (MAIN FIX)
    # -------------------------
    for row in doc.items:
        if row.name in item_map:
            rate_val = item_map[row.name].get("rate")

            if rate_val is not None:
                rate_val = flt(rate_val)

                row.rate = rate_val
                row.price_list_rate = rate_val

                row.amount = flt(row.qty) * rate_val
                row.base_amount = row.amount
                row.net_amount = row.amount
                row.base_net_amount = row.amount

    doc.set_payment_schedule()

    doc.save(ignore_permissions=True)

    # -------------------------
    # UPDATE SCO
    # -------------------------
    sco_list = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": docname},
        fields=["name"]
    )

    for sco in sco_list:
        sco_doc = frappe.get_doc("Subcontracting Order", sco.name)

        sco_doc.flags.ignore_validate = True
        sco_doc.flags.ignore_validate_update_after_submit = True

        for row in sco_doc.items:
            if row.purchase_order_item in item_map:
                rate_val = item_map[row.purchase_order_item].get("rate")

                if rate_val is not None:
                    row.service_cost_per_qty = flt(rate_val)

        sco_doc.save(ignore_permissions=True)

    return "✅ Cost Updated Successfully"