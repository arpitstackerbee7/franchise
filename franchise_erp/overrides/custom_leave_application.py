
import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


class CustomLeaveApplication(LeaveApplication):

	def validate(self):
		self.validate_backdated_application()
		self.validate_approver_permission()
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



	def validate_approver_permission(self):
		# Blocks Approve/Reject action if user is not the designated leave_approver
		if self.is_new():
			return

		if self.workflow_state not in ("Approved", "Rejected"):
			return

		if not self.has_value_changed("workflow_state"):
			return

		if frappe.session.user == "Administrator":
			return

		admin_override_roles = {"HR Manager", "System Manager"}
		user_roles = set(frappe.get_roles(frappe.session.user))
		if admin_override_roles & user_roles:
			return

		if self.leave_approver != frappe.session.user:
			frappe.throw(
				_("Only {0} is authorized to approve or reject this Leave Application.").format(
					frappe.bold(self.leave_approver)
				),
				frappe.PermissionError,
			)


def get_permission_query_conditions(user):
	# Controls what appears in List View / Report View
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return ""

	user_roles = set(frappe.get_roles(user))

	if user_roles & {"HR Manager", "System Manager"}:
		return ""

	user_escaped = frappe.db.escape(user)

	if "Leave Approver" in user_roles:
		return f"""(`tabLeave Application`.owner = {user_escaped}
			or `tabLeave Application`.leave_approver = {user_escaped})"""

	return f"""(`tabLeave Application`.owner = {user_escaped})"""


def has_permission(doc, ptype=None, user=None, debug=False):
	# Controls direct document access (e.g. via URL) and workflow action visibility
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))

	if user_roles & {"HR Manager", "System Manager"}:
		return True

	if doc.owner == user:
		return True

	if doc.leave_approver == user:
		return True

	return False