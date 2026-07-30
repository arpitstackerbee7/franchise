# Copyright (c) 2025, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



class TZUSetting(Document):

    def validate(self):
        validate_incentive_table_rows(self)

        if self.enter_series_length is not None and self.enter_series_length > 9:
            frappe.throw("Series Length can not be greater than 1")

        if self.product_bundle_series and self.enter_series_length:
            if len(self.product_bundle_series) > self.enter_series_length:
                frappe.throw(
                    f"Product Bundle Series Length can not be greater than {self.enter_series_length}"
                )

        if self.box_barcode_series_length is not None and self.box_barcode_series_length > 9:
            frappe.throw("Box Barcode Series Length cannot be greater than 1")

        if self.box_barcode_series and self.box_barcode_series_length:
            if len(self.box_barcode_series) > self.box_barcode_series_length:
                frappe.throw(
                    f"Box Barcode Series Length can not be greater than {self.box_barcode_series_length}"
                )


    def validate_incentive_table_rows(doc):
        tables = {
            "individual_sales_representative_incentives":
                "Individual Sales Representative Incentives",

            "counter_store_level_performance":
                "Counter Store Level Performance",
        }

        for fieldname, label in tables.items():
            rows = doc.get(fieldname) or []

            if len(rows) > 3:
                frappe.throw(
                    _("{0} can have a maximum of 3 rows.").format(label)
                )
