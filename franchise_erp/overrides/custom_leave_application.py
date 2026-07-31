
import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


class CustomLeaveApplication(LeaveApplication):

	def validate(self):
		self.validate_backdated_application()
		super().validate()

	def validate_backdated_application(self):
		"""
		Block leave application for past dates when the employee
		applies for themselves. HR Manager / System Manager / Administrator
		are exempt (they may need to record backdated entries).
		"""
		if frappe.session.user == "Administrator":
			return

		exempt_roles = {"HR Manager", "System Manager"}
		user_roles = set(frappe.get_roles(frappe.session.user))

		if exempt_roles & user_roles:
			return

		if getdate(self.from_date) < getdate(nowdate()):
			frappe.throw(
				_("Leave cannot be applied for past dates. From Date must be today or a future date.")
			)