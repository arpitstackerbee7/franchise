# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.utils import get_stock_balance


class BulkPurchaseReturn(Document):

    def validate(self):
        self.validate_supplier()
        self.validate_qty()
        self.validate_non_serialized_stock()


    def validate_supplier(self):

        for row in self.items:

            pr_supplier = frappe.db.get_value(
                "Purchase Receipt",
                row.purchase_receipt,
                "supplier"
            )

            if pr_supplier != self.supplier:

                frappe.throw(
                    f"Supplier mismatch in row {row.idx}"
                )


    def validate_qty(self):

        for row in self.items:

            received_qty = frappe.db.get_value(
                "Purchase Receipt Item",
                row.purchase_receipt_item,
                "qty"
            ) or 0


            if flt(row.qty) > flt(received_qty):

                frappe.throw(
                    f"Return qty cannot exceed received qty in row {row.idx}"
                )


            has_serial_no = frappe.db.get_value(
                "Item",
                row.item_code,
                "has_serial_no"
            )


            if has_serial_no:

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


                if len(serials) != flt(row.qty):

                    frappe.throw(
                        f"Row {row.idx}: Qty must match number of "
                        f"Serial Numbers for item {row.item_code}"
                    )


    def validate_non_serialized_stock(self):

        for row in self.items:

            has_serial_no = frappe.db.get_value(
                "Item",
                row.item_code,
                "has_serial_no"
            )


            if has_serial_no:
                continue


            available_stock = get_stock_balance(
                row.item_code,
                row.warehouse
            )


            if flt(available_stock) < flt(row.qty):

                frappe.throw(
                    f"Row {row.idx}: Not enough stock for "
                    f"Item {row.item_code} in Warehouse "
                    f"{row.warehouse}. Available: "
                    f"{available_stock}, Required: {row.qty}"
                )


    def on_submit(self):

        self.db_set("status", "Queued")
        frappe.db.commit()


        frappe.enqueue(

            method=
                "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.process_bulk_purchase_return",

            docname=self.name,

            queue="long",

            timeout=600,

            job_name=f"Bulk Purchase Return {self.name}"
        )


        frappe.msgprint(
            "Return document is being created in the background."
        )



def process_bulk_purchase_return(docname):

    doc = frappe.get_doc(
        "Bulk Purchase Return",
        docname
    )


    try:

        doc.db_set(
            "status",
            "In Progress"
        )

        frappe.db.commit()


        # --------------------------------------------------
        # GROUP ITEMS BY ORIGINAL PURCHASE RECEIPT
        # --------------------------------------------------

        grouped = {}


        for row in doc.items:

            grouped.setdefault(
                row.purchase_receipt,
                []
            ).append(row)


        combined_doc = None


        # --------------------------------------------------
        # CREATE ONE COMBINED RETURN PURCHASE RECEIPT
        # --------------------------------------------------

        for purchase_receipt, rows in grouped.items():


            return_doc = make_return_doc(
                "Purchase Receipt",
                purchase_receipt
            )


            return_doc.items = []


            # --------------------------------------------------
            # ADD SELECTED ITEMS OF THIS GRN
            # --------------------------------------------------

            for row in rows:


                pr_item = frappe.get_doc(
                    "Purchase Receipt Item",
                    row.purchase_receipt_item
                )


                serials = (
                    row.serial_nos.strip()
                    if row.serial_nos
                    else ""
                )


                original_wh = (
                    pr_item.warehouse
                )


                warehouse_company = frappe.db.get_value(
                    "Warehouse",
                    original_wh,
                    "company"
                )


                if (
                    warehouse_company !=
                    return_doc.company
                ):

                    frappe.throw(
                        f"Warehouse {original_wh} belongs to "
                        f"{warehouse_company}, but document company "
                        f"is {return_doc.company}"
                    )


                return_doc.append(
                    "items",
                    {

                        "item_code":
                            row.item_code,

                        "item_name":
                            row.item_name,

                        "qty":
                            -abs(flt(row.qty)),

                        "warehouse":
                            original_wh,

                        "rate":
                            row.rate,

                        "uom":
                            row.uom,

                        "stock_uom":
                            row.stock_uom,

                        "conversion_factor":
                            row.conversion_factor,

                        "serial_no":
                            serials,

                        "purchase_order":
                            pr_item.purchase_order,

                        "purchase_order_item":
                            pr_item.purchase_order_item,

                        "purchase_receipt_item":
                            row.purchase_receipt_item
                    }
                )


            # --------------------------------------------------
            # FIRST GRN → BASE RETURN DOCUMENT
            # --------------------------------------------------

            if combined_doc is None:


                combined_doc = return_doc


            # --------------------------------------------------
            # OTHER GRNs → APPEND ITEMS TO SAME DOCUMENT
            # --------------------------------------------------

            else:


                for item in return_doc.items:


                    item_dict = item.as_dict()


                    for field in (
                        "name",
                        "parent",
                        "parenttype",
                        "parentfield",
                        "owner",
                        "creation",
                        "modified",
                        "modified_by",
                        "idx",
                        "docstatus"
                    ):

                        item_dict.pop(
                            field,
                            None
                        )


                    combined_doc.append(
                        "items",
                        item_dict
                    )


        # --------------------------------------------------
        # VALIDATE DOCUMENT
        # --------------------------------------------------

        if (
            not combined_doc or
            not combined_doc.items
        ):

            frappe.throw(
                "No return items found."
            )


        # --------------------------------------------------
        # LINK WITH BULK PURCHASE RETURN
        # --------------------------------------------------

        combined_doc.custom_bulk_purchase_return = doc.name


        # --------------------------------------------------
        # RESET ITEM INDEX
        # --------------------------------------------------

        for idx, item in enumerate(
            combined_doc.items,
            start=1
        ):

            item.idx = idx


        # --------------------------------------------------
        # RE-CALCULATE VALUES
        # --------------------------------------------------

        combined_doc.set_missing_values()

        combined_doc.calculate_taxes_and_totals()


        # --------------------------------------------------
        # CREATE ONLY ONE RETURN PURCHASE RECEIPT
        # --------------------------------------------------

        combined_doc.insert(
            ignore_permissions=True
        )


        doc.db_set(
            "status",
            "Completed"
        )

        frappe.db.commit()



    except Exception:

        frappe.db.rollback()


        frappe.log_error(
            frappe.get_traceback(),
            "Bulk Purchase Return Failed"
        )


        doc.db_set(
            "status",
            "Failed"
        )

        frappe.db.commit()



@frappe.whitelist()
def get_returnable_items(
    supplier,
    company,
    item_code=None
):

    conditions = (
        "AND pr.supplier = %(supplier)s "
        "AND pr.company = %(company)s"
    )


    if item_code:

        conditions += (
            " AND pri.item_code = %(item_code)s"
        )


    items = frappe.db.sql(

        f"""

        SELECT

            pri.parent AS purchase_receipt,

            pri.name AS purchase_receipt_item,

            pri.item_code,

            pri.qty AS received_qty,

            pri.returned_qty,

            (
                pri.qty -
                pri.returned_qty
            ) AS returnable_qty,

            0 AS return_qty,

            i.has_serial_no


        FROM `tabPurchase Receipt Item` pri


        JOIN `tabPurchase Receipt` pr

            ON pr.name = pri.parent


        LEFT JOIN `tabItem` i

            ON i.name = pri.item_code


        WHERE pr.docstatus = 1

        AND pr.is_return = 0

        AND pri.qty >
            IFNULL(pri.returned_qty, 0)

        {conditions}


        ORDER BY pr.posting_date DESC

        """,

        {
            "supplier": supplier,
            "company": company,
            "item_code": item_code
        },

        as_dict=1
    )


    return items



@frappe.whitelist()
def get_pr_item_details(items):

    items = frappe.parse_json(items)

    result = []


    for d in items:


        pr_item = frappe.get_doc(
            "Purchase Receipt Item",
            d.get("purchase_receipt_item")
        )


        item_doc = frappe.get_doc(
            "Item",
            pr_item.item_code
        )


        is_serialized = (
            item_doc.has_serial_no
        )


        pr_serials = []


        if pr_item.serial_no:

            pr_serials = (
                pr_item.serial_no
                .split("\n")
            )


        returned_serials = frappe.db.sql(

            """

            SELECT pri.serial_no

            FROM `tabPurchase Receipt Item` pri


            JOIN `tabPurchase Receipt` pr

                ON pri.parent = pr.name


            WHERE pr.is_return = 1

            AND pr.docstatus = 1

            AND pri.purchase_receipt_item = %s

            """,

            pr_item.name,

            as_dict=1
        )


        returned_list = []


        for r in returned_serials:

            if r.serial_no:

                returned_list.extend(
                    r.serial_no.split("\n")
                )


        available_serials = list(
            set(pr_serials) -
            set(returned_list)
        )


        scanned_serials = []


        if d.get("serial_nos"):

            scanned_serials = [

                s.strip()

                for s in
                d.get("serial_nos").split("\n")

                if s.strip()
            ]


        invalid_serials = list(

            set(scanned_serials) -
            set(available_serials)
        )


        if invalid_serials:

            frappe.throw(

                f"Invalid Serial(s) for Item "
                f"{pr_item.item_code}: "
                f"{', '.join(invalid_serials)}"
            )


        warehouse_map = {}


        if is_serialized:


            for serial in scanned_serials:

                wh = pr_item.warehouse

                warehouse_map.setdefault(
                    wh,
                    []
                ).append(serial)


            for wh, serial_list in warehouse_map.items():


                result.append({

                    "name":
                        pr_item.name,

                    "purchase_receipt":
                        pr_item.parent,

                    "purchase_receipt_item":
                        pr_item.name,

                    "item_code":
                        pr_item.item_code,

                    "item_name":
                        pr_item.item_name,

                    "warehouse":
                        wh,

                    "uom":
                        pr_item.uom,

                    "stock_uom":
                        pr_item.stock_uom,

                    "conversion_factor":
                        pr_item.conversion_factor,

                    "rate":
                        pr_item.rate,

                    "qty":
                        len(serial_list),

                    "returnable_quantity":
                        d.get("returnable_qty"),

                    "serial_nos":
                        "\n".join(serial_list),

                    "available_serial_nos":
                        "\n".join(available_serials)
                })


        else:


            qty = d.get("return_qty")

            wh = pr_item.warehouse


            warehouse_map.setdefault(
                wh,
                0
            )


            warehouse_map[wh] += qty


            for wh, qty in warehouse_map.items():


                result.append({

                    "name":
                        pr_item.name,

                    "purchase_receipt":
                        pr_item.parent,

                    "purchase_receipt_item":
                        pr_item.name,

                    "item_code":
                        pr_item.item_code,

                    "item_name":
                        pr_item.item_name,

                    "warehouse":
                        wh,

                    "uom":
                        pr_item.uom,

                    "stock_uom":
                        pr_item.stock_uom,

                    "conversion_factor":
                        pr_item.conversion_factor,

                    "rate":
                        pr_item.rate,

                    "qty":
                        qty,

                    "returnable_quantity":
                        d.get("returnable_qty"),

                    "serial_nos":
                        "",

                    "available_serial_nos":
                        ""
                })


    return result



@frappe.whitelist()
def get_pr_from_serial(serial_no, company):


    pr_item = frappe.db.sql(

        """

        SELECT

            pri.name,

            pri.parent AS purchase_receipt,

            pri.item_code,

            pri.qty,

            pri.returned_qty


        FROM `tabPurchase Receipt Item` pri


        JOIN `tabPurchase Receipt` pr

            ON pr.name = pri.parent


        WHERE pr.docstatus = 1

        AND pr.company = %s

        AND pri.serial_no LIKE %s

        LIMIT 1

        """,

        (
            company,
            f"%{serial_no}%"
        ),

        as_dict=True
    )


    if not pr_item:

        return None


    pr_item = pr_item[0]


    serial = frappe.get_doc(
        "Serial No",
        serial_no
    )


    return {

        "purchase_receipt":
            pr_item.purchase_receipt,

        "purchase_receipt_item":
            pr_item.name,

        "item_code":
            pr_item.item_code,

        "serial_no":
            serial_no,

        "status":
            serial.status,

        "returnable_qty":
            1,

        "returned_qty":
            pr_item.returned_qty or 0,

        "return_qty":
            1
    }



@frappe.whitelist()
def submit_created_prs(docname):


    doc = frappe.get_doc(
        "Bulk Purchase Return",
        docname
    )


    doc.db_set(
        "submit_status",
        "Queued"
    )


    frappe.db.commit()


    frappe.enqueue(

        method=
            "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.process_submit_prs",

        docname=docname,

        queue="long",

        timeout=600,

        job_name=f"Submit PRs for {docname}"
    )


    return "Queued"



def process_submit_prs(docname):


    doc = frappe.get_doc(
        "Bulk Purchase Return",
        docname
    )


    try:


        doc.db_set(
            "submit_status",
            "In Progress"
        )

        frappe.db.commit()


        prs = frappe.get_all(

            "Purchase Receipt",

            filters={

                "custom_bulk_purchase_return":
                    docname,

                "docstatus":
                    0
            },

            pluck="name"
        )


        for pr in prs:


            pr_doc = frappe.get_doc(
                "Purchase Receipt",
                pr
            )


            pr_doc.flags.ignore_permissions = True


            pr_doc.submit()


        doc.db_set(
            "submit_status",
            "Completed"
        )

        frappe.db.commit()



    except Exception:


        frappe.db.rollback()


        frappe.log_error(

            frappe.get_traceback(),

            "Submit PRs Failed"
        )


        doc.db_set(
            "submit_status",
            "Failed"
        )

        frappe.db.commit()



@frappe.whitelist()
def has_draft_return_prs(docname):


    exists = frappe.db.exists(

        "Purchase Receipt",

        {

            "custom_bulk_purchase_return":
                docname,

            "docstatus":
                0
        }
    )


    return bool(exists)
