import frappe
from frappe.model.document import Document

class BulkSalesReturn(Document):

    def validate(self):
        self.validate_customer()
        self.validate_qty()

    def validate_customer(self):
        for row in self.items:
            dn_customer = frappe.db.get_value(
                "Delivery Note", row.delivery_note, "customer"
            )

            if dn_customer != self.customer:
                frappe.throw(f"Customer mismatch in row {row.idx}")

    def validate_qty(self):

        for row in self.items:

            sent_qty = frappe.db.get_value(
                "Delivery Note Item",
                row.delivery_note_item,
                "qty"
            )

            if row.qty > sent_qty:
                frappe.throw(
                    f"Return qty cannot exceed sent qty in row {row.idx}"
                )

            # check if item is serialized
            has_serial_no = frappe.db.get_value(
                "Item",
                row.item_code,
                "has_serial_no"
            )

            if has_serial_no:

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

    def on_submit(self):

        delivery_notes = {}

        for row in self.items:
            delivery_notes.setdefault(row.delivery_note, []).append(row)

        for dn, items in delivery_notes.items():

            return_doc = frappe.new_doc("Delivery Note")
            return_doc.is_return = 1
            return_doc.return_against = dn
            return_doc.customer = self.customer
            return_doc.company = self.company
            return_doc.custom_bulk_sales_return= self.name
            for row in items:
                serials = row.serial_nos.strip() if row.serial_nos else ""

                return_doc.append("items", {
                    "item_code": row.item_code,
                    "qty": -row.qty,
                    "warehouse": row.warehouse,
                    "rate": row.rate,
                    "serial_no": serials,
                    "dn_detail": row.delivery_note_item,
                    "use_serial_batch_fields": 1 if serials else 0
                })
            return_doc.insert()

@frappe.whitelist()
def submit_created_dns(docname):

    dns = frappe.get_all(
        "Delivery Note",
        filters={
            "custom_bulk_sales_return": docname,
            "docstatus": 0   # only draft
        },
        pluck="name"
    )

    for dn in dns:
        doc = frappe.get_doc("Delivery Note", dn)

        doc.flags.ignore_permissions = True
        doc.submit()

    return dns

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