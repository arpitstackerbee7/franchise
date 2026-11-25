import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, strip_html
from erpnext.controllers.sales_and_purchase_return import make_return_doc


class BulkSalesReturn(Document):

    def validate(self):
        self.remove_duplicate_serial_rows()
        self.validate_customer()
        self.validate_qty()
        self.validate_billing_addresses()

    # -------------------------------------------------------------------------
    # DUPLICATE SERIAL PROTECTION
    # -------------------------------------------------------------------------

    def remove_duplicate_serial_rows(self):
        """Keep each serial number only once across the Items table."""

        seen_serials = set()
        rows_to_remove = []

        for row in list(self.items or []):
            raw_serials = (row.get("serial_nos") or "").replace(",", "\n")
            serials = list(dict.fromkeys(
                serial.strip()
                for serial in raw_serials.splitlines()
                if serial.strip()
            ))

            if not serials:
                continue

            unique_serials = []
            for serial in serials:
                if serial in seen_serials:
                    continue
                seen_serials.add(serial)
                unique_serials.append(serial)

            if not unique_serials:
                rows_to_remove.append(row)
                continue

            # FIX: hamesha newline format me save karo (comma wale bhi normalize)
            row.serial_nos = "\n".join(unique_serials)

            has_serial_no = frappe.db.get_value(
                "Item", row.item_code, "has_serial_no"
            )

            if has_serial_no:
                row.qty = len(unique_serials)

        for row in rows_to_remove:
            self.remove(row)

        if rows_to_remove:
            frappe.msgprint(
                _("Removed {0} duplicate serial-number row(s) from Items.").format(
                    len(rows_to_remove)
                ),
                indicator="orange",
                alert=True,
            )

    # -------------------------------------------------------------------------
    # CUSTOMER VALIDATION
    # -------------------------------------------------------------------------

    def validate_customer(self):

        customers = set()

        for row in self.items:

            customer = None

            if row.delivery_note:
                customer = frappe.db.get_value(
                    "Delivery Note", row.delivery_note, "customer"
                )

            elif row.sales_invoice:
                customer = frappe.db.get_value(
                    "Sales Invoice", row.sales_invoice, "customer"
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
                frappe.throw(f"Return qty must be greater than 0 in row {row.idx}")

            # ---------------------------------------------------------------
            # DELIVERY NOTE ROW
            # ---------------------------------------------------------------

            if row.delivery_note_item:

                sent_qty = frappe.db.get_value(
                    "Delivery Note Item", row.delivery_note_item, "qty"
                ) or 0

                returned_qty = frappe.db.sql(
                    """
                    SELECT IFNULL(SUM(ABS(dni.qty)), 0)
                    FROM `tabDelivery Note Item` dni
                    INNER JOIN `tabDelivery Note` dn
                        ON dn.name = dni.parent
                    WHERE dn.docstatus = 1
                    AND dn.is_return = 1
                    AND dni.dn_detail = %s
                    """,
                    row.delivery_note_item
                )[0][0] or 0

                available_qty = flt(sent_qty) - flt(returned_qty)

                if qty > available_qty:
                    frappe.throw(
                        f"Return qty cannot exceed returnable qty "
                        f"({available_qty}) in row {row.idx}"
                    )

            # ---------------------------------------------------------------
            # SALES INVOICE ROW
            # ---------------------------------------------------------------

            elif row.sales_invoice_item:

                si_data = frappe.db.get_value(
                    "Sales Invoice Item",
                    row.sales_invoice_item,
                    ["qty", "delivered_qty", "parent"],
                    as_dict=True
                )

                if si_data:

                    sales_invoice = si_data.parent

                    update_stock = frappe.db.get_value(
                        "Sales Invoice", sales_invoice, "update_stock"
                    )

                    if update_stock:
                        available_qty = flt(si_data.qty)
                    else:
                        available_qty = flt(si_data.delivered_qty)

                    already_returned = frappe.db.sql(
                        """
                        SELECT IFNULL(SUM(ABS(sii.qty)), 0)
                        FROM `tabSales Invoice Item` sii
                        INNER JOIN `tabSales Invoice` si
                            ON si.name = sii.parent
                        WHERE si.docstatus = 1
                        AND si.is_return = 1
                        AND sii.sales_invoice_item = %s
                        """,
                        row.sales_invoice_item
                    )[0][0] or 0

                    available_qty -= flt(already_returned)

                    if qty > available_qty:
                        frappe.throw(
                            f"Return qty cannot exceed returnable qty "
                            f"({available_qty}) in row {row.idx}"
                        )

            # ---------------------------------------------------------------
            # SERIAL VALIDATION
            # ---------------------------------------------------------------

            has_serial_no = frappe.db.get_value(
                "Item", row.item_code, "has_serial_no"
            )

            if has_serial_no and (
                row.delivery_note_item or row.sales_invoice_item
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

    # -------------------------------------------------------------------------
    # BILLING ADDRESS VALIDATION
    # -------------------------------------------------------------------------

    def validate_billing_addresses(self):
        for row in self.items or []:
            if not row.delivery_note:
                continue

            source = frappe.db.get_value(
                "Delivery Note",
                row.delivery_note,
                ["customer", "customer_address"],
                as_dict=True
            )

            if not source:
                continue

            address = source.customer_address

            if not address:
                continue

            address_linked = frappe.db.exists(
                "Dynamic Link",
                {
                    "parent": address,
                    "parenttype": "Address",
                    "link_doctype": "Customer",
                    "link_name": source.customer,
                },
            )

            if not address_linked:
                frappe.throw(
                    _(
                        "Cannot save Bulk Sales Return. The address '{0}' "
                        "on Delivery Note '{1}' is not linked to Customer '{2}'. "
                        "Please correct the address on the original Delivery Note."
                    ).format(
                        address,
                        row.delivery_note,
                        source.customer,
                    ),
                    title=_("Invalid Customer Address"),
                )

    # =========================================================================
    # ON SUBMIT
    # FIX: manual frappe.db.commit() hataya, enqueue_after_commit=True lagaya
    # =========================================================================

    def on_submit(self):

        self.db_set("status", "Queued")

        frappe.enqueue(
            method=(
                "franchise_erp.franchise_erp.doctype.bulk_sales_return."
                "bulk_sales_return.process_bulk_sales_return"
            ),
            docname=self.name,
            queue="long",
            timeout=1200,
            job_name=f"Bulk Sales Return {self.name}",
            enqueue_after_commit=True,
        )

        frappe.msgprint("Return documents are being created in the background.")

    # =========================================================================
    # BEFORE CANCEL
    #
    # Draft Delivery Note / Sales Invoice returns created from this Bulk Sales
    # Return are DELETED (drafts cannot be "cancelled" in ERPNext).
    # Submitted returns are NOT touched - only a warning is shown.
    # =========================================================================

    def before_cancel(self):

        # Background job still running -> do not allow cancel
        if self.status in ("Queued", "In Progress"):
            frappe.throw(
                _(
                    "Bulk Sales Return is still being processed ({0}). "
                    "Please wait until it is Completed or Failed, then cancel."
                ).format(self.status)
            )

        deleted = []
        submitted = []

        for doctype in ("Delivery Note", "Sales Invoice"):

            linked_docs = frappe.get_all(
                doctype,
                filters={
                    "custom_bulk_sales_return": self.name,
                    "is_return": 1,
                    "docstatus": ["in", [0, 1]],
                },
                fields=["name", "docstatus"],
                order_by="creation desc",
            )

            for d in linked_docs:

                # Draft -> delete
                if d.docstatus == 0:

                    frappe.delete_doc(
                        doctype,
                        d.name,
                        ignore_permissions=True,
                        force=True,
                    )

                    deleted.append(f"{doctype}: {d.name}")

                # Submitted -> leave as it is, only inform
                else:
                    submitted.append(f"{doctype}: {d.name}")

        if deleted:
            frappe.msgprint(
                _("Draft return documents deleted:<br>{0}").format(
                    "<br>".join(deleted)
                ),
                indicator="green",
                alert=True,
            )

        if submitted:
            frappe.msgprint(
                _(
                    "These return documents are already submitted and were NOT "
                    "changed. Cancel them manually if required:<br>{0}"
                ).format("<br>".join(submitted)),
                indicator="orange",
            )


# =============================================================================
# MAIN BULK PROCESS
# FIX: hamesha max 1 SI return + max 1 DN return.
#      Sirf SI-only items  -> SI return update_stock=1
#      DN-backed / mixed   -> SI return update_stock=0 + DN return (stock
#                             dono tarah ke items ka DN return se wapas aata hai)
# =============================================================================
def process_bulk_sales_return(docname):

    lock_name = f"bulk_sales_return_si_creation:{docname}"
    lock_acquired = False

    try:
        lock_result = frappe.db.sql(
            "SELECT GET_LOCK(%s, 30) AS lock_acquired",
            lock_name,
            as_dict=True,
        )
        lock_acquired = bool(
            lock_result and lock_result[0].get("lock_acquired") == 1
        )

        if not lock_acquired:
            frappe.throw(
                f"Unable to acquire processing lock for "
                f"Bulk Sales Return {docname}. Please try again."
            )

        doc = frappe.get_doc("Bulk Sales Return", docname)

        if doc.docstatus != 1:
            return

        if doc.status == "Completed":
            existing_si = get_existing_bulk_sales_invoice_return(docname)
            existing_dn = frappe.db.exists(
                "Delivery Note",
                {
                    "custom_bulk_sales_return": docname,
                    "is_return": 1,
                    "docstatus": ["in", [0, 1]],
                },
            )
            if existing_si or existing_dn:
                return

        doc.db_set("status", "In Progress")
        frappe.db.commit()

        if not doc.items:
            frappe.throw("No return items found.")

        resolved_rows = []
        for row in doc.items:
            resolved = resolve_bulk_return_row(row)
            if not resolved:
                frappe.throw(f"Unable to resolve return source for row {row.idx}")
            resolved_rows.append(resolved)

        # ---------------------------------------------------------------
        # SINGLE CONSOLIDATED SALES INVOICE RETURN ONLY
        # Stock movement is handled by Sales Invoice Return (update_stock=1).
        # No Delivery Note Return is created.
        # ---------------------------------------------------------------

        si_rows = [
            r for r in resolved_rows
            if r.get("sales_invoice_item")
        ]

        unresolved_rows = [
            r for r in resolved_rows
            if not r.get("sales_invoice_item")
        ]

        if unresolved_rows:
            row_details = ", ".join(
                f"Row {getattr(r.get('row'), 'idx', '?')}: "
                f"{r.get('item_code') or 'Unknown Item'}"
                for r in unresolved_rows
            )
            frappe.throw(
                _("These return items could not be mapped to Sales Invoice Items: {0}").format(
                    row_details
                )
            )

        if len(si_rows) != len(resolved_rows):
            frappe.throw(
                _("Not all return items could be mapped to Sales Invoice Items.")
            )

        if not si_rows:
            frappe.throw(_("No Sales Invoice Items found for return."))

        # Remove only old DRAFT returns linked to this Bulk Sales Return.
        delete_draft_bulk_returns(doc.name)

        if not get_existing_bulk_sales_invoice_return(doc.name):
            create_single_sales_invoice_return(
                doc,
                si_rows,
                update_stock=1,
            )

        doc.db_set("status", "Completed")
        frappe.db.commit()


    except Exception as e:

        frappe.db.rollback()

        error_traceback = frappe.get_traceback()
        frappe.log_error(
            title=f"Bulk Sales Return Failed - {docname}",
            message=error_traceback,
        )

        error_detail = strip_html(str(e) or e.__class__.__name__).strip()
        if len(error_detail) > 600:
            error_detail = error_detail[:600] + "..."

        user_message = _(
            "Bulk Sales Return {0} could not be completed.\n\nReason: {1}"
        ).format(docname, error_detail)

        try:
            frappe.db.set_value(
                "Bulk Sales Return", docname, "status", "Failed",
                update_modified=False,
            )
            if frappe.db.has_column("Bulk Sales Return", "error_message"):
                frappe.db.set_value(
                    "Bulk Sales Return", docname, "error_message",
                    user_message, update_modified=False,
                )
            frappe.db.commit()
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Bulk Sales Return Status Update Failed",
            )

        try:
            frappe.publish_realtime(
                event="msgprint",
                message={
                    "title": _("Bulk Sales Return Failed"),
                    "message": user_message.replace("\n", "<br>"),
                    "indicator": "red",
                },
                user=frappe.session.user,
            )
        except Exception:
            pass

        raise

    finally:
        if lock_acquired:
            try:
                frappe.db.sql("SELECT RELEASE_LOCK(%s)", lock_name)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Failed to release Bulk Sales Return lock {docname}",
                )


# =============================================================================
# DELETE OLD DRAFT RETURNS OF THIS BULK SALES RETURN
# =============================================================================
def delete_draft_bulk_returns(bulk_sales_return):

    for doctype in ("Sales Invoice", "Delivery Note"):

        drafts = frappe.get_all(
            doctype,
            filters={
                "custom_bulk_sales_return": bulk_sales_return,
                "is_return": 1,
                "docstatus": 0,
            },
            pluck="name",
        )

        for name in drafts:
            frappe.delete_doc(
                doctype, name, force=True, ignore_permissions=True
            )


# =============================================================================
# VERIFY DN RETURN HAS ALL ITEMS
# =============================================================================
def verify_dn_return_items(bulk_sales_return, dn_rows, stock_si_rows):

    expected = sum(flt(r.get("qty")) for r in dn_rows) + sum(
        flt(r.get("qty")) for r in stock_si_rows
    )

    dn_name = frappe.db.get_value(
        "Delivery Note",
        {
            "custom_bulk_sales_return": bulk_sales_return,
            "is_return": 1,
            "docstatus": ["in", [0, 1]],
        },
        "name",
    )

    if not dn_name:
        frappe.throw("Delivery Note return was not created.")

    actual = flt(
        frappe.db.sql(
            """
            SELECT IFNULL(SUM(ABS(qty)), 0)
            FROM `tabDelivery Note Item`
            WHERE parent = %s
            """,
            dn_name,
        )[0][0]
    )

    if abs(actual - expected) > 0.0001:
        frappe.throw(
            f"Delivery Note return {dn_name} has qty {actual} but "
            f"{expected} was expected (DN items + SI-only items). "
            f"Serials of missing items will not become Active."
        )


# =============================================================================
# SPLIT SI ROWS BY STOCK EFFECT  (NEW)
#   Stock wale  : original SI me update_stock=1 aur koi DN link nahi
#                 -> SI Return update_stock=1 (SLE banega, serial Active hoga)
#   Billing wale: DN-backed (ya non-stock SI)
#                 -> SI Return update_stock=0 (stock DN Return se wapas aata hai)
# =============================================================================
def split_si_rows_by_stock_effect(si_rows):

    stock_rows = []
    billing_rows = []
    update_stock_cache = {}

    for r in si_rows:

        si_name = r.get("sales_invoice")

        if si_name not in update_stock_cache:
            update_stock_cache[si_name] = bool(
                frappe.db.get_value("Sales Invoice", si_name, "update_stock")
            )

        if update_stock_cache[si_name] and not r.get("delivery_note_item"):
            stock_rows.append(r)
        else:
            billing_rows.append(r)

    return stock_rows, billing_rows


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
            frappe.throw(f"Sales Invoice Item {row.sales_invoice_item} not found.")

        result["source_type"] = "Sales Invoice"

        result["sales_invoice"] = si_item.parent
        result["sales_invoice_item"] = row.sales_invoice_item

        result["item_code"] = si_item.item_code
        result["item_name"] = si_item.item_name
        result["rate"] = si_item.rate
        result["warehouse"] = si_item.warehouse

        # Resolve DN using exact dn_detail
        if si_item.dn_detail:

            dn_data = frappe.db.get_value(
                "Delivery Note Item",
                si_item.dn_detail,
                ["parent", "name", "item_code", "warehouse"],
                as_dict=True
            )

            if dn_data:
                result["delivery_note"] = dn_data.parent
                result["delivery_note_item"] = dn_data.name

        # Fallback using delivery_note
        elif si_item.delivery_note:

            result["delivery_note"] = si_item.delivery_note

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
            frappe.throw(f"Delivery Note Item {row.delivery_note_item} not found.")

        result["source_type"] = "Delivery Note"

        result["delivery_note"] = dn_item.parent
        result["delivery_note_item"] = dn_item.name

        result["item_code"] = dn_item.item_code
        result["item_name"] = dn_item.item_name
        result["rate"] = dn_item.rate
        result["warehouse"] = dn_item.warehouse

        # Find related Sales Invoice Item through exact dn_detail
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
                (dn_item.parent, dn_item.item_code),
                as_dict=True
            )

            if si_item:

                si_item = si_item[0]

                result["sales_invoice"] = si_item.parent
                result["sales_invoice_item"] = si_item.name

        return result

    return None


# =============================================================================
# FIND EXISTING BULK SALES INVOICE RETURN
# FIX: update_stock ke hisab se alag-alag existing return check hota hai
# =============================================================================

def get_existing_bulk_sales_invoice_return(bulk_sales_return, update_stock=None):

    if not bulk_sales_return:
        return None

    meta = frappe.get_meta("Sales Invoice")

    if not meta.has_field("custom_bulk_sales_return"):
        return None

    conditions = ""
    params = [bulk_sales_return]

    if update_stock is not None:
        conditions = " AND update_stock = %s"
        params.append(1 if update_stock else 0)

    # Only Draft / Submitted returns are considered.
    # Cancelled return should NOT block creation of a new return.
    existing = frappe.db.sql(
        f"""
        SELECT name, docstatus, creation
        FROM `tabSales Invoice`
        WHERE custom_bulk_sales_return = %s
        AND is_return = 1
        AND docstatus IN (0, 1)
        {conditions}
        ORDER BY creation ASC
        LIMIT 1
        """,
        params,
        as_dict=True
    )

    if existing:
        return existing[0].name

    return None


# =============================================================================
# CREATE ONE CONSOLIDATED SALES INVOICE RETURN
# FIX: update_stock parameter (1 = SI-only items, 0 = DN-backed items)
# =============================================================================

def create_single_sales_invoice_return(doc, rows, update_stock=None):

    # ---------------------------------------------------------------------
    # HARD DUPLICATE PROTECTION
    # ---------------------------------------------------------------------

    if not doc or not doc.name:
        return None

    existing_return = get_existing_bulk_sales_invoice_return(doc.name, update_stock)

    if existing_return:
        frappe.logger().warning(
            f"Bulk Sales Return {doc.name}: Sales Invoice Return "
            f"{existing_return} already exists. NEW SI RETURN WILL NOT BE CREATED."
        )
        return existing_return

    if not rows:
        return None

    # ---------------------------------------------------------------------
    # COMBINE DUPLICATE SALES INVOICE ITEM ROWS
    # ---------------------------------------------------------------------

    selected = {}

    for row in rows:

        sales_invoice_item = row.get("sales_invoice_item")

        if not sales_invoice_item:
            continue

        if sales_invoice_item not in selected:
            selected[sales_invoice_item] = {
                "sales_invoice": row.get("sales_invoice"),
                "qty": 0,
                "serials": [],
                "item_code": row.get("item_code"),
                "rate": row.get("rate"),
                "warehouse": row.get("warehouse"),
                "item_name": row.get("item_name"),
                "delivery_note": row.get("delivery_note"),
                "delivery_note_item": row.get("delivery_note_item"),
            }

        selected[sales_invoice_item]["qty"] += flt(row.get("qty"))
        selected[sales_invoice_item]["serials"].extend(row.get("serials") or [])

        if row.get("delivery_note"):
            selected[sales_invoice_item]["delivery_note"] = row.get("delivery_note")

        if row.get("delivery_note_item"):
            selected[sales_invoice_item]["delivery_note_item"] = row.get(
                "delivery_note_item"
            )

    if not selected:
        return None

    # ---------------------------------------------------------------------
    # GET ALL ORIGINAL SALES INVOICES
    # ---------------------------------------------------------------------

    source_si_names = list(
        dict.fromkeys(
            data.get("sales_invoice")
            for data in selected.values()
            if data.get("sales_invoice")
        )
    )

    if not source_si_names:
        frappe.throw(f"No Sales Invoice found for Bulk Sales Return {doc.name}.")

    # ---------------------------------------------------------------------
    # LOAD / VALIDATE SOURCE SALES INVOICES
    # ---------------------------------------------------------------------

    customers = set()
    companies = set()
    currencies = set()
    source_sis = {}

    for si_name in source_si_names:

        source_si_doc = frappe.get_doc("Sales Invoice", si_name)

        if source_si_doc.docstatus != 1:
            frappe.throw(f"Sales Invoice {si_name} must be submitted.")

        source_sis[si_name] = source_si_doc
        customers.add(source_si_doc.customer)
        companies.add(source_si_doc.company)
        currencies.add(source_si_doc.currency)

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

    # ---------------------------------------------------------------------
    # FIRST SOURCE SI AS BASE
    # ---------------------------------------------------------------------

    source_si = source_sis[source_si_names[0]]

    # ---------------------------------------------------------------------
    # CREATE RETURN DOCUMENT
    # ---------------------------------------------------------------------

    return_doc = make_return_doc("Sales Invoice", source_si.name)

    return_doc.is_return = 1
    return_doc.return_against = None

    return_doc.customer = source_si.customer
    return_doc.company = source_si.company
    return_doc.currency = source_si.currency
    return_doc.conversion_rate = source_si.conversion_rate

    # ---------------------------------------------------------------------
    # STOCK LOGIC
    # FIX: pehle yaha any(DN-backed) se poore return ka update_stock=0 ho
    # jata tha. Ab caller (process_bulk_sales_return) decide karta hai.
    # ---------------------------------------------------------------------

    if update_stock is not None:
        return_doc.update_stock = 1 if update_stock else 0
    else:
        source_update_stock = all(
            bool(source_sis[d.get("sales_invoice")].update_stock)
            for d in selected.values()
            if d.get("sales_invoice") in source_sis
        )
        return_doc.update_stock = 1 if source_update_stock else 0

    # ---------------------------------------------------------------------
    # REMOVE AUTO-MAPPED ITEMS
    # ---------------------------------------------------------------------

    return_doc.set("items", [])

    # ---------------------------------------------------------------------
    # ADD ONLY SELECTED ITEMS
    # ---------------------------------------------------------------------

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
                "price_list_rate",
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
                "dn_detail",
                "item_tax_template",
                "item_tax_rate",
            ],
            as_dict=True,
        )

        if not original_data:
            frappe.throw(f"Sales Invoice Item {sales_invoice_item} not found.")

        selected_source_si = selected_row.get("sales_invoice")

        if selected_source_si and selected_source_si != original_data.parent:
            frappe.throw(
                f"Sales Invoice Item {sales_invoice_item} "
                f"does not belong to Sales Invoice {selected_source_si}."
            )

        item = return_doc.append("items", {})

        item.item_code = original_data.item_code
        item.item_name = original_data.item_name
        item.description = (
            original_data.description
            or original_data.item_name
            or original_data.item_code
        )
        item.uom = original_data.uom
        item.stock_uom = original_data.stock_uom
        item.conversion_factor = original_data.conversion_factor or 1

        # Original transaction rate
        item.rate = flt(original_data.rate)

        if hasattr(item, "price_list_rate"):
            item.price_list_rate = flt(
                original_data.price_list_rate
                if original_data.price_list_rate is not None
                else original_data.rate
            )

        item.warehouse = original_data.warehouse

        # Return qty (negative)
        item.qty = -abs(flt(selected_row.get("qty")))

        if hasattr(item, "sales_invoice_item"):
            item.sales_invoice_item = sales_invoice_item

        if hasattr(item, "sales_order"):
            item.sales_order = original_data.sales_order

        if hasattr(item, "so_detail"):
            item.so_detail = original_data.so_detail

        # Remove DN link from return SI
        if hasattr(item, "delivery_note"):
            item.delivery_note = None

        if hasattr(item, "dn_detail"):
            item.dn_detail = None

        # Accounting
        if hasattr(item, "income_account"):
            item.income_account = original_data.income_account

        if hasattr(item, "cost_center"):
            item.cost_center = original_data.cost_center

        if hasattr(item, "brand"):
            item.brand = original_data.brand

        # ITEM TAX TEMPLATE / ITEM TAX RATE
        if hasattr(item, "item_tax_template"):
            item.item_tax_template = original_data.item_tax_template

        if hasattr(item, "item_tax_rate"):
            item.item_tax_rate = original_data.item_tax_rate

        # Serial numbers
        serials = list(dict.fromkeys(selected_row.get("serials") or []))

        if serials:
            item.serial_no = "\n".join(serials)

            if hasattr(item, "use_serial_batch_fields"):
                item.use_serial_batch_fields = 1 if return_doc.update_stock else 0

    # ---------------------------------------------------------------------
    # RE-INDEX
    # ---------------------------------------------------------------------

    for idx, item in enumerate(return_doc.items, start=1):
        item.idx = idx

    if not return_doc.items:
        frappe.throw(
            f"No valid Sales Invoice items found for Bulk Sales Return {doc.name}."
        )

    # ---------------------------------------------------------------------
    # COPY TAXES FROM SOURCE SALES INVOICE
    # ---------------------------------------------------------------------

    return_doc.taxes_and_charges = source_si.taxes_and_charges

    if hasattr(return_doc, "tax_category"):
        return_doc.tax_category = source_si.get("tax_category")

    # Ratio used only for "Actual" type charges (scaled to returned value)
    source_net_total = flt(source_si.net_total) or flt(source_si.total) or 0

    returned_value = 0
    for i in return_doc.items:
        parent_si = frappe.db.get_value(
            "Sales Invoice Item", i.get("sales_invoice_item"), "parent"
        )
        if parent_si == source_si.name:
            returned_value += abs(flt(i.qty)) * flt(i.rate)

    actual_ratio = (returned_value / source_net_total) if source_net_total else 0

    def build_tax_rows():

        # Fields which must NOT be copied from the source tax row
        skip_fields = {
            "name", "owner", "creation", "modified", "modified_by",
            "docstatus", "idx", "parent", "parentfield", "parenttype",
            "doctype",
            "tax_amount", "tax_amount_after_discount_amount",
            "base_tax_amount", "base_tax_amount_after_discount_amount",
            "total", "base_total",
            "item_wise_tax_detail",
        }

        tax_rows = []

        for tax in source_si.get("taxes") or []:

            tax_row = {
                key: value
                for key, value in tax.as_dict().items()
                if key not in skip_fields and not key.startswith("__")
            }

            tax_row["dont_recompute_tax"] = 0

            # "Actual" charges are fixed amounts -> scale to returned value.
            # All other charge types are recalculated by ERPNext.
            if tax.charge_type == "Actual":
                tax_row["tax_amount"] = -abs(flt(tax.tax_amount)) * actual_ratio

            tax_rows.append(tax_row)

        return tax_rows

    return_doc.set("taxes", [])

    for tax_row in build_tax_rows():
        return_doc.append("taxes", tax_row)

    # ---------------------------------------------------------------------
    # REMOVE PAYMENTS
    # ---------------------------------------------------------------------

    if hasattr(return_doc, "payments"):
        return_doc.set("payments", [])

    if hasattr(return_doc, "payment_schedule"):
        return_doc.set("payment_schedule", [])

    if hasattr(return_doc, "paid_amount"):
        return_doc.paid_amount = 0

    if hasattr(return_doc, "base_paid_amount"):
        return_doc.base_paid_amount = 0

    # ---------------------------------------------------------------------
    # FLAGS
    # ---------------------------------------------------------------------

    return_doc.flags.bulk_consolidated_return = True
    return_doc.flags.ignore_permissions = True

    set_bulk_reference(return_doc, doc.name)

    # ---------------------------------------------------------------------
    # STORE ORIGINAL RATES (key = source SI item name)
    # ---------------------------------------------------------------------

    source_rates = {}

    for item in return_doc.items:

        source_item = (
            item.get("sales_invoice_item")
            if hasattr(item, "sales_invoice_item")
            else None
        )

        if not source_item:
            continue

        source_data = frappe.db.get_value(
            "Sales Invoice Item",
            source_item,
            ["rate", "price_list_rate"],
            as_dict=True,
        )

        if not source_data:
            continue

        source_rates[source_item] = {
            "rate": flt(source_data.rate),
            "price_list_rate": (
                flt(source_data.price_list_rate)
                if source_data.price_list_rate is not None
                else None
            ),
        }

    # If taxes are included in print rate, do NOT force net_rate/net_amount
    taxes_inclusive = any(
        t.included_in_print_rate for t in (return_doc.get("taxes") or [])
    )

    # ---------------------------------------------------------------------
    # HELPER: RESTORE ORIGINAL SOURCE RATE
    # ---------------------------------------------------------------------

    def restore_original_rates():

        for item in return_doc.items:

            source_item = (
                item.get("sales_invoice_item")
                if hasattr(item, "sales_invoice_item")
                else None
            )

            if not source_item:
                continue

            original = source_rates.get(source_item)

            if not original:
                continue

            original_rate = flt(original["rate"])
            conversion_rate = flt(return_doc.conversion_rate or 1)

            item.rate = original_rate

            if hasattr(item, "price_list_rate"):
                source_plr = original["price_list_rate"]
                item.price_list_rate = (
                    source_plr if source_plr is not None else original_rate
                )

            if hasattr(item, "discount_percentage"):
                plr = flt(
                    getattr(item, "price_list_rate", original_rate)
                    or original_rate
                )

                if plr:
                    item.discount_percentage = ((plr - original_rate) / plr) * 100

            item.amount = flt(item.qty) * original_rate

            if hasattr(item, "base_rate"):
                item.base_rate = original_rate * conversion_rate

            if hasattr(item, "base_amount"):
                item.base_amount = flt(item.qty) * flt(item.base_rate or 0)

            # net fields (tax is calculated on net_amount)
            if not taxes_inclusive:

                if hasattr(item, "net_rate"):
                    item.net_rate = original_rate

                if hasattr(item, "net_amount"):
                    item.net_amount = flt(item.qty) * original_rate

                if hasattr(item, "base_net_rate"):
                    item.base_net_rate = original_rate * conversion_rate

                if hasattr(item, "base_net_amount"):
                    item.base_net_amount = flt(item.qty) * flt(
                        item.base_net_rate or 0
                    )

    # ---------------------------------------------------------------------
    # SET MISSING VALUES
    # ---------------------------------------------------------------------

    return_doc.set_missing_values()

    # set_missing_values may have wiped taxes -> re-apply if empty
    if not return_doc.get("taxes") and source_si.get("taxes"):

        return_doc.taxes_and_charges = source_si.taxes_and_charges

        for tax_row in build_tax_rows():
            return_doc.append("taxes", tax_row)

    # item tax template / rate may be reset by set_missing_values
    for item in return_doc.items:

        source_item = (
            item.get("sales_invoice_item")
            if hasattr(item, "sales_invoice_item")
            else None
        )

        if not source_item:
            continue

        src_tax = frappe.db.get_value(
            "Sales Invoice Item",
            source_item,
            ["item_tax_template", "item_tax_rate"],
            as_dict=True,
        )

        if not src_tax:
            continue

        if hasattr(item, "item_tax_template"):
            item.item_tax_template = src_tax.item_tax_template

        if hasattr(item, "item_tax_rate"):
            item.item_tax_rate = src_tax.item_tax_rate

    # ---------------------------------------------------------------------
    # ADDITIONAL DISCOUNT FIX
    # make_return_doc poore original invoice ka discount_amount copy kar deta
    # hai. Ham sirf kuch items return karte hain, isliye discount ko har source
    # SI ke returned items ke hisab se proportional karna zaroori hai.
    # ---------------------------------------------------------------------

    discount_share = 0

    for src_name, src in source_sis.items():

        src_discount = abs(flt(src.discount_amount))
        src_total = flt(src.total)

        if not src_discount or not src_total:
            continue

        returned_value_si = 0

        for i in return_doc.items:
            sii_name = i.get("sales_invoice_item")
            parent_si = frappe.db.get_value(
                "Sales Invoice Item", sii_name, "parent"
            )
            if parent_si != src_name:
                continue

            original_rate = flt((source_rates.get(sii_name) or {}).get("rate"))
            returned_value_si += abs(flt(i.qty)) * original_rate

        ratio = min(returned_value_si / src_total, 1) if src_total else 0
        discount_share += src_discount * ratio

    return_doc.additional_discount_percentage = 0
    return_doc.discount_amount = (
        -flt(discount_share, return_doc.precision("discount_amount"))
        if discount_share
        else 0
    )

    # ---------------------------------------------------------------------
    # FIX INVALID BILLING / SHIPPING ADDRESS LINKS
    # ---------------------------------------------------------------------

    def get_customer_address(address_field):
        address_name = return_doc.get(address_field)

        if not address_name:
            return None

        is_linked = frappe.db.exists(
            "Dynamic Link",
            {
                "parent": address_name,
                "parenttype": "Address",
                "parentfield": "links",
                "link_doctype": "Customer",
                "link_name": return_doc.customer,
            },
        )

        if is_linked:
            return address_name

        frappe.logger("bulk_sales_return").warning(
            f"Bulk Sales Return {doc.name}: address {address_name} in "
            f"{address_field} is not linked to customer {return_doc.customer}; "
            "looking for a valid customer address."
        )

        candidates = frappe.get_all(
            "Dynamic Link",
            filters={
                "parenttype": "Address",
                "parentfield": "links",
                "link_doctype": "Customer",
                "link_name": return_doc.customer,
            },
            fields=["parent"],
            order_by="parent asc",
            limit_page_length=1,
        )

        return candidates[0].parent if candidates else None

    for address_field, display_field in (
        ("customer_address", "address_display"),
        ("shipping_address_name", "shipping_address"),
    ):
        valid_address = get_customer_address(address_field)

        if return_doc.get(address_field) != valid_address:
            return_doc.set(address_field, valid_address)

            if display_field in return_doc.as_dict():
                return_doc.set(display_field, None)

    # ---------------------------------------------------------------------
    # RESTORE RATE -> CALCULATE TAXES -> RESTORE -> CALCULATE -> RESTORE
    # ---------------------------------------------------------------------

    restore_original_rates()
    return_doc.calculate_taxes_and_totals()

    restore_original_rates()
    return_doc.calculate_taxes_and_totals()

    restore_original_rates()

    return_doc.return_against = None

    # ---------------------------------------------------------------------
    # DEBUG LOG
    # ---------------------------------------------------------------------

    frappe.logger().info(
        f"Bulk Sales Return {doc.name}: update_stock={return_doc.update_stock}, "
        f"taxes_and_charges={return_doc.taxes_and_charges}, "
        f"taxes_rows={len(return_doc.get('taxes') or [])}, "
        f"total_taxes_and_charges={return_doc.total_taxes_and_charges}, "
        f"item_tax_templates={[i.get('item_tax_template') for i in return_doc.items]}"
    )

    for item in return_doc.items:

        source_item = (
            item.get("sales_invoice_item")
            if hasattr(item, "sales_invoice_item")
            else None
        )

        if not source_item:
            continue

        original = source_rates.get(source_item)

        if not original:
            continue

        frappe.logger().info(
            f"Bulk Sales Return {doc.name}: SI Item {source_item} | "
            f"Original Rate={original['rate']} | Return Rate={item.rate} | "
            f"Qty={item.qty} | Amount={item.amount}"
        )

    # ---------------------------------------------------------------------
    # INSERT AS DRAFT
    # ---------------------------------------------------------------------

    return_doc.insert(ignore_permissions=True)

    # ---------------------------------------------------------------------
    # VERIFY DATABASE RATE AFTER INSERT
    # ---------------------------------------------------------------------

    rate_corrected = False

    for return_item in return_doc.items:

        source_item = (
            return_item.get("sales_invoice_item")
            if hasattr(return_item, "sales_invoice_item")
            else None
        )

        if not source_item:
            continue

        original = source_rates.get(source_item)

        if not original:
            continue

        original_rate = flt(original["rate"])

        db_rate = frappe.db.get_value(
            "Sales Invoice Item", return_item.name, "rate"
        )

        if flt(db_rate) != original_rate:

            rate_corrected = True

            conversion_rate = flt(return_doc.conversion_rate or 1)
            base_rate = original_rate * conversion_rate
            qty = flt(return_item.qty)

            frappe.db.set_value(
                "Sales Invoice Item",
                return_item.name,
                {
                    "rate": original_rate,
                    "amount": qty * original_rate,
                    "net_rate": original_rate,
                    "net_amount": qty * original_rate,
                    "base_rate": base_rate,
                    "base_amount": qty * base_rate,
                    "base_net_rate": base_rate,
                    "base_net_amount": qty * base_rate,
                },
                update_modified=False,
            )

            frappe.logger().warning(
                f"Bulk Sales Return {doc.name}: Sales Invoice Return "
                f"{return_doc.name}, Item {return_item.name}: DB rate was "
                f"{db_rate}, forced back to original rate {original_rate} "
                f"from source SI Item {source_item}."
            )

    # If a rate was forced directly in DB, recalculate parent totals / taxes
    if rate_corrected:

        return_doc.reload()
        return_doc.flags.ignore_permissions = True
        return_doc.calculate_taxes_and_totals()
        return_doc.db_update()

        for child in return_doc.get_all_children():
            child.db_update()

    frappe.db.set_value(
        "Sales Invoice",
        return_doc.name,
        "return_against",
        None,
        update_modified=False,
    )

    persist_bulk_reference(return_doc, doc.name)

    return_doc.reload()

    return_doc.flags.bulk_consolidated_return = True
    return_doc.flags.ignore_permissions = True

    frappe.db.commit()

    frappe.logger().info(
        f"Bulk Sales Return {doc.name}: FINAL | SI Return={return_doc.name} | "
        f"update_stock={return_doc.update_stock} | "
        f"net_total={return_doc.net_total} | "
        f"total_taxes_and_charges={return_doc.total_taxes_and_charges} | "
        f"grand_total={return_doc.grand_total}"
    )

    return return_doc.name


# =============================================================================
# DELIVERY NOTE RETURNS (ONE consolidated return)
# FIX: agar selected DN item ka returnable qty nahi bacha to pehle wo chupchap
# skip ho jata tha, ab clear error aata hai.
# =============================================================================

def create_delivery_note_returns(doc, rows, extra_si_rows=None):
    """ONE consolidated Delivery Note Return for all source Delivery Notes."""

    existing = frappe.db.get_value(
        "Delivery Note",
        {
            "custom_bulk_sales_return": doc.name,
            "is_return": 1,
            "docstatus": ["in", [0, 1]],
        },
        "name",
    )
    if existing:
        return [existing]

    grouped = {}
    for row in rows:
        dn = row.get("delivery_note")
        dn_item = row.get("delivery_note_item")
        if not dn or not dn_item:
            continue
        sel = grouped.setdefault(dn, {}).setdefault(
            dn_item, {"qty": 0, "serials": []}
        )
        sel["qty"] += flt(row.get("qty"))
        sel["serials"].extend(row.get("serials") or [])

    if not grouped:
        return []

    customers, companies = set(), set()
    for dn in grouped:
        s = frappe.db.get_value(
            "Delivery Note", dn, ["docstatus", "customer", "company"], as_dict=True
        )
        if s.docstatus != 1:
            frappe.throw(f"Delivery Note {dn} must be submitted.")
        customers.add(s.customer)
        companies.add(s.company)
    if len(customers) > 1 or len(companies) > 1:
        frappe.throw("All Delivery Notes must have the same Customer and Company.")

    skip_keys = {
        "name", "parent", "parentfield", "parenttype", "idx", "creation",
        "modified", "owner", "modified_by", "docstatus", "doctype",
        "serial_and_batch_bundle", "rejected_serial_and_batch_bundle",
    }

    return_doc = None

    for source_name, selected in grouped.items():
        mapped = make_return_doc("Delivery Note", source_name)
        added = set()

        for return_item in list(mapped.items):
            original_item_name = getattr(return_item, "dn_detail", None)
            data = selected.get(original_item_name)
            if not data:
                continue

            original_qty = flt(
                frappe.db.get_value("Delivery Note Item", original_item_name, "qty")
            )
            already_returned = flt(
                frappe.db.sql(
                    """
                    SELECT IFNULL(SUM(ABS(dni.qty)), 0)
                    FROM `tabDelivery Note Item` dni
                    INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
                    WHERE dn.docstatus = 1 AND dn.is_return = 1
                    AND dni.dn_detail = %s
                    """,
                    original_item_name,
                )[0][0]
            )
            if flt(data["qty"]) > original_qty - already_returned:
                frappe.throw(
                    f"Delivery Note Item {original_item_name}: only "
                    f"{original_qty - already_returned} qty available for return."
                )

            return_item.qty = -abs(flt(data["qty"]))
            serials = list(dict.fromkeys(data["serials"]))
            if serials:
                return_item.serial_no = "\n".join(serials)
                if hasattr(return_item, "use_serial_batch_fields"):
                    return_item.use_serial_batch_fields = 1

            if return_doc is None:
                return_doc = mapped
                return_doc.set("items", [])

            item_dict = return_item.as_dict()
            for k in list(item_dict.keys()):
                if k in skip_keys or k.startswith("__"):
                    item_dict.pop(k)
            return_doc.append("items", item_dict)
            added.add(original_item_name)

        # make_return_doc fully-returned items ko mapped doc me nahi deta.
        # Aise item ko chupchap skip karne ki jagah error do.
        missing = set(selected) - added
        if missing:
            frappe.throw(
                f"Delivery Note {source_name}: no returnable qty left for item(s) "
                f"{', '.join(sorted(missing))}. Already returned?"
            )

    if not return_doc or not return_doc.items:
        return []

    # -----------------------------------------------------------------
    # SI-ONLY ITEMS (koi DN nahi, stock Sales Invoice se gaya tha)
    # Inka stock isi consolidated DN return se wapas aata hai, taaki
    # ek hi SI return (update_stock=0) aur ek hi DN return bane.
    # -----------------------------------------------------------------
    if extra_si_rows:

        merged_si = {}

        for r in extra_si_rows:
            sii_name = r.get("sales_invoice_item")
            if not sii_name:
                continue
            m = merged_si.setdefault(sii_name, {"qty": 0, "serials": []})
            m["qty"] += flt(r.get("qty"))
            m["serials"].extend(r.get("serials") or [])

        for sii_name, data in merged_si.items():

            src = frappe.db.get_value(
                "Sales Invoice Item",
                sii_name,
                [
                    "parent", "item_code", "item_name", "description", "uom",
                    "stock_uom", "conversion_factor", "rate", "warehouse",
                    "cost_center",
                ],
                as_dict=True,
            )

            if not src:
                frappe.throw(f"Sales Invoice Item {sii_name} not found.")

            si_head = frappe.db.get_value(
                "Sales Invoice",
                src.parent,
                ["docstatus", "customer", "company"],
                as_dict=True,
            )

            if si_head.docstatus != 1:
                frappe.throw(f"Sales Invoice {src.parent} must be submitted.")

            if (
                si_head.customer not in customers
                or si_head.company not in companies
            ):
                frappe.throw(
                    "All Sales Invoices and Delivery Notes must have the "
                    "same Customer and Company."
                )

            new_item = return_doc.append(
                "items",
                {
                    "item_code": src.item_code,
                    "item_name": src.item_name,
                    "description": src.description or src.item_name,
                    "uom": src.uom,
                    "stock_uom": src.stock_uom,
                    "conversion_factor": src.conversion_factor or 1,
                    "qty": -abs(flt(data["qty"])),
                    "rate": flt(src.rate),
                    "warehouse": src.warehouse,
                    "cost_center": src.cost_center,
                },
            )

            serials = list(dict.fromkeys(data["serials"]))

            if serials:
                new_item.serial_no = "\n".join(serials)

                if hasattr(new_item, "use_serial_batch_fields"):
                    new_item.use_serial_batch_fields = 1

    for idx, item in enumerate(return_doc.items, start=1):
        item.idx = idx

    return_doc.is_return = 1
    return_doc.return_against = None
    return_doc.custom_bulk_sales_return = doc.name
    return_doc.flags.ignore_permissions = True

    return_doc.set_missing_values()
    return_doc.calculate_taxes_and_totals()
    return_doc.return_against = None
    return_doc.insert(ignore_permissions=True)

    frappe.db.set_value(
        "Delivery Note", return_doc.name,
        {"return_against": None, "custom_bulk_sales_return": doc.name},
        update_modified=False,
    )
    frappe.db.commit()
    return [return_doc.name]


# =============================================================================
# FORCE DELIVERY NOTE BULK REFERENCE
# =============================================================================

def force_set_delivery_note_bulk_reference(delivery_note, bulk_sales_return):

    frappe.db.sql(
        """
        UPDATE `tabDelivery Note`
        SET custom_bulk_sales_return = %s
        WHERE name = %s
        """,
        (bulk_sales_return, delivery_note)
    )

    frappe.db.commit()


# =============================================================================
# VERIFY DELIVERY NOTE BULK REFERENCE
# =============================================================================

def verify_delivery_note_bulk_reference(delivery_note, bulk_sales_return):

    actual_value = frappe.db.get_value(
        "Delivery Note", delivery_note, "custom_bulk_sales_return"
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

def reconcile_delivery_note_bulk_reference(doc):

    source_dn_names = set()

    for row in doc.items:

        if row.delivery_note:
            source_dn_names.add(row.delivery_note)

        if row.delivery_note_item:

            source_dn = frappe.db.get_value(
                "Delivery Note Item", row.delivery_note_item, "parent"
            )

            if source_dn:
                source_dn_names.add(source_dn)

    if not source_dn_names:
        return

    for source_dn in source_dn_names:

        return_dns = frappe.db.sql(
            """
            SELECT name
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

            existing_bulk = frappe.db.get_value(
                "Delivery Note", return_dn, "custom_bulk_sales_return"
            )

            if existing_bulk and existing_bulk != doc.name:
                continue

            force_set_delivery_note_bulk_reference(return_dn, doc.name)
            verify_delivery_note_bulk_reference(return_dn, doc.name)

    frappe.db.commit()


# =============================================================================
# BULK REFERENCE
# =============================================================================

def set_bulk_reference(return_doc, bulk_name):

    meta = frappe.get_meta(return_doc.doctype)

    if meta.has_field("custom_bulk_sales_return"):
        return_doc.set("custom_bulk_sales_return", bulk_name)
        return

    if meta.has_field("bulk_sales_return"):
        return_doc.set("bulk_sales_return", bulk_name)


def persist_bulk_reference(return_doc, bulk_name):

    meta = frappe.get_meta(return_doc.doctype)

    if meta.has_field("custom_bulk_sales_return"):

        frappe.db.set_value(
            return_doc.doctype,
            return_doc.name,
            "custom_bulk_sales_return",
            bulk_name,
            update_modified=False
        )

        frappe.db.commit()

        return

    if meta.has_field("bulk_sales_return"):

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

    doc = frappe.get_doc("Bulk Sales Return", docname)

    doc.db_set("submit_status", "Queued")

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


# =============================================================================
# PROCESS SUBMIT RETURNS
# FIX: purana code DN return ko seedha dn_doc.submit() se submit karta tha
# (consolidated DN return me return_against blank hota hai, isliye fail).
# Ab SI returns submit hote hain, fir DN returns auto-submit wale path se.
# =============================================================================

def process_submit_returns(docname):

    doc = frappe.get_doc("Bulk Sales Return", docname)

    try:

        doc.db_set("submit_status", "In Progress")

        frappe.db.commit()

        # SALES INVOICE RETURNS (update_stock=1 wale se SLE banega)
        sis = frappe.get_all(
            "Sales Invoice",
            filters={
                "custom_bulk_sales_return": docname,
                "docstatus": 0,
                "is_return": 1
            },
            pluck="name",
            order_by="creation asc"
        )

        for si in sis:

            si_doc = frappe.get_doc("Sales Invoice", si)

            if si_doc.docstatus != 0:
                continue

            si_doc.flags.ignore_permissions = True

            si_doc.submit()

            frappe.db.commit()

        # No Delivery Note Return submission.
        # Only the consolidated Sales Invoice Return is submitted.
        doc.db_set("submit_status", "Completed")

        frappe.db.commit()

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Submit Sales Returns Failed"
        )

        try:

            doc.db_set("submit_status", "Failed")

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
            "docstatus": 0,
            "is_return": 1
        }
    )

    return bool(exists)


@frappe.whitelist()
def has_draft_return_sis(docname):

    exists = frappe.db.exists(
        "Sales Invoice",
        {
            "custom_bulk_sales_return": docname,
            "docstatus": 0,
            "is_return": 1
        }
    )

    return bool(exists)


# =============================================================================
# DELIVERY NOTE RETURNABLE ITEMS
# =============================================================================

@frappe.whitelist()
def get_returnable_items(customer, company, item_code=None):

    items = []

    # ============================================================
    # 1. DELIVERY NOTE ITEMS (DN has FIRST PRIORITY)
    # ============================================================

    dn_conditions = """
        AND dn.customer = %(customer)s
        AND dn.company = %(company)s
    """

    if item_code:
        dn_conditions += """
            AND dni.item_code = %(item_code)s
        """

    delivery_note_items = frappe.db.sql(
        f"""
        SELECT
            dni.parent AS delivery_note,
            dni.name AS delivery_note_item,

            dni.item_code,
            dni.item_name,

            dni.qty AS delivered_qty,
            dni.rate AS rate,

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

        {dn_conditions}

        ORDER BY
            dn.posting_date DESC,
            dn.posting_time DESC
        """,
        {
            "customer": customer,
            "company": company,
            "item_code": item_code
        },
        as_dict=1
    )

    dn_item_codes = set()

    for row in delivery_note_items:

        row["source_type"] = "Delivery Note"

        dn_item_codes.add(row.item_code)

        items.append(row)

    # ============================================================
    # 2. SALES INVOICE ITEMS (only if NO returnable DN for item)
    # ============================================================

    si_conditions = """
        AND si.customer = %(customer)s
        AND si.company = %(company)s
    """

    if item_code:
        si_conditions += """
            AND sii.item_code = %(item_code)s
        """

    sales_invoice_items = frappe.db.sql(
        f"""
        SELECT
            sii.parent AS sales_invoice,
            sii.name AS sales_invoice_item,

            sii.item_code,
            sii.item_name,

            sii.qty AS delivered_qty,
            sii.rate AS rate,

            0 AS returned_qty,

            sii.qty AS returnable_qty,

            0 AS return_qty,

            i.has_serial_no

        FROM `tabSales Invoice Item` sii

        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent

        LEFT JOIN `tabItem` i
            ON i.name = sii.item_code

        WHERE si.docstatus = 1
        AND si.is_return = 0
        AND sii.qty > 0

        {si_conditions}

        ORDER BY
            si.posting_date DESC,
            si.posting_time DESC
        """,
        {
            "customer": customer,
            "company": company,
            "item_code": item_code
        },
        as_dict=1
    )

    for row in sales_invoice_items:

        # DN HAS PRIORITY
        if row.item_code in dn_item_codes:
            continue

        row["source_type"] = "Sales Invoice"

        items.append(row)

    return items


# =============================================================================
# DELIVERY NOTE ITEM DETAILS
# =============================================================================

@frappe.whitelist()
def get_dn_item_details(items):

    items = frappe.parse_json(items)

    result = []

    for d in items:

        dn_item = frappe.get_doc("Delivery Note Item", d.get("delivery_note_item"))

        item_doc = frappe.get_doc("Item", dn_item.item_code)

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

        available_serials = list(set(dn_serials) - set(returned_list))

        scanned_serials = []

        if d.get("serial_nos"):
            scanned_serials = [
                s.strip()
                for s in d.get("serial_nos").split("\n")
                if s.strip()
            ]

        invalid_serials = list(set(scanned_serials) - set(available_serials))

        if invalid_serials:
            frappe.throw(
                f"Invalid Serial(s) for Item "
                f"{dn_item.item_code}: "
                f"{', '.join(invalid_serials)}"
            )

        warehouse_map = {}

        if is_serialized:

            for serial in scanned_serials:

                serial_doc = frappe.get_doc("Serial No", serial)

                wh = serial_doc.warehouse or dn_item.warehouse

                warehouse_map.setdefault(wh, []).append(serial)

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
                    "returnable_quantity": d.get("returnable_qty"),
                    "serial_nos": "\n".join(serial_list),
                    "available_serial_nos": "\n".join(available_serials)
                })

        else:

            qty = flt(d.get("return_qty"))

            wh = dn_item.warehouse

            warehouse_map.setdefault(wh, 0)

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
                    "returnable_quantity": d.get("returnable_qty"),
                    "serial_nos": "",
                    "available_serial_nos": ""
                })

    return result


# =============================================================================
# DELIVERY NOTE SERIAL SEARCH
# =============================================================================

@frappe.whitelist()
def get_dn_from_serial(serial_no, company):

    serial_no = (serial_no or "").strip()

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
        (company, f"%{serial_no}%"),
        as_dict=True
    )

    if not dn_items:
        return None

    for dn_item in dn_items:

        actual_serials = [
            s.strip()
            for s in (dn_item.serial_no or "").split("\n")
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

        serial = frappe.get_doc("Serial No", serial_no)

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
def get_si_from_serial(serial_no, company, sales_invoice=None, customer=None):

    serial_no = (serial_no or "").strip()

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

    if not frappe.db.exists("Serial No", serial_no):
        return None

    serial = frappe.get_doc("Serial No", serial_no)

    for si_item in si_items:

        actual_serials = [
            s.strip()
            for s in (si_item.serial_no or "").split("\n")
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
            SELECT IFNULL(SUM(ABS(sii2.qty)), 0) AS returned_qty
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
            flt(returned_qty[0].returned_qty) if returned_qty else 0
        )

        returnable_qty = flt(si_item.billed_qty) - returned_qty_val

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
def get_sales_invoice_items(sales_invoice):

    doc = frappe.get_doc("Sales Invoice", sales_invoice)

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
                ELSE IFNULL(sii.delivered_qty, 0)
            END AS delivered_qty,

            IFNULL(ret.returned_qty, 0) AS returned_qty,

            (
                CASE
                    WHEN si.update_stock = 1
                        THEN sii.qty
                    ELSE IFNULL(sii.delivered_qty, 0)
                END
                - IFNULL(ret.returned_qty, 0)
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

        LEFT JOIN (
            SELECT
                sii_return.sales_invoice_item,
                SUM(ABS(sii_return.qty)) AS returned_qty

            FROM `tabSales Invoice Item` sii_return

            INNER JOIN `tabSales Invoice` si_return
                ON si_return.name = sii_return.parent

            WHERE si_return.docstatus = 1
              AND si_return.is_return = 1
              AND sii_return.sales_invoice_item IS NOT NULL

            GROUP BY sii_return.sales_invoice_item
        ) ret
            ON ret.sales_invoice_item = sii.name

        WHERE si.docstatus = 1
          AND si.is_return = 0

        {conditions}

        AND (
            si.update_stock = 1

            OR IFNULL(sii.delivered_qty, 0) > 0

            OR (
                sii.dn_detail IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM `tabDelivery Note Item` dni

                    INNER JOIN `tabDelivery Note` dn
                        ON dn.name = dni.parent

                    WHERE dni.name = sii.dn_detail
                      AND dn.docstatus = 1
                      AND dn.is_return = 0
                )
            )
        )

        HAVING returnable_qty > 0

        ORDER BY
            si.posting_date DESC,
            si.name DESC
        """,
        {
            "customer": customer,
            "company": company,
            "sales_invoice": sales_invoice,
            "item_code": item_code
        },
        as_dict=1
    )

    return items


# =============================================================================
# COMMON SI / DN SERIAL SOURCE
# =============================================================================

@frappe.whitelist()
def get_return_source_from_serial(serial_no, company, customer=None):

    serial_no = (serial_no or "").strip()

    if not serial_no:
        return None

    if not frappe.db.exists("Serial No", serial_no):
        return None

    serial_doc = frappe.get_doc("Serial No", serial_no)

    # =========================================================================
    # CURRENT STOCK COMPANY VALIDATION
    # Reject an Active serial if its current warehouse belongs to another
    # company. Warehouse company is authoritative; Serial No company is fallback.
    # =========================================================================

    if serial_doc.status == "Active":

        warehouse_company = None

        if serial_doc.warehouse:
            warehouse_company = frappe.db.get_value(
                "Warehouse",
                serial_doc.warehouse,
                "company"
            )

        current_company = warehouse_company or serial_doc.company

        if current_company and current_company != company:

            frappe.throw(
                _("Serial No {0} is currently available in warehouse {1} under company {2}. It cannot be returned against company {3}.").format(
                    serial_no,
                    serial_doc.warehouse or _("Not Set"),
                    current_company,
                    company
                )
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
            for s in (si_item.serial_no or "").split("\n")
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
                ["parent", "name"],
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
            for s in (dn_item.serial_no or "").split("\n")
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

        # Find related Sales Invoice
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

        si_item = si_items[0] if si_items else None

        return {
            "source_type": "Delivery Note",

            "sales_invoice": si_item.parent if si_item else None,
            "sales_invoice_item": si_item.name if si_item else None,

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


# =============================================================================
# SUBMIT CONSOLIDATED DN RETURN
# =============================================================================

def submit_bulk_dn_return(dn_doc):
    """
    Consolidated DN return (return_against blank) ko submit karta hai.
    ERPNext submit par return_against wale DN ka per_returned update karta hai,
    blank hone par wo fail hota hai, isliye wo step skip karke baad me
    source DNs ka per_returned/status khud update kiya jata hai.
    """
    dn_doc.flags.ignore_permissions = True

    source_dns = set()

    if not dn_doc.return_against:

        new_updater = []
        for entry in dn_doc.status_updater:
            if entry.get("percent_join_field_parent") == "return_against":
                entry = dict(entry)
                entry.pop("percent_join_field_parent", None)
            new_updater.append(entry)
        dn_doc.status_updater = new_updater

        for it in dn_doc.items:
            if it.get("dn_detail"):
                parent = frappe.db.get_value(
                    "Delivery Note Item", it.dn_detail, "parent"
                )
                if parent:
                    source_dns.add(parent)

    dn_doc.submit()

    for src in source_dns:
        tot = frappe.db.sql(
            """
            SELECT IFNULL(SUM(stock_qty), 0), IFNULL(SUM(returned_qty), 0)
            FROM `tabDelivery Note Item`
            WHERE parent = %s
            """,
            src,
        )[0]

        per = (
            min(abs(flt(tot[1])) / flt(tot[0]) * 100, 100)
            if flt(tot[0])
            else 0
        )

        frappe.db.set_value(
            "Delivery Note", src, "per_returned", per, update_modified=False
        )
        frappe.get_doc("Delivery Note", src).set_status(update=True)


# =============================================================================
# AUTO SUBMIT LINKED DELIVERY NOTE RETURNS
# =============================================================================

def auto_submit_linked_delivery_note_return(doc, method=None):
    # Bulk Sales Return no longer creates or auto-submits Delivery Note Returns.
    return


# FIX: serial activation hack (db me seedha status Active) hata diya.
# SI-only items ka SI return ab update_stock=1 hota hai, isliye ERPNext
# khud Stock Ledger Entry banake serial Active karta hai.
# Ab ye function failed list return karta hai.
def submit_linked_delivery_note_returns(bulk_sales_return):
    if not bulk_sales_return:
        return []

    lock_name = f"bsr_submit_dn:{bulk_sales_return}"
    got_lock = frappe.db.sql("SELECT GET_LOCK(%s, 30)", lock_name)[0][0] == 1

    if not got_lock:
        frappe.throw(f"Could not acquire lock for {bulk_sales_return}")

    failed = []

    try:
        dns = frappe.get_all(
            "Delivery Note",
            filters={
                "custom_bulk_sales_return": bulk_sales_return,
                "is_return": 1,
                "docstatus": 0,
            },
            pluck="name",
            order_by="creation asc",
        )

        for dn_name in dns:
            try:
                dn_doc = frappe.get_doc("Delivery Note", dn_name)

                if dn_doc.docstatus != 0:
                    continue
                auto_purchase_return_for_dn_serials(dn_doc)
                submit_bulk_dn_return(dn_doc)
                frappe.db.commit()

            except Exception as e:
                frappe.db.rollback()
                reason = strip_html(str(e) or e.__class__.__name__).strip()[:300]
                failed.append(f"{dn_name} -> {reason}")
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Bulk Sales Return - DN Return submit failed: {dn_name}",
                )

        # DN returns submit ho gaye -> check karo ki saare serial Active hain
        if not failed:
            inactive = get_inactive_bulk_serials(bulk_sales_return)

            if inactive:
                failed.append(
                    "These serial numbers are not Active after the returns: "
                    + ", ".join(inactive)
                )

        if failed:
            frappe.publish_realtime(
                event="msgprint",
                message=(
                    f"Bulk Sales Return {bulk_sales_return}: Delivery Note "
                    f"return submit failed:<br>" + "<br>".join(failed)
                ),
            )

        return failed

    finally:
        frappe.db.sql("SELECT RELEASE_LOCK(%s)", lock_name)


def get_inactive_bulk_serials(bulk_sales_return):
    """Bulk Return ke jo serial abhi Active nahi hain unki list (check only)."""

    bulk_doc = frappe.get_doc("Bulk Sales Return", bulk_sales_return)

    inactive = []

    for row in bulk_doc.items:
        for serial in (row.serial_nos or "").split("\n"):
            serial = serial.strip()

            if not serial:
                continue

            status = frappe.db.get_value("Serial No", serial, "status")

            if status != "Active":
                inactive.append(f"{serial} ({status or 'not found'})")

    return inactive


def auto_purchase_return_for_dn_serials(dn_doc):
    """
    DN return ke serials agar customer company (BDBA) ke warehouse me pade hain,
    to unki Purchase Receipt ka Purchase Return bana ke submit karta hai,
    taaki TZUPL me DN return submit ho sake.
    """
    # serial -> (PR, PR item) latest inward bundle se
    groups = {}  # (pr_name, pr_item) -> [serials]

    for it in dn_doc.items:
        for s in (it.serial_no or "").split("\n"):
            s = s.strip()
            if not s:
                continue

            wh = frappe.db.get_value("Serial No", s, "warehouse")
            if not wh:
                continue
            if frappe.db.get_value("Warehouse", wh, "company") == dn_doc.company:
                continue  # already apni company me, kuch nahi karna

            row = frappe.db.sql(
                """
                SELECT sbb.voucher_no, sbb.voucher_detail_no
                FROM `tabSerial and Batch Entry` sbe
                JOIN `tabSerial and Batch Bundle` sbb ON sbb.name = sbe.parent
                WHERE sbe.serial_no = %s AND sbb.docstatus = 1
                AND sbb.is_cancelled = 0 AND sbb.voucher_type = 'Purchase Receipt'
                AND sbb.type_of_transaction = 'Inward' AND sbb.warehouse = %s
                ORDER BY sbb.posting_date DESC, sbb.posting_time DESC, sbb.creation DESC
                LIMIT 1
                """,
                (s, wh),
                as_dict=True,
            )
            if not row:
                frappe.throw(
                    f"Serial {s} {wh} me hai par uski Purchase Receipt nahi mili. "
                    f"Manual reverse karein."
                )
            groups.setdefault(
                (row[0].voucher_no, row[0].voucher_detail_no), []
            ).append(s)

    if not groups:
        return []

    by_pr = {}
    for (pr, pr_item), serials in groups.items():
        by_pr.setdefault(pr, {})[pr_item] = serials

    created = []
    for pr_name, items_map in by_pr.items():
        ret = make_return_doc("Purchase Receipt", pr_name)
        kept = []
        for item in list(ret.items):
            serials = items_map.get(item.get("purchase_receipt_item"))
            if not serials:
                continue
            item.qty = -len(serials)
            item.received_qty = -len(serials)
            item.serial_and_batch_bundle = None
            item.serial_no = "\n".join(serials)
            if hasattr(item, "use_serial_batch_fields"):
                item.use_serial_batch_fields = 1
            kept.append(item)

        if not kept:
            continue

        ret.items = kept
        for idx, i in enumerate(ret.items, start=1):
            i.idx = idx
        ret.flags.ignore_permissions = True
        ret.set_missing_values()
        ret.insert(ignore_permissions=True)
        ret.submit()
        created.append(ret.name)

    frappe.db.commit()
    return created
