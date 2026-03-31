# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
from frappe.model.naming import make_autoname 
from erpnext.accounts.utils import get_fiscal_year
from frappe.model.document import Document
from franchise_erp.send_whatsapp_notification import send_sales_invoice_pdf_from_outgoing_logistics

class OutgoingLogistics(Document):

    def validate(self):
        if not self.references or len(self.references) == 0:
            frappe.throw("Reference ID is mandatory. Please add at least one row.")

    def autoname(self):
        # Fetch metadata from the document fields
        abbr = self.company_abbreviation
        fy = get_fiscal_year(self.date, company=self.owner_site)[0]
        series_key = f"{abbr}-OL-"

        # Synchronize series counter with existing records
        res = frappe.db.sql("""
            SELECT name FROM `tabOutgoing Logistics` 
            WHERE name LIKE %s ORDER BY name DESC LIMIT 1
        """, (f"{abbr}-OL-%",))

        if res:
            try:
                last_name = res[0][0]
                parts = last_name.split("-")
                max_idx = int(parts[2])

                db_val = frappe.db.sql("SELECT `current` FROM `tabSeries` WHERE name=%s", (series_key,))
                current_val = db_val[0][0] if db_val else 0
                
                if max_idx > int(current_val):
                    frappe.db.sql("""
                        INSERT INTO `tabSeries` (name, `current`) 
                        VALUES (%s, %s) ON DUPLICATE KEY UPDATE `current` = %s
                    """, (series_key, max_idx, max_idx))
            except (IndexError, ValueError):
                pass

        # Generate final dynamic document name
        self.name = make_autoname(f"{abbr}-OL-.#####.-{fy}")



    # -----------------------------
    # ON SUBMIT
    # -----------------------------
    def on_submit(self):
        if not self.references:
            return

        for row in self.references:
            if not row.source_doctype or not row.source_name:
                continue

            if not frappe.db.exists(row.source_doctype, row.source_name):
                continue

            meta = frappe.get_meta(row.source_doctype)

            # field exist check
            if not meta.has_field("custom_outgoing_logistics_no"):
                continue

            frappe.db.set_value(
                row.source_doctype,
                row.source_name,
                {
                    "custom_outgoing_logistics_reference": self.name,
                    "custom_outgoing_logistics_no": self.name,
                    "custom_document_nolr_no": self.document_no
                },
                update_modified=False
            )

        # ✅ WhatsApp PDF send call
        send_sales_invoice_pdf_from_outgoing_logistics(self)
    # -----------------------------
    # BEFORE CANCEL
    # -----------------------------
    # def before_cancel(self):
    #     if frappe.flags.get("in_cancel_outgoing_logistics"):
    #         return

    #     frappe.flags.in_cancel_outgoing_logistics = True

    #     try:
    #         # Cancel all linked Sales Invoices dynamically
    #         if self.references:
    #             for row in self.references:
    #                 if row.source_doctype != "Sales Invoice" or not row.source_name:
    #                     continue

    #                 if frappe.db.exists("Sales Invoice", row.source_name):
    #                     si = frappe.get_doc("Sales Invoice", row.source_name)

    #                     # Clear any references
    #                     for ref_row in getattr(si, "references", []):
    #                         if getattr(ref_row, "outgoing_logistics", None) == self.name:
    #                             ref_row.outgoing_logistics = None

    #                     # Clear custom fields
    #                     frappe.db.set_value(
    #                         "Sales Invoice",
    #                         si.name,
    #                         {
    #                             "custom_outgoing_logistics_no": None,
    #                             "custom_ol_no": None
    #                         },
    #                         update_modified=False
    #                     )

    #                     # Cancel the Sales Invoice forcibly if submitted
    #                     if si.docstatus == 1:
    #                         si.flags.ignore_permissions = True
    #                         si.cancel()
    #                         frappe.db.commit()

    #     finally:
    #         frappe.flags.in_cancel_outgoing_logistics = False


	
    # -----------------------------
    # UPDATE AFTER SUBMIT
    # -----------------------------
    def on_update_after_submit(self):
        if not self.references:
            return

        for row in self.references:
            if row.source_doctype != "Sales Invoice" or not row.source_name:
                continue

            frappe.db.set_value(
                "Sales Invoice",
                row.source_name,
                "custom_document_nolr_no",
                self.document_no,
                update_modified=False
            )


# def on_cancel(self):
#         """
#         On cancelling Outgoing Logistics:
#         - Clear custom fields in linked Sales Invoices
#         - Remove any references in Sales Invoice linking back to this Outgoing Logistics
#         """
#         if not self.references:
#             return

#         for row in self.references:
#             if row.source_doctype == "Sales Invoice" and row.source_name:
#                 # Fetch the linked Sales Invoice
#                 si = frappe.get_doc("Sales Invoice", row.source_name)

#                 # 1️⃣ Clear custom fields
#                 si.custom_outgoing_logistics_reference = None
#                 if hasattr(si, "custom_outgoing_logistics_no"):
#                     si.custom_outgoing_logistics_no = None

#                 # 2️⃣ Remove any references linking back to this Outgoing Logistics
#                 if hasattr(si, "references") and si.references:
#                     to_remove = []
#                     for r in si.references:
#                         if getattr(r, "source_doctype", "") == "Sales Invoice" and getattr(r, "source_name", "") == self.name:
#                             to_remove.append(r)
#                     for r in to_remove:
#                         si.remove(r)

#                 # Save changes to Sales Invoice
#                 si.save()


def on_cancel(self):
        if not self.references:
            return

        user = frappe.session.user
        user_name = frappe.get_fullname(user) or user

        for row in self.references:
            if not row.source_doctype or not row.source_name:
                continue

            # check document exists
            if not frappe.db.exists(row.source_doctype, row.source_name):
                continue

            try:
                doc = frappe.get_doc(row.source_doctype, row.source_name)

                doc.add_comment(
                    comment_type="Info",
                    text=f"""
                    <b>{user_name}</b> cancelled
                    <b>Outgoing Logistics</b>
                    <a href="/app/outgoing-logistics/{self.name}">{self.name}</a>
                    """
                )

                doc.save(ignore_permissions=True)

            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Outgoing Logistics Cancel Log Failed: {row.source_doctype} {row.source_name}"
                )

        frappe.db.commit()












