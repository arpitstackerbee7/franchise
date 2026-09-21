
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.controllers.sales_and_purchase_return import make_return_doc


class BulkSalesReturn(Document):

    def validate(self):
        self.validate_customer()
        self.validate_qty()

    # -------------------------------------------------------------------------
    # CUSTOMER VALIDATION
    # -------------------------------------------------------------------------

    def validate_customer(self):

        customers = set()

        for row in self.items:

            customer = None

            if row.delivery_note:

                customer = frappe.db.get_value(
                    "Delivery Note",
                    row.delivery_note,
                    "customer"
                )

            elif row.sales_invoice:

                customer = frappe.db.get_value(
                    "Sales Invoice",
                    row.sales_invoice,
                    "customer"
                )

            if customer:
                customers.add(customer)

        if len(customers) > 1:

            frappe.throw(
                "All items in Bulk Sales Return must belong to the same Customer."
            )

    # -------------------------------------------------------------------------
    # QTY VALIDATION
    # -------------------------------------------------------------------------

    def validate_qty(self):

        for row in self.items:

            qty = flt(row.qty)

            if qty <= 0:

                frappe.throw(
                    f"Return qty must be greater than 0 in row {row.idx}"
                )

            # -------------------------------------------------------------
            # DELIVERY NOTE ROW
            # -------------------------------------------------------------

            if row.delivery_note_item:

                sent_qty = frappe.db.get_value(
                    "Delivery Note Item",
                    row.delivery_note_item,
                    "qty"
                ) or 0

                returned_qty = frappe.db.sql(
                    """
                    SELECT
                        IFNULL(SUM(ABS(dni.qty)), 0)
                    FROM `tabDelivery Note Item` dni
                    INNER JOIN `tabDelivery Note` dn
                        ON dn.name = dni.parent
                    WHERE dn.docstatus = 1
                    AND dn.is_return = 1
                    AND dni.dn_detail = %s
                    """,
                    row.delivery_note_item
                )[0][0] or 0

                available_qty = (
                    flt(sent_qty)
                    - flt(returned_qty)
                )

                if qty > available_qty:

                    frappe.throw(
                        f"Return qty cannot exceed returnable qty "
                        f"({available_qty}) in row {row.idx}"
                    )

            # -------------------------------------------------------------
            # SALES INVOICE ROW
            # -------------------------------------------------------------

            elif row.sales_invoice_item:

                si_data = frappe.db.get_value(
                    "Sales Invoice Item",
                    row.sales_invoice_item,
                    [
                        "qty",
                        "delivered_qty",
                        "parent"
                    ],
                    as_dict=True
                )

                if si_data:

                    sales_invoice = si_data.parent

                    update_stock = frappe.db.get_value(
                        "Sales Invoice",
                        sales_invoice,
                        "update_stock"
                    )

                    if update_stock:

                        available_qty = flt(
                            si_data.qty
                        )

                    else:

                        available_qty = flt(
                            si_data.delivered_qty
                        )

                    # -----------------------------------------------------
                    # Count ALL submitted Sales Invoice Returns.
                    # -----------------------------------------------------

                    already_returned = frappe.db.sql(
                        """
                        SELECT
                            IFNULL(SUM(ABS(sii.qty)), 0)
                        FROM `tabSales Invoice Item` sii
                        INNER JOIN `tabSales Invoice` si
                            ON si.name = sii.parent
                        WHERE si.docstatus = 1
                        AND si.is_return = 1
                        AND sii.sales_invoice_item = %s
                        """,
                        row.sales_invoice_item
                    )[0][0] or 0

                    available_qty -= flt(
                        already_returned
                    )

                    if qty > available_qty:

                        frappe.throw(
                            f"Return qty cannot exceed returnable qty "
                            f"({available_qty}) in row {row.idx}"
                        )

            # -------------------------------------------------------------
            # SERIAL VALIDATION
            # -------------------------------------------------------------

            has_serial_no = frappe.db.get_value(
                "Item",
                row.item_code,
                "has_serial_no"
            )

            if has_serial_no and (
                row.delivery_note_item
                or row.sales_invoice_item
            ):

                serials = []

                if row.serial_nos:

                    serials = [
                        s.strip()
                        for s in row.serial_nos.split("\n")
                        if s.strip()
                    ]

                if not serials:

                    frappe.throw(
                        f"Row {row.idx}: Serial Numbers are required "
                        f"for serialized item {row.item_code}"
                    )

                if len(serials) != int(qty):

                    frappe.throw(
                        f"Row {row.idx}: Qty must match number of "
                        f"Serial Numbers for item {row.item_code}"
                    )

    # =========================================================================
    # ON SUBMIT
    # =========================================================================

    def on_submit(self):

        self.db_set(
            "status",
            "Queued"
        )

        frappe.db.commit()

        frappe.enqueue(
            method=(
                "franchise_erp.franchise_erp.doctype.bulk_sales_return."
                "bulk_sales_return.process_bulk_sales_return"
            ),
            docname=self.name,
            queue="long",
            timeout=1200,
            job_name=f"Bulk Sales Return {self.name}"
        )

        frappe.msgprint(
            "Return documents are being created and submitted in the background."
        )


# =============================================================================
# MAIN BULK PROCESS
# =============================================================================

def process_bulk_sales_return(docname):

    doc = frappe.get_doc(
        "Bulk Sales Return",
        docname
    )

    try:

        doc.db_set(
            "status",
            "In Progress"
        )

        frappe.db.commit()

        if not doc.items:

            frappe.throw(
                "No return items found."
            )

        # ================================================================
        # RESOLVE ALL BULK ROWS
        # ================================================================

        resolved_rows = []

        for row in doc.items:

            resolved = resolve_bulk_return_row(
                row
            )

            if not resolved:

                frappe.throw(
                    f"Unable to resolve return source for row {row.idx}"
                )

            resolved_rows.append(
                resolved
            )

        # ================================================================
        # ONE SALES INVOICE RETURN
        # ================================================================

        si_rows = [
            row
            for row in resolved_rows
            if row.get("sales_invoice_item")
        ]

        if si_rows:

            create_single_sales_invoice_return(
                doc,
                si_rows
            )

        # ================================================================
        # ONE DELIVERY NOTE RETURN PER SOURCE DN
        # ================================================================

        dn_rows = [
            row
            for row in resolved_rows
            if row.get("delivery_note")
            and row.get("delivery_note_item")
        ]

        if dn_rows:

            create_delivery_note_returns(
                doc,
                dn_rows
            )

        # ================================================================
        # ACTIVATE SALES-INVOICE-ONLY STOCK
        # ================================================================

        activate_sales_invoice_only_stock(
            doc,
            resolved_rows
        )

        # ================================================================
        # FINAL DELIVERY NOTE REFERENCE REPAIR
        #
        # This is intentionally AFTER all return processing.
        #
        # Any Delivery Note Return created for this Bulk Sales Return
        # MUST finally contain:
        #
        # custom_bulk_sales_return = Bulk Sales Return.name
        #
        # This protects against any internal ERPNext save/submit logic
        # clearing the custom field.
        # ================================================================

        reconcile_delivery_note_bulk_reference(
            doc
        )

        # ================================================================
        # COMPLETE
        # ================================================================

        doc.db_set(
            "status",
            "Completed"
        )

        frappe.db.commit()

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            f"Bulk Sales Return Failed - {docname}"
        )

        try:

            doc.db_set(
                "status",
                "Failed"
            )

            if frappe.db.has_column(
                "Bulk Sales Return",
                "error_message"
            ):

                doc.db_set(
                    "error_message",
                    frappe.get_traceback()[-4000:]
                )

            frappe.db.commit()

        except Exception:

            frappe.log_error(
                frappe.get_traceback(),
                "Bulk Sales Return Status Update Failed"
            )

        raise


# =============================================================================
# RESOLVE BULK RETURN ROW
# =============================================================================

def resolve_bulk_return_row(row):

    result = {
        "item_code": row.item_code,
        "item_name": None,
        "qty": flt(row.qty),
        "serials": [],
        "rate": None,
        "warehouse": None,

        "sales_invoice": row.sales_invoice,
        "sales_invoice_item": row.sales_invoice_item,

        "delivery_note": row.delivery_note,
        "delivery_note_item": row.delivery_note_item,

        "source_type": None,
    }

    # -------------------------------------------------------------------------
    # SERIALS
    # -------------------------------------------------------------------------

    if row.serial_nos:

        result["serials"] = [
            s.strip()
            for s in row.serial_nos.split("\n")
            if s.strip()
        ]

    # =========================================================================
    # CASE 1: SALES INVOICE SOURCE
    # =========================================================================

    if row.sales_invoice_item:

        si_item = frappe.db.get_value(
            "Sales Invoice Item",
            row.sales_invoice_item,
            [
                "parent",
                "item_code",
                "item_name",
                "qty",
                "rate",
                "warehouse",
                "dn_detail",
                "delivery_note",
                "sales_order",
                "so_detail"
            ],
            as_dict=True
        )

        if not si_item:

            frappe.throw(
                f"Sales Invoice Item {row.sales_invoice_item} not found."
            )

        result["source_type"] = "Sales Invoice"

        result["sales_invoice"] = si_item.parent
        result["sales_invoice_item"] = row.sales_invoice_item

        result["item_code"] = si_item.item_code
        result["item_name"] = si_item.item_name
        result["rate"] = si_item.rate
        result["warehouse"] = si_item.warehouse

        # ---------------------------------------------------------------------
        # Resolve DN using dn_detail.
        # ---------------------------------------------------------------------

        if si_item.dn_detail:

            dn_data = frappe.db.get_value(
                "Delivery Note Item",
                si_item.dn_detail,
                [
                    "parent",
                    "name",
                    "item_code",
                    "warehouse"
                ],
                as_dict=True
            )

            if dn_data:

                result["delivery_note"] = dn_data.parent
                result["delivery_note_item"] = dn_data.name

        # ---------------------------------------------------------------------
        # Fallback using delivery_note.
        # ---------------------------------------------------------------------

        elif si_item.delivery_note:

            result["delivery_note"] = (
                si_item.delivery_note
            )

            dn_item = frappe.db.get_value(
                "Delivery Note Item",
                {
                    "parent": si_item.delivery_note,
                    "item_code": si_item.item_code
                },
                "name"
            )

            if dn_item:

                result["delivery_note_item"] = dn_item

        return result

    # =========================================================================
    # CASE 2: DELIVERY NOTE SOURCE
    # =========================================================================

    if row.delivery_note_item:

        dn_item = frappe.db.get_value(
            "Delivery Note Item",
            row.delivery_note_item,
            [
                "parent",
                "name",
                "item_code",
                "item_name",
                "qty",
                "rate",
                "warehouse",
                "so_detail",
                "against_sales_order"
            ],
            as_dict=True
        )

        if not dn_item:

            frappe.throw(
                f"Delivery Note Item {row.delivery_note_item} not found."
            )

        result["source_type"] = "Delivery Note"

        result["delivery_note"] = dn_item.parent
        result["delivery_note_item"] = dn_item.name

        result["item_code"] = dn_item.item_code
        result["item_name"] = dn_item.item_name
        result["rate"] = dn_item.rate
        result["warehouse"] = dn_item.warehouse

        # ---------------------------------------------------------------------
        # Find related Sales Invoice Item through exact dn_detail.
        # ---------------------------------------------------------------------

        si_items = frappe.db.sql(
            """
            SELECT
                sii.name,
                sii.parent,
                sii.item_code,
                sii.rate,
                sii.warehouse,
                si.posting_date,
                si.posting_time,
                si.creation
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE sii.dn_detail = %s
            AND si.docstatus = 1
            AND si.is_return = 0
            ORDER BY
                si.posting_date DESC,
                si.posting_time DESC,
                si.creation DESC
            """,
            dn_item.name,
            as_dict=True
        )

        if si_items:

            si_item = si_items[0]

            result["sales_invoice"] = si_item.parent
            result["sales_invoice_item"] = si_item.name

        else:

            # -----------------------------------------------------------------
            # Fallback through delivery_note + item_code.
            # -----------------------------------------------------------------

            si_item = frappe.db.sql(
                """
                SELECT
                    sii.name,
                    sii.parent,
                    sii.item_code,
                    sii.rate,
                    sii.warehouse
                FROM `tabSales Invoice Item` sii
                INNER JOIN `tabSales Invoice` si
                    ON si.name = sii.parent
                WHERE si.docstatus = 1
                AND si.is_return = 0
                AND sii.delivery_note = %s
                AND sii.item_code = %s
                ORDER BY
                    si.posting_date DESC,
                    si.posting_time DESC,
                    si.creation DESC
                LIMIT 1
                """,
                (
                    dn_item.parent,
                    dn_item.item_code
                ),
                as_dict=True
            )

            if si_item:

                si_item = si_item[0]

                result["sales_invoice"] = (
                    si_item.parent
                )

                result["sales_invoice_item"] = (
                    si_item.name
                )

        return result

    return None


# =============================================================================
# CREATE ONE CONSOLIDATED SALES INVOICE RETURN
# =============================================================================

def create_single_sales_invoice_return(
    doc,
    rows
):

    if not rows:
        return None

    # -------------------------------------------------------------------------
    # Combine duplicate SI Item rows.
    # -------------------------------------------------------------------------

    selected = {}

    for row in rows:

        sales_invoice_item = row.get(
            "sales_invoice_item"
        )

        if not sales_invoice_item:
            continue

        if sales_invoice_item not in selected:

            selected[sales_invoice_item] = {
                "sales_invoice": row.get(
                    "sales_invoice"
                ),
                "qty": 0,
                "serials": [],
                "item_code": row.get(
                    "item_code"
                ),
                "rate": row.get(
                    "rate"
                ),
                "warehouse": row.get(
                    "warehouse"
                ),
                "item_name": row.get(
                    "item_name"
                ),
                "delivery_note": row.get(
                    "delivery_note"
                ),
                "delivery_note_item": row.get(
                    "delivery_note_item"
                ),
            }

        selected[
            sales_invoice_item
        ]["qty"] += flt(
            row.get("qty")
        )

        selected[
            sales_invoice_item
        ]["serials"].extend(
            row.get("serials") or []
        )

        if row.get("delivery_note"):

            selected[
                sales_invoice_item
            ]["delivery_note"] = (
                row.get("delivery_note")
            )

        if row.get("delivery_note_item"):

            selected[
                sales_invoice_item
            ]["delivery_note_item"] = (
                row.get("delivery_note_item")
            )

    if not selected:
        return None

    # -------------------------------------------------------------------------
    # Get source SIs.
    # -------------------------------------------------------------------------

    source_si_names = list(
        dict.fromkeys(
            data.get("sales_invoice")
            for data in selected.values()
            if data.get("sales_invoice")
        )
    )

    if not source_si_names:

        frappe.throw(
            f"No Sales Invoice found for Bulk Sales Return {doc.name}."
        )

    # -------------------------------------------------------------------------
    # Validate same customer/company/currency.
    # -------------------------------------------------------------------------

    customers = set()
    companies = set()
    currencies = set()

    source_sis = {}

    for si_name in source_si_names:

        source_si = frappe.get_doc(
            "Sales Invoice",
            si_name
        )

        if source_si.docstatus != 1:

            frappe.throw(
                f"Sales Invoice {si_name} must be submitted."
            )

        source_sis[si_name] = source_si

        customers.add(
            source_si.customer
        )

        companies.add(
            source_si.company
        )

        currencies.add(
            source_si.currency
        )

    if len(customers) > 1:

        frappe.throw(
            "All Sales Invoice items in one Bulk Sales Return "
            "must belong to the same Customer."
        )

    if len(companies) > 1:

        frappe.throw(
            "All Sales Invoice items in one Bulk Sales Return "
            "must belong to the same Company."
        )

    if len(currencies) > 1:

        frappe.throw(
            "All Sales Invoice items in one Bulk Sales Return "
            "must use the same Currency."
        )

    first_source_si = source_si_names[0]

    source_si = source_sis[
        first_source_si
    ]

    # -------------------------------------------------------------------------
    # Create base return.
    # -------------------------------------------------------------------------

    return_doc = make_return_doc(
        "Sales Invoice",
        source_si.name
    )

    return_doc.is_return = 1

    return_doc.return_against = None

    return_doc.customer = source_si.customer
    return_doc.company = source_si.company
    return_doc.currency = source_si.currency
    return_doc.conversion_rate = source_si.conversion_rate

    # -------------------------------------------------------------------------
    # Check DN-backed items.
    # -------------------------------------------------------------------------

    has_dn_backed_item = any(
        data.get("delivery_note_item")
        for data in selected.values()
    )

    if has_dn_backed_item:

        return_doc.update_stock = 0

    else:

        source_update_stock = all(
            bool(
                source_sis[si_name].update_stock
            )
            for si_name in source_si_names
        )

        return_doc.update_stock = (
            1
            if source_update_stock
            else 0
        )

    # -------------------------------------------------------------------------
    # Remove auto-mapped items.
    # -------------------------------------------------------------------------

    return_doc.set(
        "items",
        []
    )

    # -------------------------------------------------------------------------
    # Add selected items.
    # -------------------------------------------------------------------------

    for sales_invoice_item, selected_row in selected.items():

        original_data = frappe.db.get_value(
            "Sales Invoice Item",
            sales_invoice_item,
            [
                "name",
                "parent",
                "item_code",
                "item_name",
                "qty",
                "rate",
                "warehouse",
                "uom",
                "stock_uom",
                "conversion_factor",
                "income_account",
                "cost_center",
                "description",
                "brand",
                "sales_order",
                "so_detail",
                "delivery_note",
                "dn_detail"
            ],
            as_dict=True
        )

        if not original_data:

            frappe.throw(
                f"Sales Invoice Item {sales_invoice_item} not found."
            )

        item = return_doc.append(
            "items",
            {}
        )

        item.item_code = (
            original_data.item_code
        )

        item.item_name = (
            original_data.item_name
        )

        item.description = (
            original_data.description
            or original_data.item_name
            or original_data.item_code
        )

        item.uom = (
            original_data.uom
        )

        item.stock_uom = (
            original_data.stock_uom
        )

        item.conversion_factor = (
            original_data.conversion_factor
            or 1
        )

        item.rate = (
            original_data.rate
        )

        item.warehouse = (
            original_data.warehouse
        )

        item.qty = -abs(
            flt(
                selected_row["qty"]
            )
        )

        if hasattr(
            item,
            "sales_invoice_item"
        ):

            item.sales_invoice_item = (
                sales_invoice_item
            )

        if hasattr(
            item,
            "sales_order"
        ):

            item.sales_order = (
                original_data.sales_order
            )

        if hasattr(
            item,
            "so_detail"
        ):

            item.so_detail = (
                original_data.so_detail
            )

        dn_name = (
            selected_row.get("delivery_note")
            or original_data.delivery_note
        )

        dn_item_name = (
            selected_row.get("delivery_note_item")
            or original_data.dn_detail
        )

        if hasattr(
            item,
            "delivery_note"
        ):

            item.delivery_note = dn_name

        if hasattr(
            item,
            "dn_detail"
        ):

            item.dn_detail = dn_item_name

        if hasattr(
            item,
            "income_account"
        ):

            item.income_account = (
                original_data.income_account
            )

        if hasattr(
            item,
            "cost_center"
        ):

            item.cost_center = (
                original_data.cost_center
            )

        if hasattr(
            item,
            "brand"
        ):

            item.brand = (
                original_data.brand
            )

        serials = list(
            dict.fromkeys(
                selected_row.get("serials") or []
            )
        )

        if serials:

            item.serial_no = "\n".join(
                serials
            )

            if hasattr(
                item,
                "use_serial_batch_fields"
            ):

                item.use_serial_batch_fields = (
                    1
                    if return_doc.update_stock
                    else 0
                )

    # -------------------------------------------------------------------------
    # Re-index.
    # -------------------------------------------------------------------------

    for idx, item in enumerate(
        return_doc.items,
        start=1
    ):

        item.idx = idx

    if not return_doc.items:

        frappe.throw(
            f"No valid Sales Invoice items found for Bulk Sales Return "
            f"{doc.name}."
        )

    # -------------------------------------------------------------------------
    # Remove payments.
    # -------------------------------------------------------------------------

    if hasattr(
        return_doc,
        "payments"
    ):

        return_doc.set(
            "payments",
            []
        )

    if hasattr(
        return_doc,
        "payment_schedule"
    ):

        return_doc.set(
            "payment_schedule",
            []
        )

    if hasattr(
        return_doc,
        "paid_amount"
    ):

        return_doc.paid_amount = 0

    if hasattr(
        return_doc,
        "base_paid_amount"
    ):

        return_doc.base_paid_amount = 0

    # -------------------------------------------------------------------------
    # Flags.
    # -------------------------------------------------------------------------

    return_doc.flags.bulk_consolidated_return = True
    return_doc.flags.ignore_permissions = True

    # -------------------------------------------------------------------------
    # Set Bulk reference.
    # -------------------------------------------------------------------------

    set_bulk_reference(
        return_doc,
        doc.name
    )

    return_doc.set_missing_values()
    return_doc.calculate_taxes_and_totals()

    # -------------------------------------------------------------------------
    # Insert.
    # -------------------------------------------------------------------------

    return_doc.insert(
        ignore_permissions=True
    )

    # -------------------------------------------------------------------------
    # Force reference after insert.
    # -------------------------------------------------------------------------

    persist_bulk_reference(
        return_doc,
        doc.name
    )

    return_doc.reload()

    return_doc.flags.bulk_consolidated_return = True
    return_doc.flags.ignore_permissions = True

    # -------------------------------------------------------------------------
    # Submit.
    # -------------------------------------------------------------------------

    return_doc.submit()

    # -------------------------------------------------------------------------
    # Force reference after submit.
    # -------------------------------------------------------------------------

    persist_bulk_reference(
        return_doc,
        doc.name
    )

    frappe.db.commit()

    return return_doc.name


# =============================================================================
# ACTIVATE SALES-INVOICE-ONLY STOCK
# =============================================================================

def activate_sales_invoice_only_stock(
    doc,
    resolved_rows
):

    for row in resolved_rows:

        if not row.get("sales_invoice_item"):
            continue

        # DN-backed item is handled by DN Return.
        if row.get("delivery_note_item"):
            continue

        sales_invoice = row.get(
            "sales_invoice"
        )

        if not sales_invoice:
            continue

        source_update_stock = frappe.db.get_value(
            "Sales Invoice",
            sales_invoice,
            "update_stock"
        )

        if not source_update_stock:
            continue

        has_serial_no = frappe.db.get_value(
            "Item",
            row.get("item_code"),
            "has_serial_no"
        )

        if not has_serial_no:
            continue

        serials = row.get(
            "serials"
        ) or []

        warehouse = row.get(
            "warehouse"
        )

        for serial_no in serials:

            if not frappe.db.exists(
                "Serial No",
                serial_no
            ):
                continue

            values = {
                "status": "Active"
            }

            if warehouse:
                values["warehouse"] = warehouse

            frappe.db.set_value(
                "Serial No",
                serial_no,
                values,
                update_modified=False
            )

    frappe.db.commit()


# =============================================================================
# DELIVERY NOTE RETURNS
# =============================================================================

def create_delivery_note_returns(
    doc,
    rows
):

    grouped = {}

    for row in rows:

        delivery_note = row.get(
            "delivery_note"
        )

        delivery_note_item = row.get(
            "delivery_note_item"
        )

        if not delivery_note:
            continue

        if not delivery_note_item:
            continue

        grouped.setdefault(
            delivery_note,
            []
        ).append(row)

    created = []

    for delivery_note, source_rows in grouped.items():

        source_dn = frappe.get_doc(
            "Delivery Note",
            delivery_note
        )

        if source_dn.docstatus != 1:

            frappe.throw(
                f"Delivery Note {delivery_note} must be submitted."
            )

        selected = {}

        for row in source_rows:

            delivery_note_item = row.get(
                "delivery_note_item"
            )

            if not delivery_note_item:
                continue

            selected.setdefault(
                delivery_note_item,
                {
                    "qty": 0,
                    "serials": []
                }
            )

            selected[
                delivery_note_item
            ]["qty"] += flt(
                row.get("qty")
            )

            selected[
                delivery_note_item
            ]["serials"].extend(
                row.get("serials") or []
            )

        if not selected:
            continue

        # ============================================================
        # CHECK ALREADY RETURNED QTY
        # ============================================================

        valid_selected = {}

        for delivery_note_item, data in selected.items():

            requested_qty = flt(
                data["qty"]
            )

            original_qty = flt(
                frappe.db.get_value(
                    "Delivery Note Item",
                    delivery_note_item,
                    "qty"
                ) or 0
            )

            already_returned_qty = flt(
                frappe.db.sql(
                    """
                    SELECT
                        IFNULL(
                            SUM(ABS(dni.qty)),
                            0
                        )
                    FROM `tabDelivery Note Item` dni
                    INNER JOIN `tabDelivery Note` dn
                        ON dn.name = dni.parent
                    WHERE dn.docstatus = 1
                    AND dn.is_return = 1
                    AND dni.dn_detail = %s
                    """,
                    delivery_note_item
                )[0][0]
                or 0
            )

            available_qty = (
                original_qty
                - already_returned_qty
            )

            if available_qty <= 0:

                frappe.log_error(
                    (
                        f"Bulk Sales Return {doc.name}: "
                        f"Skipping already returned DN Item "
                        f"{delivery_note_item}."
                    ),
                    "Bulk Sales Return - DN Already Returned"
                )

                continue

            if requested_qty > available_qty:

                frappe.throw(
                    f"Delivery Note Item {delivery_note_item} "
                    f"has only {available_qty} qty available for return, "
                    f"but requested {requested_qty}."
                )

            valid_selected[
                delivery_note_item
            ] = data

        if not valid_selected:
            continue

        # ============================================================
        # CREATE STANDARD DELIVERY NOTE RETURN
        # ============================================================

        return_doc = make_return_doc(
            "Delivery Note",
            source_dn.name
        )

        return_doc.is_return = 1

        return_doc.return_against = (
            source_dn.name
        )

        # ---------------------------------------------------------------------
        # DIRECT FIELD ASSIGNMENT
        # ---------------------------------------------------------------------

        return_doc.custom_bulk_sales_return = (
            doc.name
        )

        kept_items = []

        for return_item in list(
            return_doc.items
        ):

            original_item_name = (
                getattr(
                    return_item,
                    "dn_detail",
                    None
                )
                or None
            )

            if not original_item_name:

                if return_item.idx:

                    original_item_name = frappe.db.get_value(
                        "Delivery Note Item",
                        {
                            "parent": source_dn.name,
                            "idx": return_item.idx
                        },
                        "name"
                    )

            selected_row = valid_selected.get(
                original_item_name
            )

            if not selected_row:
                continue

            return_item.dn_detail = (
                original_item_name
            )

            return_item.qty = -abs(
                flt(
                    selected_row["qty"]
                )
            )

            serials = list(
                dict.fromkeys(
                    selected_row["serials"]
                )
            )

            if serials:

                return_item.serial_no = (
                    "\n".join(serials)
                )

                if hasattr(
                    return_item,
                    "use_serial_batch_fields"
                ):

                    return_item.use_serial_batch_fields = 1

            kept_items.append(
                return_item
            )

        if not kept_items:
            continue

        return_doc.items = kept_items

        for idx, item in enumerate(
            return_doc.items,
            start=1
        ):

            item.idx = idx

        # ============================================================
        # SET AGAIN AFTER ITEM MANIPULATION
        # ============================================================

        return_doc.custom_bulk_sales_return = (
            doc.name
        )

        return_doc.set_missing_values()

        return_doc.flags.ignore_permissions = True

        # ============================================================
        # INSERT
        # ============================================================

        return_doc.insert(
            ignore_permissions=True
        )

        # ============================================================
        # FORCE DATABASE VALUE AFTER INSERT
        # ============================================================

        force_set_delivery_note_bulk_reference(
            return_doc.name,
            doc.name
        )

        # ============================================================
        # VERIFY AFTER INSERT
        # ============================================================

        verify_delivery_note_bulk_reference(
            return_doc.name,
            doc.name
        )

        # ============================================================
        # RELOAD
        # ============================================================

        return_doc.reload()

        return_doc.flags.ignore_permissions = True

        # ============================================================
        # SUBMIT
        # ============================================================

        return_doc.submit()

        # ============================================================
        # FORCE DATABASE VALUE AFTER SUBMIT
        # ============================================================

        force_set_delivery_note_bulk_reference(
            return_doc.name,
            doc.name
        )

        # ============================================================
        # VERIFY AFTER SUBMIT
        # ============================================================

        verify_delivery_note_bulk_reference(
            return_doc.name,
            doc.name
        )

        created.append(
            return_doc.name
        )

        frappe.db.commit()

    # -------------------------------------------------------------------------
    # Final safety reconciliation for all created DN returns.
    # -------------------------------------------------------------------------

    reconcile_delivery_note_bulk_reference(
        doc
    )

    return created


# =============================================================================
# FORCE DELIVERY NOTE BULK REFERENCE
# =============================================================================

def force_set_delivery_note_bulk_reference(
    delivery_note,
    bulk_sales_return
):

    # -------------------------------------------------------------------------
    # Use direct database UPDATE.
    #
    # This is intentional because manual frappe.db.set_value() has already
    # been verified to work for this field.
    # -------------------------------------------------------------------------

    frappe.db.sql(
        """
        UPDATE `tabDelivery Note`
        SET custom_bulk_sales_return = %s
        WHERE name = %s
        """,
        (
            bulk_sales_return,
            delivery_note
        )
    )

    frappe.db.commit()


# =============================================================================
# VERIFY DELIVERY NOTE BULK REFERENCE
# =============================================================================

def verify_delivery_note_bulk_reference(
    delivery_note,
    bulk_sales_return
):

    actual_value = frappe.db.get_value(
        "Delivery Note",
        delivery_note,
        "custom_bulk_sales_return"
    )

    if actual_value != bulk_sales_return:

        frappe.throw(
            f"Unable to save Bulk Sales Return reference "
            f"on Delivery Note Return {delivery_note}. "
            f"Expected {bulk_sales_return}, "
            f"found {actual_value or 'Blank'}."
        )


# =============================================================================
# FINAL DELIVERY NOTE REFERENCE RECONCILIATION
# =============================================================================

def reconcile_delivery_note_bulk_reference(
    doc
):

    # -------------------------------------------------------------------------
    # Find every submitted Delivery Note Return which was created against
    # one of the source Delivery Notes present in this Bulk Sales Return.
    # -------------------------------------------------------------------------

    source_dn_names = set()

    for row in doc.items:

        if row.delivery_note:

            source_dn_names.add(
                row.delivery_note
            )

        if row.delivery_note_item:

            source_dn = frappe.db.get_value(
                "Delivery Note Item",
                row.delivery_note_item,
                "parent"
            )

            if source_dn:

                source_dn_names.add(
                    source_dn
                )

    if not source_dn_names:
        return

    for source_dn in source_dn_names:

        return_dns = frappe.db.sql(
            """
            SELECT
                name
            FROM `tabDelivery Note`
            WHERE docstatus = 1
            AND is_return = 1
            AND return_against = %s
            """,
            source_dn,
            as_dict=True
        )

        for row in return_dns:

            return_dn = row.name

            # -----------------------------------------------------------------
            # Only update if the DN Return belongs to this Bulk.
            #
            # If another Bulk has already created a return against the same
            # source DN, do not overwrite it.
            # -----------------------------------------------------------------

            existing_bulk = frappe.db.get_value(
                "Delivery Note",
                return_dn,
                "custom_bulk_sales_return"
            )

            if existing_bulk and existing_bulk != doc.name:

                continue

            force_set_delivery_note_bulk_reference(
                return_dn,
                doc.name
            )

            verify_delivery_note_bulk_reference(
                return_dn,
                doc.name
            )

    frappe.db.commit()


# =============================================================================
# BULK REFERENCE
# =============================================================================

def set_bulk_reference(
    return_doc,
    bulk_name
):

    meta = frappe.get_meta(
        return_doc.doctype
    )

    if meta.has_field(
        "custom_bulk_sales_return"
    ):

        return_doc.set(
            "custom_bulk_sales_return",
            bulk_name
        )

        return

    if meta.has_field(
        "bulk_sales_return"
    ):

        return_doc.set(
            "bulk_sales_return",
            bulk_name
        )


def persist_bulk_reference(
    return_doc,
    bulk_name
):

    meta = frappe.get_meta(
        return_doc.doctype
    )

    if meta.has_field(
        "custom_bulk_sales_return"
    ):

        frappe.db.set_value(
            return_doc.doctype,
            return_doc.name,
            "custom_bulk_sales_return",
            bulk_name,
            update_modified=False
        )

        frappe.db.commit()

        return

    if meta.has_field(
        "bulk_sales_return"
    ):

        frappe.db.set_value(
            return_doc.doctype,
            return_doc.name,
            "bulk_sales_return",
            bulk_name,
            update_modified=False
        )

        frappe.db.commit()


# =============================================================================
# OLD MANUAL SUBMIT API
# =============================================================================

@frappe.whitelist()
def submit_created_returns(docname):

    doc = frappe.get_doc(
        "Bulk Sales Return",
        docname
    )

    doc.db_set(
        "submit_status",
        "Queued"
    )

    frappe.db.commit()

    frappe.enqueue(
        method=(
            "franchise_erp.franchise_erp.doctype.bulk_sales_return."
            "bulk_sales_return.process_submit_returns"
        ),
        docname=docname,
        queue="long",
        timeout=1200,
        job_name=f"Submit Returns for {docname}"
    )

    return "Queued"


def process_submit_returns(docname):

    doc = frappe.get_doc(
        "Bulk Sales Return",
        docname
    )

    try:

        doc.db_set(
            "submit_status",
            "In Progress"
        )

        frappe.db.commit()

        dns = frappe.get_all(
            "Delivery Note",
            filters={
                "custom_bulk_sales_return": docname,
                "docstatus": 0
            },
            pluck="name"
        )

        for dn in dns:

            dn_doc = frappe.get_doc(
                "Delivery Note",
                dn
            )

            dn_doc.flags.ignore_permissions = True
            dn_doc.submit()

            frappe.db.commit()

        sis = frappe.get_all(
            "Sales Invoice",
            filters={
                "custom_bulk_sales_return": docname,
                "docstatus": 0
            },
            pluck="name"
        )

        for si in sis:

            si_doc = frappe.get_doc(
                "Sales Invoice",
                si
            )

            si_doc.flags.ignore_permissions = True
            si_doc.submit()

            frappe.db.commit()

        doc.db_set(
            "submit_status",
            "Completed"
        )

        frappe.db.commit()

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Submit Sales Returns Failed"
        )

        try:

            doc.db_set(
                "submit_status",
                "Failed"
            )

            frappe.db.commit()

        except Exception:

            frappe.log_error(
                frappe.get_traceback(),
                "Submit Sales Returns Status Update Failed"
            )

        raise


# =============================================================================
# DRAFT RETURN CHECKS
# =============================================================================

@frappe.whitelist()
def has_draft_return_dns(docname):

    exists = frappe.db.exists(
        "Delivery Note",
        {
            "custom_bulk_sales_return": docname,
            "docstatus": 0
        }
    )

    return bool(exists)


@frappe.whitelist()
def has_draft_return_sis(docname):

    exists = frappe.db.exists(
        "Sales Invoice",
        {
            "custom_bulk_sales_return": docname,
            "docstatus": 0
        }
    )

    return bool(exists)


# =============================================================================
# DELIVERY NOTE RETURNABLE ITEMS
# =============================================================================

@frappe.whitelist()
def get_returnable_items(
    customer,
    company,
    item_code=None
):

    conditions = """
        AND dn.customer = %(customer)s
        AND dn.company = %(company)s
    """

    if item_code:

        conditions += """
            AND dni.item_code = %(item_code)s
        """

    items = frappe.db.sql(
        f"""
        SELECT
            dni.parent AS delivery_note,
            dni.name AS delivery_note_item,
            dni.item_code,
            dni.qty AS delivered_qty,
            IFNULL(dni.returned_qty, 0) AS returned_qty,
            (
                dni.qty -
                IFNULL(dni.returned_qty, 0)
            ) AS returnable_qty,
            0 AS return_qty,
            i.has_serial_no
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn
            ON dn.name = dni.parent
        LEFT JOIN `tabItem` i
            ON i.name = dni.item_code
        WHERE dn.docstatus = 1
        AND dn.is_return = 0
        AND dni.qty > IFNULL(dni.returned_qty, 0)
        {conditions}
        ORDER BY dn.posting_date DESC
        """,
        {
            "customer": customer,
            "company": company,
            "item_code": item_code
        },
        as_dict=1
    )

    return items


# =============================================================================
# DELIVERY NOTE ITEM DETAILS
# =============================================================================

@frappe.whitelist()
def get_dn_item_details(items):

    items = frappe.parse_json(
        items
    )

    result = []

    for d in items:

        dn_item = frappe.get_doc(
            "Delivery Note Item",
            d.get("delivery_note_item")
        )

        item_doc = frappe.get_doc(
            "Item",
            dn_item.item_code
        )

        is_serialized = item_doc.has_serial_no

        dn_serials = []

        if dn_item.serial_no:

            dn_serials = [
                s.strip()
                for s in dn_item.serial_no.split("\n")
                if s.strip()
            ]

        returned_serials = frappe.db.sql(
            """
            SELECT dni.serial_no
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn
                ON dni.parent = dn.name
            WHERE dn.is_return = 1
            AND dn.docstatus = 1
            AND dni.dn_detail = %s
            """,
            dn_item.name,
            as_dict=1
        )

        returned_list = []

        for r in returned_serials:

            if r.serial_no:

                returned_list.extend(
                    s.strip()
                    for s in r.serial_no.split("\n")
                    if s.strip()
                )

        available_serials = list(
            set(dn_serials) - set(returned_list)
        )

        scanned_serials = []

        if d.get("serial_nos"):

            scanned_serials = [
                s.strip()
                for s in d.get("serial_nos").split("\n")
                if s.strip()
            ]

        invalid_serials = list(
            set(scanned_serials) - set(available_serials)
        )

        if invalid_serials:

            frappe.throw(
                f"Invalid Serial(s) for Item "
                f"{dn_item.item_code}: "
                f"{', '.join(invalid_serials)}"
            )

        warehouse_map = {}

        if is_serialized:

            for serial in scanned_serials:

                serial_doc = frappe.get_doc(
                    "Serial No",
                    serial
                )

                wh = (
                    serial_doc.warehouse
                    or dn_item.warehouse
                )

                warehouse_map.setdefault(
                    wh,
                    []
                ).append(
                    serial
                )

            for wh, serial_list in warehouse_map.items():

                result.append({
                    "name": dn_item.name,
                    "delivery_note": dn_item.parent,
                    "delivery_note_item": dn_item.name,
                    "item_code": dn_item.item_code,
                    "item_name": dn_item.item_name,
                    "warehouse": wh,
                    "uom": dn_item.uom,
                    "stock_uom": dn_item.stock_uom,
                    "conversion_factor": dn_item.conversion_factor,
                    "rate": dn_item.rate,
                    "qty": len(serial_list),
                    "returnable_quantity": d.get(
                        "returnable_qty"
                    ),
                    "serial_nos": "\n".join(
                        serial_list
                    ),
                    "available_serial_nos": "\n".join(
                        available_serials
                    )
                })

        else:

            qty = flt(
                d.get("return_qty")
            )

            wh = dn_item.warehouse

            warehouse_map.setdefault(
                wh,
                0
            )

            warehouse_map[wh] += qty

            for wh, qty in warehouse_map.items():

                result.append({
                    "name": dn_item.name,
                    "delivery_note": dn_item.parent,
                    "delivery_note_item": dn_item.name,
                    "item_code": dn_item.item_code,
                    "item_name": dn_item.item_name,
                    "warehouse": wh,
                    "uom": dn_item.uom,
                    "stock_uom": dn_item.stock_uom,
                    "conversion_factor": dn_item.conversion_factor,
                    "rate": dn_item.rate,
                    "qty": qty,
                    "returnable_quantity": d.get(
                        "returnable_qty"
                    ),
                    "serial_nos": "",
                    "available_serial_nos": ""
                })

    return result


# =============================================================================
# DELIVERY NOTE SERIAL SEARCH
# =============================================================================

@frappe.whitelist()
def get_dn_from_serial(
    serial_no,
    company
):

    serial_no = (
        serial_no or ""
    ).strip()

    dn_items = frappe.db.sql(
        """
        SELECT
            dni.name,
            dni.parent AS delivery_note,
            dni.item_code,
            dni.qty,
            dni.returned_qty,
            dni.serial_no,
            dn.posting_date,
            dn.posting_time,
            dn.creation
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn
            ON dn.name = dni.parent
        WHERE dn.docstatus = 1
        AND dn.is_return = 0
        AND dn.company = %s
        AND dni.serial_no LIKE %s
        ORDER BY
            dn.posting_date DESC,
            dn.posting_time DESC,
            dn.creation DESC
        """,
        (
            company,
            f"%{serial_no}%"
        ),
        as_dict=True
    )

    if not dn_items:
        return None

    for dn_item in dn_items:

        actual_serials = [
            s.strip()
            for s in (
                dn_item.serial_no or ""
            ).split("\n")
            if s.strip()
        ]

        if serial_no not in actual_serials:
            continue

        returned_serials = frappe.db.sql(
            """
            SELECT dni.serial_no
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn
                ON dni.parent = dn.name
            WHERE dn.docstatus = 1
            AND dn.is_return = 1
            AND dni.dn_detail = %s
            """,
            dn_item.name,
            as_dict=True
        )

        already_returned = []

        for returned in returned_serials:

            if returned.serial_no:

                already_returned.extend(
                    s.strip()
                    for s in returned.serial_no.split("\n")
                    if s.strip()
                )

        if serial_no in already_returned:
            continue

        serial = frappe.get_doc(
            "Serial No",
            serial_no
        )

        return {
            "delivery_note": dn_item.delivery_note,
            "delivery_note_item": dn_item.name,
            "item_code": dn_item.item_code,
            "serial_no": serial_no,
            "status": serial.status,
            "returnable_qty": 1,
            "returned_qty": 0,
            "return_qty": 1
        }

    return None


# =============================================================================
# SALES INVOICE SERIAL SEARCH
# =============================================================================

@frappe.whitelist()
def get_si_from_serial(
    serial_no,
    company,
    sales_invoice=None,
    customer=None
):

    serial_no = (
        serial_no or ""
    ).strip()

    conditions = """
        AND si.company = %(company)s
        AND sii.serial_no LIKE %(serial_pattern)s
    """

    params = {
        "serial_pattern": f"%{serial_no}%",
        "company": company
    }

    if sales_invoice:

        conditions += """
            AND si.name = %(sales_invoice)s
        """

        params["sales_invoice"] = sales_invoice

    if customer:

        conditions += """
            AND si.customer = %(customer)s
        """

        params["customer"] = customer

    si_items = frappe.db.sql(
        f"""
        SELECT
            sii.name AS sales_invoice_item,
            sii.parent AS sales_invoice,
            sii.item_code,
            sii.item_name,
            sii.qty AS billed_qty,
            sii.rate,
            sii.warehouse,
            i.has_serial_no,
            si.posting_date,
            si.posting_time,
            si.creation,
            sii.serial_no
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code
        WHERE si.docstatus = 1
        AND si.is_return = 0
        AND si.update_stock = 1
        {conditions}
        ORDER BY
            si.posting_date DESC,
            si.posting_time DESC,
            si.creation DESC
        """,
        params,
        as_dict=True
    )

    if not si_items:
        return None

    if not frappe.db.exists(
        "Serial No",
        serial_no
    ):
        return None

    serial = frappe.get_doc(
        "Serial No",
        serial_no
    )

    for si_item in si_items:

        actual_serials = [
            s.strip()
            for s in (
                si_item.serial_no or ""
            ).split("\n")
            if s.strip()
        ]

        if serial_no not in actual_serials:
            continue

        returned_serials = frappe.db.sql(
            """
            SELECT sii2.serial_no
            FROM `tabSales Invoice Item` sii2
            INNER JOIN `tabSales Invoice` si2
                ON si2.name = sii2.parent
            WHERE si2.docstatus = 1
            AND si2.is_return = 1
            AND sii2.sales_invoice_item = %s
            """,
            si_item.sales_invoice_item,
            as_dict=True
        )

        already_returned = []

        for returned in returned_serials:

            if returned.serial_no:

                already_returned.extend(
                    s.strip()
                    for s in returned.serial_no.split("\n")
                    if s.strip()
                )

        if serial_no in already_returned:
            continue

        returned_qty = frappe.db.sql(
            """
            SELECT
                IFNULL(
                    SUM(ABS(sii2.qty)),
                    0
                ) AS returned_qty
            FROM `tabSales Invoice Item` sii2
            INNER JOIN `tabSales Invoice` si2
                ON si2.name = sii2.parent
            WHERE si2.docstatus = 1
            AND si2.is_return = 1
            AND sii2.sales_invoice_item = %s
            """,
            si_item.sales_invoice_item,
            as_dict=True
        )

        returned_qty_val = (
            flt(
                returned_qty[0].returned_qty
            )
            if returned_qty
            else 0
        )

        returnable_qty = (
            flt(si_item.billed_qty)
            - returned_qty_val
        )

        if returnable_qty <= 0:
            continue

        return {
            "sales_invoice": si_item.sales_invoice,
            "sales_invoice_item": si_item.sales_invoice_item,
            "item_code": si_item.item_code,
            "item_name": si_item.item_name,
            "warehouse": si_item.warehouse,
            "rate": si_item.rate,
            "has_serial_no": si_item.has_serial_no,
            "status": serial.status,
            "returnable_qty": returnable_qty,
            "returned_qty": returned_qty_val,
            "return_qty": 1,
            "serial_nos": serial_no
        }

    return None


# =============================================================================
# SALES INVOICE ITEMS
# =============================================================================

@frappe.whitelist()
def get_sales_invoice_items(
    sales_invoice
):

    doc = frappe.get_doc(
        "Sales Invoice",
        sales_invoice
    )

    items = []

    for d in doc.items:

        items.append({
            "sales_invoice": doc.name,
            "sales_invoice_item": d.name,
            "item_code": d.item_code,
            "item_name": d.item_name,
            "qty": d.qty,
            "rate": d.rate,
            "warehouse": d.warehouse
        })

    return items


# =============================================================================
# SALES INVOICE RETURNABLE ITEMS
# =============================================================================

@frappe.whitelist()
def get_sales_invoice_returnable_items(
    customer,
    company,
    sales_invoice=None,
    item_code=None
):

    conditions = """
        AND si.customer = %(customer)s
        AND si.company = %(company)s
    """

    if sales_invoice:

        conditions += """
            AND si.name = %(sales_invoice)s
        """

    if item_code:

        conditions += """
            AND sii.item_code = %(item_code)s
        """

    items = frappe.db.sql(
        f"""
        SELECT
            sii.parent AS sales_invoice,
            sii.name AS sales_invoice_item,
            sii.item_code,
            sii.item_name,
            sii.qty AS billed_qty,

            CASE
                WHEN si.update_stock = 1
                    THEN sii.qty
                ELSE sii.delivered_qty
            END AS delivered_qty,

            IFNULL(
                (
                    SELECT
                        SUM(ABS(sii2.qty))
                    FROM `tabSales Invoice Item` sii2
                    INNER JOIN `tabSales Invoice` si2
                        ON si2.name = sii2.parent
                    WHERE si2.docstatus = 1
                    AND si2.is_return = 1
                    AND sii2.sales_invoice_item = sii.name
                ),
                0
            ) AS returned_qty,

            (
                CASE
                    WHEN si.update_stock = 1
                        THEN sii.qty
                    ELSE sii.delivered_qty
                END
                -
                IFNULL(
                    (
                        SELECT
                            SUM(ABS(sii2.qty))
                        FROM `tabSales Invoice Item` sii2
                        INNER JOIN `tabSales Invoice` si2
                            ON si2.name = sii2.parent
                        WHERE si2.docstatus = 1
                        AND si2.is_return = 1
                        AND sii2.sales_invoice_item = sii.name
                    ),
                    0
                )
            ) AS returnable_qty,

            0 AS return_qty,
            i.has_serial_no,
            sii.rate,
            sii.warehouse

        FROM `tabSales Invoice Item` sii

        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent

        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code

        WHERE si.docstatus = 1
        AND si.is_return = 0

        {conditions}

        AND (
            sii.delivered_qty > 0
            OR si.update_stock = 1
        )

        HAVING returnable_qty > 0

        ORDER BY si.posting_date DESC
        """,
        {
            "sales_invoice": sales_invoice,
            "customer": customer,
            "company": company,
            "item_code": item_code
        },
        as_dict=1
    )

    return items


# =============================================================================
# COMMON SI / DN SERIAL SOURCE
# =============================================================================

@frappe.whitelist()
def get_return_source_from_serial(
    serial_no,
    company,
    customer=None
):

    serial_no = (
        serial_no or ""
    ).strip()

    if not serial_no:
        return None

    if not frappe.db.exists(
        "Serial No",
        serial_no
    ):
        return None

    serial_doc = frappe.get_doc(
        "Serial No",
        serial_no
    )

    # =========================================================================
    # FIRST: SALES INVOICE
    # =========================================================================

    si_conditions = """
        si.docstatus = 1
        AND si.is_return = 0
        AND si.company = %(company)s
        AND si.update_stock = 1
        AND sii.serial_no LIKE %(serial_pattern)s
    """

    si_params = {
        "company": company,
        "serial_pattern": f"%{serial_no}%"
    }

    if customer:

        si_conditions += """
            AND si.customer = %(customer)s
        """

        si_params["customer"] = customer

    si_items = frappe.db.sql(
        f"""
        SELECT
            sii.name AS sales_invoice_item,
            sii.parent AS sales_invoice,
            sii.item_code,
            sii.item_name,
            sii.qty AS billed_qty,
            sii.rate,
            sii.warehouse,
            sii.serial_no,
            i.has_serial_no,
            si.posting_date,
            si.posting_time,
            si.creation
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code
        WHERE {si_conditions}
        ORDER BY
            si.posting_date DESC,
            si.posting_time DESC,
            si.creation DESC
        """,
        si_params,
        as_dict=True
    )

    for si_item in si_items:

        actual_serials = [
            s.strip()
            for s in (
                si_item.serial_no or ""
            ).split("\n")
            if s.strip()
        ]

        if serial_no not in actual_serials:
            continue

        returned_serials = frappe.db.sql(
            """
            SELECT sii2.serial_no
            FROM `tabSales Invoice Item` sii2
            INNER JOIN `tabSales Invoice` si2
                ON si2.name = sii2.parent
            WHERE si2.docstatus = 1
            AND si2.is_return = 1
            AND sii2.sales_invoice_item = %s
            """,
            si_item.sales_invoice_item,
            as_dict=True
        )

        already_returned = []

        for r in returned_serials:

            if r.serial_no:

                already_returned.extend(
                    s.strip()
                    for s in r.serial_no.split("\n")
                    if s.strip()
                )

        if serial_no in already_returned:
            continue

        dn_detail = frappe.db.get_value(
            "Sales Invoice Item",
            si_item.sales_invoice_item,
            "dn_detail"
        )

        delivery_note = None
        delivery_note_item = None

        if dn_detail:

            dn_data = frappe.db.get_value(
                "Delivery Note Item",
                dn_detail,
                [
                    "parent",
                    "name"
                ],
                as_dict=True
            )

            if dn_data:

                delivery_note = dn_data.parent
                delivery_note_item = dn_data.name

        return {
            "source_type": "Sales Invoice",

            "sales_invoice": si_item.sales_invoice,
            "sales_invoice_item": si_item.sales_invoice_item,

            "delivery_note": delivery_note,
            "delivery_note_item": delivery_note_item,

            "item_code": si_item.item_code,
            "item_name": si_item.item_name,

            "warehouse": si_item.warehouse,
            "rate": si_item.rate,

            "has_serial_no": si_item.has_serial_no,

            "status": serial_doc.status,

            "returnable_qty": 1,
            "returned_qty": 0,
            "return_qty": 1,

            "serial_nos": serial_no
        }

    # =========================================================================
    # SECOND: DELIVERY NOTE
    # =========================================================================

    dn_conditions = """
        dn.docstatus = 1
        AND dn.is_return = 0
        AND dn.company = %(company)s
        AND dni.serial_no LIKE %(serial_pattern)s
    """

    dn_params = {
        "company": company,
        "serial_pattern": f"%{serial_no}%"
    }

    if customer:

        dn_conditions += """
            AND dn.customer = %(customer)s
        """

        dn_params["customer"] = customer

    dn_items = frappe.db.sql(
        f"""
        SELECT
            dni.name AS delivery_note_item,
            dni.parent AS delivery_note,
            dni.item_code,
            dni.serial_no,
            dni.item_name,
            dni.qty AS delivered_qty,
            dni.returned_qty,
            dni.rate,
            dni.warehouse,
            dni.uom,
            dni.stock_uom,
            dni.conversion_factor,
            i.has_serial_no,
            dn.posting_date,
            dn.posting_time,
            dn.creation
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn
            ON dn.name = dni.parent
        LEFT JOIN `tabItem` i
            ON i.name = dni.item_code
        WHERE {dn_conditions}
        ORDER BY
            dn.posting_date DESC,
            dn.posting_time DESC,
            dn.creation DESC
        """,
        dn_params,
        as_dict=True
    )

    for dn_item in dn_items:

        original_serials = [
            s.strip()
            for s in (
                dn_item.serial_no or ""
            ).split("\n")
            if s.strip()
        ]

        if serial_no not in original_serials:
            continue

        returned_serials = frappe.db.sql(
            """
            SELECT dni.serial_no
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn
                ON dn.name = dni.parent
            WHERE dn.docstatus = 1
            AND dn.is_return = 1
            AND dni.dn_detail = %s
            """,
            dn_item.delivery_note_item,
            as_dict=True
        )

        already_returned = []

        for returned in returned_serials:

            if returned.serial_no:

                already_returned.extend(
                    s.strip()
                    for s in returned.serial_no.split("\n")
                    if s.strip()
                )

        if serial_no in already_returned:
            continue

        # ---------------------------------------------------------------------
        # Find related Sales Invoice.
        # ---------------------------------------------------------------------

        si_items = frappe.db.sql(
            """
            SELECT
                sii.name,
                sii.parent,
                si.posting_date,
                si.posting_time,
                si.creation
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE sii.dn_detail = %s
            AND si.docstatus = 1
            AND si.is_return = 0
            ORDER BY
                si.posting_date DESC,
                si.posting_time DESC,
                si.creation DESC
            """,
            dn_item.delivery_note_item,
            as_dict=True
        )

        si_item = (
            si_items[0]
            if si_items
            else None
        )

        return {
            "source_type": "Delivery Note",

            "sales_invoice": (
                si_item.parent
                if si_item
                else None
            ),

            "sales_invoice_item": (
                si_item.name
                if si_item
                else None
            ),

            "delivery_note": dn_item.delivery_note,
            "delivery_note_item": dn_item.delivery_note_item,

            "item_code": dn_item.item_code,
            "item_name": dn_item.item_name,

            "warehouse": dn_item.warehouse,
            "rate": dn_item.rate,

            "uom": dn_item.uom,
            "stock_uom": dn_item.stock_uom,
            "conversion_factor": dn_item.conversion_factor,

            "has_serial_no": dn_item.has_serial_no,

            "status": serial_doc.status,

            "returnable_qty": 1,
            "returned_qty": 0,
            "return_qty": 1,

            "serial_nos": serial_no
        }

    return None
