
import re

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.stock_ledger import make_sl_entries


@frappe.whitelist()
def recover_return_stock(sales_invoice):
    """
    Recover missing stock for an already submitted Return Sales Invoice.

    Supports:
      - Submitted Return Sales Invoices
      - Update Stock checked or unchecked
      - Serial-tracked, non-batch stock items

    Does not:
      - Cancel or resubmit the invoice
      - Change the Update Stock checkbox
      - Change Serial No company directly
      - Call GL posting methods

    Existing inward stock entries are skipped to prevent duplicates.
    """

    frappe.has_permission("Sales Invoice", "write", throw=True)

    # Lock invoice against simultaneous recovery requests.
    frappe.db.sql(
        """
        SELECT name
        FROM `tabSales Invoice`
        WHERE name = %s
        FOR UPDATE
        """,
        sales_invoice,
    )

    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    doc.check_permission("write")

    if doc.docstatus != 1:
        frappe.throw(_("Sales Invoice must be submitted."))

    if not doc.is_return:
        frappe.throw(_("Only Return Sales Invoice is allowed."))

    recovered = []
    skipped = []
    errors = []

    plans = []
    seen_serials = set()

    # ---------------------------------------------------------
    # Existing inward stock entries for this return invoice.
    # ---------------------------------------------------------

    existing_recovered = frappe.db.sql(
        """
        SELECT DISTINCT sbe.serial_no
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabSerial and Batch Bundle` sbb
            ON sbb.name = sle.serial_and_batch_bundle
        INNER JOIN `tabSerial and Batch Entry` sbe
            ON sbe.parent = sbb.name
        WHERE sle.voucher_type = 'Sales Invoice'
            AND sle.voucher_no = %s
            AND sle.actual_qty > 0
            AND sle.is_cancelled = 0
            AND sbb.docstatus = 1
            AND sbb.is_cancelled = 0
            AND sbb.type_of_transaction = 'Inward'
            AND sbe.docstatus = 1
            AND sbe.is_outward = 0
            AND sbe.serial_no IS NOT NULL
        """,
        doc.name,
        pluck=True,
    )

    existing_recovered = set(existing_recovered)

    # ---------------------------------------------------------
    # PHASE 1: Validate all rows before creating stock entries.
    # ---------------------------------------------------------

    for row in doc.items:

        item = frappe.get_cached_value(
            "Item",
            row.item_code,
            [
                "has_serial_no",
                "has_batch_no",
                "is_stock_item",
            ],
            as_dict=True,
        )

        if not item:
            errors.append(
                f"{row.item_code}: Item does not exist."
            )
            continue

        if not item.is_stock_item:
            continue

        if not item.has_serial_no:
            continue

        if item.has_batch_no:
            errors.append(
                f"{row.item_code}: Serial + Batch item is not supported."
            )
            continue

        if flt(row.qty) >= 0:
            continue

        warehouse = row.warehouse

        if not warehouse:
            errors.append(
                f"{row.item_code}: Warehouse is missing."
            )
            continue

        warehouse_company = frappe.db.get_value(
            "Warehouse",
            warehouse,
            "company",
        )

        if not warehouse_company:
            errors.append(
                f"{row.item_code}: Warehouse does not exist."
            )
            continue

        if warehouse_company != doc.company:
            errors.append(
                f"{row.item_code}: Warehouse company does not match "
                "the invoice company."
            )
            continue

        if not row.serial_no:
            errors.append(
                f"{row.item_code}: Serial Number is missing."
            )
            continue

        serials = [
            sn.strip()
            for sn in re.split(r"[,;\n]+", row.serial_no)
            if sn.strip()
        ]

        abs_qty = abs(flt(row.qty))

        if abs(abs_qty - round(abs_qty)) > 0.000001:
            errors.append(
                f"{row.item_code}: Serial quantity must be a whole number."
            )
            continue

        expected_count = int(round(abs_qty))

        if len(serials) != expected_count:
            errors.append(
                f"{row.item_code}: Serial count ({len(serials)}) "
                f"does not match return quantity ({expected_count})."
            )
            continue

        if len(serials) != len(set(serials)):
            errors.append(
                f"{row.item_code}: Duplicate serial numbers in row."
            )
            continue

        pending_serials = []

        for serial in serials:

            if serial in seen_serials:
                errors.append(
                    f"{serial}: Duplicate serial across invoice rows."
                )
                continue

            seen_serials.add(serial)

            if serial in existing_recovered:
                skipped.append(
                    f"{serial}: Stock already recovered in this invoice."
                )
                continue

            sn = frappe.db.get_value(
                "Serial No",
                serial,
                [
                    "item_code",
                    "warehouse",
                    "status",
                ],
                as_dict=True,
            )

            if not sn:
                errors.append(
                    f"{serial}: Serial Number does not exist."
                )
                continue

            if sn.item_code != row.item_code:
                errors.append(
                    f"{serial}: Item mismatch. Expected "
                    f"{row.item_code}, found {sn.item_code}."
                )
                continue

            # Do not use Serial No.company for ownership validation.
            # Validate the destination warehouse instead.
            if sn.status == "Active" and sn.warehouse == warehouse:
                skipped.append(
                    f"{serial}: Already Active in correct warehouse."
                )
                continue

            if sn.status == "Active" and sn.warehouse != warehouse:
                errors.append(
                    f"{serial}: Already Active in another warehouse "
                    f"({sn.warehouse})."
                )
                continue

            if sn.status != "Delivered" or sn.warehouse:
                errors.append(
                    f"{serial}: Cannot recover automatically. "
                    f"Status: {sn.status}, Warehouse: {sn.warehouse}."
                )
                continue

            # -------------------------------------------------
            # Find original outward Sales Invoice for the
            # same customer, company, item and serial.
            # -------------------------------------------------

            original = frappe.db.sql(
                """
                SELECT
                    sle.name,
                    sle.warehouse,
                    sle.company,
                    si.customer,
                    si.name AS original_invoice,
                    sbe.incoming_rate AS recovery_rate
                FROM `tabStock Ledger Entry` sle
                INNER JOIN `tabSales Invoice` si
                    ON si.name = sle.voucher_no
                INNER JOIN `tabSerial and Batch Bundle` sbb
                    ON sbb.name = sle.serial_and_batch_bundle
                INNER JOIN `tabSerial and Batch Entry` sbe
                    ON sbe.parent = sbb.name
                WHERE sle.voucher_type = 'Sales Invoice'
                    AND sle.company = %s
                    AND si.company = %s
                    AND si.customer = %s
                    AND si.docstatus = 1
                    AND si.is_return = 0
                    AND sle.item_code = %s
                    AND sle.is_cancelled = 0
                    AND sle.actual_qty < 0
                    AND sbb.docstatus = 1
                    AND sbb.is_cancelled = 0
                    AND sbb.type_of_transaction = 'Outward'
                    AND sbe.docstatus = 1
                    AND sbe.is_outward = 1
                    AND sbe.serial_no = %s
                    AND sle.posting_datetime < %s
                ORDER BY
                    sle.posting_datetime DESC,
                    sle.creation DESC
                LIMIT 1
                """,
                (
                    doc.company,
                    doc.company,
                    doc.customer,
                    row.item_code,
                    serial,
                    f"{doc.posting_date} {doc.posting_time or '23:59:59'}",
                ),
                as_dict=True,
            )

            if not original:
                errors.append(
                    f"{serial}: Original outward Sales Invoice for "
                    f"this customer was not found."
                )
                continue

            original = original[0]

            if original.warehouse != warehouse:
                errors.append(
                    f"{serial}: Original sale warehouse "
                    f"({original.warehouse}) does not match return "
                    f"warehouse ({warehouse})."
                )
                continue

            if original.recovery_rate is None:
                errors.append(
                    f"{serial}: Original serial valuation rate is missing."
                )
                continue

            rate = flt(original.recovery_rate)

            if rate < 0:
                errors.append(
                    f"{serial}: Original serial valuation rate cannot be negative."
                )
                continue

            pending_serials.append(
                {
                    "serial_no": serial,
                    "rate": rate,
                }
            )

        if not pending_serials:
            continue

        # Keep different valuation rates in separate bundles.
        rates = {}

        for entry in pending_serials:
            rate_key = round(entry["rate"], 6)
            rates.setdefault(rate_key, []).append(entry["serial_no"])

        for rate, rate_serials in rates.items():
            plans.append(
                {
                    "row": row,
                    "item_code": row.item_code,
                    "warehouse": warehouse,
                    "serial_names": rate_serials,
                    "qty": len(rate_serials),
                    "rate": rate,
                }
            )

    # Stop before creating any stock if validation failed.
    if errors:
        frappe.throw(
            _(
                "Stock recovery stopped. No recovery entries were "
                "created because of these validation issues:"
                "<br><br>{0}"
            ).format("<br>".join(errors))
        )

    if not plans and not skipped:
        frappe.throw(
            _("No eligible serial-tracked stock rows were found.")
        )

    # ---------------------------------------------------------
    # PHASE 2: Create inward bundles and positive SLE entries.
    # ---------------------------------------------------------

    posting_date = doc.posting_date
    posting_time = doc.posting_time or "00:00:00"

    for plan in plans:

        row = plan["row"]
        item_code = plan["item_code"]
        warehouse = plan["warehouse"]
        serial_names = plan["serial_names"]
        qty = plan["qty"]
        rate = plan["rate"]

        bundle = SerialBatchCreation(
            {
                "item_code": item_code,
                "warehouse": warehouse,
                "posting_date": posting_date,
                "posting_time": posting_time,
                "voucher_type": "Sales Invoice",
                "voucher_no": doc.name,
                "voucher_detail_no": row.name,
                "qty": qty,
                "actual_qty": qty,
                "avg_rate": rate,
                "incoming_rate": rate,
                "total_amount": qty * rate,
                "type_of_transaction": "Inward",
                "company": doc.company,
                "serial_nos": serial_names,
                "use_serial_batch_fields": 1,
                "make_bundle_from_sle": 1,
                "do_not_submit": 1,
                "custom_is_return_stock_recovery": 1,
            }
        ).make_serial_and_batch_bundle(
            serial_nos=serial_names
        )

        if not bundle or not bundle.name:
            frappe.throw(
                _("Could not create Serial and Batch Bundle for {0}.").format(
                    item_code
                )
            )

        make_sl_entries(
            [
                frappe._dict(
                    {
                        "item_code": item_code,
                        "warehouse": warehouse,
                        "company": doc.company,
                        "posting_date": posting_date,
                        "posting_time": posting_time,
                        "voucher_type": "Sales Invoice",
                        "voucher_no": doc.name,
                        "voucher_detail_no": row.name,
                        "actual_qty": qty,
                        "incoming_rate": rate,
                        "stock_uom": row.stock_uom,
                        "serial_and_batch_bundle": bundle.name,
                        "has_serial_no": 1,
                        "has_batch_no": 0,
                        "is_cancelled": 0,
                        "project": row.project,
                        "cost_center": row.cost_center,
                    }
                )
            ]
        )

        recovered.extend(serial_names)

    return {
        "message": "Return stock recovery completed.",
        "recovered": recovered,
        "skipped": skipped,
        "recovered_count": len(recovered),
        "skipped_count": len(skipped),
    }
