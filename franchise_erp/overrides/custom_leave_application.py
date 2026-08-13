
import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


class CustomLeaveApplication(LeaveApplication):

	def validate(self):
		self.validate_backdated_application()
		super().validate()

	def validate_backdated_application(self):
		if not self.is_new():
			return
		if frappe.session.user == "Administrator":
			return

		exempt_roles = {"HR Manager", "System Manager", "Leave Approver"}
		user_roles = set(frappe.get_roles(frappe.session.user))

		if exempt_roles & user_roles:
			return

		if getdate(self.from_date) < getdate(nowdate()):
			frappe.throw(
				_("Leave cannot be applied for past dates. From Date must be today or a future date.")
			)