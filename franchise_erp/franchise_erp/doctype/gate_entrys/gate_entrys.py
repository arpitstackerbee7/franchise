# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GateEntrys(Document):
	pass


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