# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from frappe.utils import now
class GateEntrys(Document):
	# pass

	def before_submit(self):   # 🔥 CHANGE HERE

		if not self.no_of_parcels:
			return

		self.set("gate_entry_box_barcode", [])

		parts = self.name.split("-")

		try:
			last = "%03d" % int(parts[-1])
		except:
			last = parts[-1]

		base_name = parts[0] + "-" + last

		for i in range(1, int(self.no_of_parcels) + 1):

			serial = "%02d" % i
			final_barcode = f"{base_name}-{serial}"

			self.append("gate_entry_box_barcode", {
				"box_barcode": final_barcode,
				"total_barcode_qty": self.no_of_parcels,
				"status": "Received",
				"scan_date_time": now()
			})
# import frappe
# from frappe.model.naming import make_autoname
# from datetime import datetime

# class GateEntrys(frappe.model.document.Document):

#     def autoname(self):
#         today = datetime.now()
#         year = today.year
#         month = today.month

#         # Fiscal Year (April to March)
#         if month >= 4:
#             start_year = year
#             end_year = year + 1
#         else:
#             start_year = year - 1
#             end_year = year

#         short_year = str(start_year)[2:] + "-" + str(end_year)[2:]

#         # Naming Series
#         series = f"GE/{short_year}/.#####"

#         # Generate Name safely
#         self.name = make_autoname(series)