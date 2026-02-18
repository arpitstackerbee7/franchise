# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OutgoingLogistics(Document):

	def on_submit(self, method=None):
		if not self.sales_invoice_no:
			return

		for row in self.sales_invoice_no:
			if not row.sales_invoice:
				continue

			# Do not overwrite if already linked
			existing_ref = frappe.db.get_value(
				"Sales Invoice",
				row.sales_invoice,
				"custom_outgoing_logistics_reference"
			)

			if existing_ref:
				continue

			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"custom_outgoing_logistics_reference",
				self.name
			)

			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"custom_outgoing_logistics_no",
				self.name
			)

			
			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"custom_document_nolr_no",
				self.document_no
			)



	def before_cancel(self, method=None):
		# Prevent recursive cancel
		if frappe.flags.in_cancel_outgoing_logistics:
			return

		frappe.flags.in_cancel_outgoing_logistics = True

		try:
			for row in self.sales_invoice_no:
				if not row.sales_invoice:
					continue

				si = frappe.get_doc("Sales Invoice", row.sales_invoice)

				# Cancel only if submitted
				if si.docstatus == 1:
					# Remove link BEFORE cancel to avoid validation error
					frappe.db.set_value(
						"Sales Invoice",
						si.name,
						"custom_outgoing_logistics_reference",
						None,
						update_modified=False
					)

					si.flags.ignore_permissions = True
					si.cancel()

		finally:
			frappe.flags.in_cancel_outgoing_logistics = False


	def on_update_after_submit(self):
		if not self.sales_invoice_no:
			return

		for row in self.sales_invoice_no:
			if not row.sales_invoice:
				continue

			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"custom_document_nolr_no",
				self.document_no
			)
