# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



class TZUSetting(Document):
	def validate(self):
		if self.enter_series_length is not None and self.enter_series_length > 9:
			frappe.throw(f"Series Length can not be greater than 1")

		if len(self.product_bundle_series) >self.enter_series_length:
			frappe.throw(f"Product Bundle Series Length can not be greater than {self.enter_series_length}")
	
		if self.box_barcode_series_length is not None and self.box_barcode_series_length > 9:
			frappe.throw("Box Barcode Series Length cannot be greater than 1")

		if self.box_barcode_series and self.box_barcode_series_length:
			if len(self.box_barcode_series) > self.box_barcode_series_length:
				frappe.throw(
					f"Box Barcode Series Length cannot be greater than {self.box_barcode_series_length}"
				)


