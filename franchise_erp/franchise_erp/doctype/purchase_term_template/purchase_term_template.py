# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PurchaseTermTemplate(Document):
	def validate(self):
		for row in self.purchase_term_charges:

			# APPLY ON VALIDATION
			if row.charge_type == "Rate Diff" and row.apply_on != "Item":
				frappe.throw(
					f"Row {row.idx}: Rate Diff can only be applied on Item"
				)

			if row.charge_type == "Discount" and row.apply_on != "Taxable Amount":
				frappe.throw(
					f"Row {row.idx}: Discount can only be applied on Taxable Amount"
				)

			# VALUE TYPE VALIDATION
			if row.charge_type in ("Rate Diff", "Freight"):
				if row.value_type != "Amount":
					frappe.throw(
						f"Row {row.idx}: {row.charge_type} must have Value Type = Amount"
					)


