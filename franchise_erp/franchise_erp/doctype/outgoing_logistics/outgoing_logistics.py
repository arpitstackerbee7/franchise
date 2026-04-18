# Copyright (c) 2025, Franchise Erp
# For license information, please see license.txt

import frappe
# from frappe.model.naming import make_autoname 
from erpnext.accounts.utils import get_fiscal_year
from frappe.model.document import Document
from franchise_erp.send_whatsapp_notification import send_sales_invoice_pdf_from_outgoing_logistics
from franchise_erp.utils.fy_naming import company_fy_autoname
class OutgoingLogistics(Document):

    def autoname(self):

        # 🔥 VERY IMPORTANT (bypass ERP validation)
        self.naming_series = None

        frappe.logger().info("Incoming Logistic autoname triggered")

        company_fy_autoname(self)

    def validate(self):
        if not self.references or len(self.references) == 0:
            frappe.throw("Reference ID is mandatory. Please add at least one row.")

    # def autoname(self):
    #     """
    #     Custom autoname for Outgoing Logistics

    #     Format:
    #     TZUPL-OL-00001-2026-2027

    #     Features:
    #     - FY last me
    #     - Har FY me counter reset
    #     - Automatic series handling
    #     """

    #     # ✅ Safety checks
    #     if not self.owner_site:
    #         frappe.throw("Company is required for naming")

    #     if not self.date:
    #         frappe.throw("Date is required for naming")

    #     if not self.company_abbreviation:
    #         frappe.throw("Company Abbreviation is required")

    #     # ✅ Get values
    #     abbr = self.company_abbreviation

    #     # 🔥 Correct FY fetch
    #     fy = get_fiscal_year(self.date, company=self.owner_site)[0]

    #     # 🔥 Hidden FY-based series (important for reset)
    #     # ERPNext isko unique series maanega
    #     series_pattern = f"{abbr}-OL-{fy}-.#####."

    #     # ✅ Generate temporary name
    #     # Example: TZUPL-OL-2026-2027-00001
    #     temp_name = make_autoname(series_pattern)

    #     try:
    #         parts = temp_name.split("-")

    #         # Last part = running number
    #         number = parts[-1]

    #     except Exception:
    #         frappe.throw("Error while generating naming series")

    #     # ✅ Final required format (FY last me)
    #     # TZUPL-OL-00001-2026-2027
    #     self.name = f"{abbr}-OL-{number}-{fy}"



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
            # ---------------------------
            # Generate Barcode
            # ---------------------------
            # if self.name:
            #     barcode_value = self.name
            #     self.db_set("barcode_value", barcode_value)
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












