import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.controllers.sales_and_purchase_return import make_return_doc
class BulkSalesReturn(Document):

    def validate(self):
        self.validate_customer()
        self.validate_qty()

    def validate_customer(self):
        for row in self.items:
            dn_customer = frappe.db.get_value(
                "Delivery Note", row.delivery_note, "customer"
            )

            
                

    def validate_qty(self):

      for row in self.items:

        # 🔹 Case 1: Delivery Note based
        if row.delivery_note_item:

            sent_qty = frappe.db.get_value(
                "Delivery Note Item",
                row.delivery_note_item,
                "qty"
            ) or 0

            if row.qty > sent_qty:
                frappe.throw(
                    f"Return qty cannot exceed sent qty in row {row.idx}"
                )

        # 🔹 Case 2: Sales Invoice based
        elif row.sales_invoice_item:

            billed_qty = frappe.db.get_value(
                "Sales Invoice Item",
                row.sales_invoice_item,
                "qty"
            ) or 0

            if row.qty > billed_qty:
                frappe.throw(
                    f"Return qty cannot exceed billed qty in row {row.idx}"
                )

        # 🔥 SERIAL VALIDATION (same as before)
        has_serial_no = frappe.db.get_value(
            "Item",
            row.item_code,
            "has_serial_no"
        )

        if has_serial_no and (row.delivery_note_item or row.sales_invoice_item):

            serials = []

            if row.serial_nos:
                serials = [s.strip() for s in row.serial_nos.split("\n") if s.strip()]

            if not serials:
                frappe.throw(
                    f"Row {row.idx}: Serial Numbers are required for serialized item {row.item_code}"
                )

            if len(serials) != row.qty:
                frappe.throw(
                    f"Row {row.idx}: Qty must match number of Serial Numbers for item {row.item_code}"
                )
    #fixed gst
    def on_submit(self):

        self.db_set("status", "Queued")
        frappe.db.commit()

        # 🚀 Enqueue background job
        frappe.enqueue(
            method="franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.process_bulk_sales_return",
            docname=self.name,
            queue="long",
            timeout=600,
            job_name=f"Bulk Sales Return {self.name}"
        )

        # 💬 User message
        frappe.msgprint(
            "Return documents are being created in the background."
        )


def process_bulk_sales_return(docname):

    doc = frappe.get_doc("Bulk Sales Return", docname)

    try:

        doc.db_set("status", "In Progress")
        frappe.db.commit()

        delivery_notes = {}
        sales_invoices = {}

        for row in doc.items:

            if row.delivery_note:
                delivery_notes.setdefault(row.delivery_note, []).append(row)

            elif row.sales_invoice:
                sales_invoices.setdefault(row.sales_invoice, []).append(row)

        # 🔹 DELIVERY NOTE RETURN
        for dn, items in delivery_notes.items():

            return_doc = make_return_doc("Delivery Note", dn)
            return_doc.custom_bulk_sales_return = doc.name

            # Aggregate user-selected rows by source Delivery Note Item name
            selected = {}
            for row in items:
                key = row.delivery_note_item
                if not key:
                    continue
                selected.setdefault(key, {"qty": 0, "serials": []})
                selected[key]["qty"] += flt(row.qty)
                if row.serial_nos:
                    selected[key]["serials"].extend(
                        s.strip() for s in row.serial_nos.split("\n") if s.strip()
                    )

            # make_return_doc preserves source order, so match return items
            # to original DN items by position. Keep only selected lines and
            # override qty + serials; all pricing/tax fields stay intact.
            original_dn = frappe.get_doc("Delivery Note", dn)
            kept = []
            for orig_item, ret_item in zip(original_dn.items, return_doc.items):
                sel = selected.get(orig_item.name)
                if not sel:
                    continue
                ret_item.qty = -abs(sel["qty"])
                if sel["serials"]:
                    ret_item.serial_no = "\n".join(sel["serials"])
                    ret_item.use_serial_batch_fields = 1
                kept.append(ret_item)

            return_doc.items = kept
            return_doc.insert(ignore_permissions=True)

        # 🔹 SALES INVOICE RETURN
        for si, items in sales_invoices.items():

            si_return = make_return_doc("Sales Invoice", si)
            si_return.custom_bulk_sales_return = doc.name

            selected = {}
            for row in items:
                key = row.sales_invoice_item
                if not key:
                    continue
                selected.setdefault(key, {"qty": 0, "serials": []})
                selected[key]["qty"] += flt(row.qty)
                if row.serial_nos:
                    selected[key]["serials"].extend(
                        s.strip() for s in row.serial_nos.split("\n") if s.strip()
                    )

            original_si = frappe.get_doc("Sales Invoice", si)
            kept = []
            for orig_item, ret_item in zip(original_si.items, si_return.items):
                sel = selected.get(orig_item.name)
                if not sel:
                    continue
                ret_item.qty = -abs(sel["qty"])
                if sel["serials"]:
                    ret_item.serial_no = "\n".join(sel["serials"])
                    ret_item.use_serial_batch_fields = 1
                kept.append(ret_item)

            si_return.items = kept
            si_return.insert(ignore_permissions=True)

        doc.db_set("status", "Completed")
        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Bulk Sales Return Failed")

        doc.db_set("status", "Failed")
        frappe.db.commit()


@frappe.whitelist()
def submit_created_returns(docname):

    doc = frappe.get_doc("Bulk Sales Return", docname)
    doc.db_set("submit_status", "Queued")
    frappe.db.commit()

    frappe.enqueue(
        method="franchise_erp.franchise_erp.doctype.bulk_sales_return.bulk_sales_return.process_submit_returns",
        docname=docname,
        queue="long",
        timeout=600,
        job_name=f"Submit Returns for {docname}"
    )

    return "Queued"


def process_submit_returns(docname):

    doc = frappe.get_doc("Bulk Sales Return", docname)

    try:
        doc.db_set("submit_status", "In Progress")
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
            dn_doc = frappe.get_doc("Delivery Note", dn)
            dn_doc.flags.ignore_permissions = True
            dn_doc.submit()

        sis = frappe.get_all(
            "Sales Invoice",
            filters={
                "custom_bulk_sales_return": docname,
                "docstatus": 0
            },
            pluck="name"
        )

        for si in sis:
            si_doc = frappe.get_doc("Sales Invoice", si)
            si_doc.flags.ignore_permissions = True
            si_doc.submit()

        doc.db_set("submit_status", "Completed")
        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Submit Sales Returns Failed")

        doc.db_set("submit_status", "Failed")
        frappe.db.commit()

@frappe.whitelist()
def has_draft_return_dns(docname):

    exists = frappe.db.exists(
        "Delivery Note",
        {
            "custom_bulk_sales_return": docname,
            "docstatus": 0  # Draft
        }
    )

    return bool(exists)

@frappe.whitelist()
def has_draft_return_sis(docname):

    exists = frappe.db.exists(
        "Sales Invoice",
        {
            "custom_bulk_sales_return": docname,
            "docstatus": 0  # Draft
        }
    )

    return bool(exists)

@frappe.whitelist()
def get_returnable_items(customer, company, item_code=None):

    conditions = "AND dn.customer = %(customer)s AND dn.company = %(company)s"

    if item_code:
        conditions += " AND dni.item_code = %(item_code)s"

    items = frappe.db.sql(f"""
        SELECT
            dni.parent AS delivery_note,
            dni.name AS delivery_note_item,
            dni.item_code,
            dni.qty AS delivered_qty,
            dni.returned_qty,
            (dni.qty - dni.returned_qty) AS returnable_qty,
            0 AS return_qty,
            i.has_serial_no
        FROM `tabDelivery Note Item` dni
        JOIN `tabDelivery Note` dn
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
    as_dict=1)

    return items

@frappe.whitelist()
def get_dn_item_details(items):

    items = frappe.parse_json(items)
    result = []

    for d in items:

        dn_item = frappe.get_doc("Delivery Note Item", d.get("delivery_note_item"))
        item_doc = frappe.get_doc("Item", dn_item.item_code)

        is_serialized = item_doc.has_serial_no

        # original DN serials
        dn_serials = []
        if dn_item.serial_no:
            dn_serials = dn_item.serial_no.split("\n")

        # returned serials (from Sales Return DN)
        returned_serials = frappe.db.sql("""
            SELECT dni.serial_no
            FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn
            ON dni.parent = dn.name
            WHERE dn.is_return = 1
            AND dn.docstatus = 1
            AND dni.dn_detail = %s
        """, dn_item.name, as_dict=1)

        returned_list = []

        for r in returned_serials:
            if r.serial_no:
                returned_list.extend(r.serial_no.split("\n"))

        available_serials = list(set(dn_serials) - set(returned_list))

        scanned_serials = []

        if d.get("serial_nos"):
            scanned_serials = [
                s.strip() for s in d.get("serial_nos").split("\n") if s.strip()
            ]

        # ❌ validation
        invalid_serials = list(set(scanned_serials) - set(available_serials))
        if invalid_serials:
            frappe.throw(
                f"Invalid Serial(s) for Item {dn_item.item_code}: {', '.join(invalid_serials)}"
            )

        # warehouse grouping
        warehouse_map = {}

        if is_serialized:

            for serial in scanned_serials:

                serial_doc = frappe.get_doc("Serial No", serial)

                # For sales return → stock comes back to warehouse
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

            qty = d.get("return_qty")
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

@frappe.whitelist()
def get_dn_from_serial(serial_no, company):

    dn_item = frappe.db.sql("""
        SELECT
            dni.name,
            dni.parent AS delivery_note,
            dni.item_code,
            dni.qty,
            dni.returned_qty
        FROM `tabDelivery Note Item` dni
        JOIN `tabDelivery Note` dn
            ON dn.name = dni.parent
        WHERE dn.docstatus = 1
        AND dn.company = %s
        AND dni.serial_no LIKE %s
        LIMIT 1
    """, (company, f"%{serial_no}%"), as_dict=True)

    if not dn_item:
        return None

    dn_item = dn_item[0]

    serial = frappe.get_doc("Serial No", serial_no)

    return {
        "delivery_note": dn_item.delivery_note,
        "delivery_note_item": dn_item.name,
        "item_code": dn_item.item_code,
        "serial_no": serial_no,
        "status": serial.status,
        "returnable_qty": 1,
        "returned_qty": dn_item.returned_qty or 0,
        "return_qty": 1
    }

@frappe.whitelist()
def get_si_from_serial(serial_no, company, sales_invoice=None, customer=None):

    conditions = "AND si.company = %(company)s"
    params = {
        "serial_pattern": f"%{serial_no}%",
        "company": company
    }

    if sales_invoice:
        conditions += " AND si.name = %(sales_invoice)s"
        params["sales_invoice"] = sales_invoice

    if customer:
        conditions += " AND si.customer = %(customer)s"
        params["customer"] = customer

    si_item = frappe.db.sql(f"""
        SELECT
            sii.name AS sales_invoice_item,
            sii.parent AS sales_invoice,
            sii.item_code,
            sii.item_name,
            sii.qty AS billed_qty,
            sii.rate,
            sii.warehouse,
            i.has_serial_no
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE si.docstatus = 1
        AND si.is_return = 0
        AND si.update_stock = 1
        AND sii.serial_no LIKE %(serial_pattern)s
        {conditions}
        LIMIT 1
    """, params, as_dict=True)

    if not si_item:
        return None

    si_item = si_item[0]

    if not frappe.db.exists("Serial No", serial_no):
        return None

    serial = frappe.get_doc("Serial No", serial_no)

    returned_qty = frappe.db.sql("""
        SELECT IFNULL(SUM(ABS(sii2.qty)), 0) AS returned_qty
        FROM `tabSales Invoice Item` sii2
        JOIN `tabSales Invoice` si2 ON si2.name = sii2.parent
        WHERE si2.is_return = 1
        AND si2.docstatus = 1
        AND si2.return_against = %s
        AND sii2.item_code = %s
    """, (si_item.sales_invoice, si_item.item_code), as_dict=True)

    returned_qty_val = returned_qty[0].returned_qty if returned_qty else 0
    returnable_qty = (si_item.billed_qty or 0) - (returned_qty_val or 0)

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

@frappe.whitelist()
def get_sales_invoice_returnable_items(customer, company, sales_invoice=None, item_code=None):

    conditions = "AND si.customer = %(customer)s AND si.company = %(company)s"

    if sales_invoice:
        conditions += " AND si.name = %(sales_invoice)s"

    if item_code:
        conditions += " AND sii.item_code = %(item_code)s"

    items = frappe.db.sql(f"""
        SELECT
            sii.parent AS sales_invoice,
            sii.name AS sales_invoice_item,
            sii.item_code,
            sii.item_name,
            sii.qty AS billed_qty,
            CASE
              WHEN si.update_stock = 1 THEN sii.qty
              ELSE sii.delivered_qty
            END AS delivered_qty,

            IFNULL((
                SELECT SUM(ABS(sii2.qty))
                FROM `tabSales Invoice Item` sii2
                JOIN `tabSales Invoice` si2 ON si2.name = sii2.parent
                WHERE si2.is_return = 1
                AND si2.return_against = sii.parent
                AND sii2.item_code = sii.item_code
                ), 0) AS returned_qty,

            (
               CASE
                   WHEN si.update_stock = 1 THEN sii.qty
                   ELSE sii.delivered_qty
                END
                -
                IFNULL((
                   SELECT SUM(ABS(sii2.qty))
                   FROM `tabSales Invoice Item` sii2
                   JOIN `tabSales Invoice` si2 ON si2.name = sii2.parent
                   WHERE si2.is_return = 1
                   AND si2.return_against = sii.parent
                   AND sii2.item_code = sii.item_code
                 ), 0)
            ) AS returnable_qty,

            0 AS return_qty,
            i.has_serial_no,
            sii.rate,
            sii.warehouse

        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code

        WHERE si.docstatus = 1
        AND si.is_return = 0
        {conditions}
        AND (
             sii.delivered_qty > 0 OR si.update_stock = 1
        )
        HAVING returnable_qty > 0
        ORDER BY si.posting_date DESC
    """, {
        "sales_invoice": sales_invoice,
        "customer": customer,
        "company": company,
        "item_code": item_code
    }, as_dict=1)

    return items

    