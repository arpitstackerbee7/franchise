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
	
	