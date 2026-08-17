
import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from hrms.hr.utils import share_doc_with_approver


# Users having any of these roles can create/approve/reject backdated leaves
BACKDATE_PRIVILEGED_ROLES = {
    "HR Manager",
    "HR Head",
    "System Manager",
}


class CustomLeaveApplication(LeaveApplication):

    def validate(self):
        # First run standard ERPNext/HRMS validation
        super().validate()

        # Apply our custom creation rules only for new documents
        if self.is_new():
            self.validate_leave_creation_permission()

        # Validate who is allowed to approve/reject
        self.validate_approver_permission()

    def on_update(self):
        # Only notify the leave approver once the application has actually moved
        # out of Draft (i.e. been submitted into a Pending state), not on every Draft save.
        if self.workflow_state != "Draft" and self.status == "Open" and self.docstatus < 1:
            if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
                self.notify_leave_approver()

        share_doc_with_approver(self, self.leave_approver)
        self.publish_update()
        self.notify_approval_status()
	
    # -------------------------------------------------------------------------
    # CREATION PERMISSION
    # -------------------------------------------------------------------------

    def validate_leave_creation_permission(self):
        """
        Rules:

        1. Backdated leave:
           Only HR Manager / HR Head / System Manager can create it.

        2. Today/Future leave:
           Only the employee himself/herself can create it.
        """

        if frappe.session.user == "Administrator":
            return

        user_roles = set(frappe.get_roles(frappe.session.user))

        # ---------------------------------------------------------
        # BACKDATED LEAVE
        # ---------------------------------------------------------

        if self.is_backdated():

            if BACKDATE_PRIVILEGED_ROLES & user_roles:
                # For backdated leave, the HR user creating it becomes
                # the leave approver for notification/reference purposes.
                self.leave_approver = frappe.session.user
                self.leave_approver_name = frappe.db.get_value("User", frappe.session.user, "full_name")
                return

            frappe.throw(
                _(
                    "Backdated Leave Application can only be created by "
                    "HR Manager, HR Head or System Manager."
                ),
                frappe.PermissionError,
            )

        # ---------------------------------------------------------
        # TODAY / FUTURE LEAVE
        # ---------------------------------------------------------

        employee_data = frappe.db.get_value(
            "Employee",
            self.employee,
            ["user_id", "leave_approver"],
            as_dict=True,
        )

        if not employee_data:
            frappe.throw(
                _("Employee {0} does not exist.").format(
                    frappe.bold(self.employee)
                )
            )

        employee_user = employee_data.user_id
        designated_leave_approver = employee_data.leave_approver

        if not employee_user:
            frappe.throw(
                _(
                    "No User is linked with Employee {0}. "
                    "The employee cannot apply for leave."
                ).format(frappe.bold(self.employee))
            )

        if not designated_leave_approver:
            frappe.throw(
                _(
                    "No Leave Approver is assigned for Employee {0}."
                ).format(frappe.bold(self.employee))
            )

        # Employee can create only his/her own leave
        if employee_user != frappe.session.user:
            frappe.throw(
                _(
                    "Only the employee can apply for their own "
                    "Leave Application."
                ),
                frappe.PermissionError,
            )

        # Make sure the document contains the employee's actual
        # designated Leave Approver.
        self.leave_approver = designated_leave_approver

    # -------------------------------------------------------------------------
    # APPROVAL / REJECTION PERMISSION
    # -------------------------------------------------------------------------

    def validate_approver_permission(self):
        """
        Rules:

        Backdated:
            HR Manager / HR Head / System Manager only.

        Today/Future:
            Only the exact designated leave_approver of that employee.
        """

        # Nothing to validate for a brand-new document.
        if self.is_new():
            return

        # Only validate when workflow state is actually changed.
        if not self.has_value_changed("workflow_state"):
            return

        # Administrator bypass
        if frappe.session.user == "Administrator":
            return

        # Only check approval/rejection states
        if self.workflow_state not in ("Approved", "Rejected"):
            return

        user_roles = set(frappe.get_roles(frappe.session.user))

        # ---------------------------------------------------------
        # BACKDATED LEAVE
        # ---------------------------------------------------------

        if self.is_backdated():

            if BACKDATE_PRIVILEGED_ROLES & user_roles:
                return

            frappe.throw(
                _(
                    "Only HR Manager, HR Head or System Manager can "
                    "approve or reject a backdated Leave Application."
                ),
                frappe.PermissionError,
            )

        # ---------------------------------------------------------
        # TODAY / FUTURE LEAVE
        # ---------------------------------------------------------

        # Do NOT give HR Manager / HR Head / System Manager
        # any special bypass here.

        if not self.leave_approver:
            frappe.throw(
                _(
                    "No Leave Approver is assigned to this "
                    "Leave Application."
                )
            )

        if self.leave_approver != frappe.session.user:
            frappe.throw(
                _(
                    "Only {0} is authorized to approve or reject "
                    "this Leave Application."
                ).format(
                    frappe.bold(self.leave_approver)
                ),
                frappe.PermissionError,
            )

    # -------------------------------------------------------------------------
    # BACKDATED CHECK
    # -------------------------------------------------------------------------

    def is_backdated(self):
        """
        Returns True when From Date is before today's date.
        """

        return getdate(self.from_date) < getdate(nowdate())


    

# -----------------------------------------------------------------------------
# LIST / REPORT VIEW PERMISSIONS
# -----------------------------------------------------------------------------

def get_permission_query_conditions(user):
    """
    Controls which Leave Applications appear in List View / Report View.

    Rules:

    HR Manager / HR Head / System Manager:
        Can see all Leave Applications.

    Normal users:
        Can see:
        - their own Leave Applications
        - Leave Applications where they are the designated Leave Approver

        But they cannot see backdated Leave Applications.
    """

    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    user_roles = set(frappe.get_roles(user))

    # HR roles can see all Leave Applications
    if BACKDATE_PRIVILEGED_ROLES & user_roles:
        return ""

    user_escaped = frappe.db.escape(user)

    return f"""
        (
            (
                `tabLeave Application`.owner = {user_escaped}
                OR
                `tabLeave Application`.leave_approver = {user_escaped}
            )
            AND
            `tabLeave Application`.from_date >= CURRENT_DATE
        )
    """


# -----------------------------------------------------------------------------
# DIRECT DOCUMENT PERMISSION
# -----------------------------------------------------------------------------

def has_permission(doc, ptype=None, user=None, debug=False):
    """
    Controls direct document access.

    HR Manager / HR Head / System Manager:
        Full access.

    Normal leave:
        Employee who created it OR designated Leave Approver.

    Backdated leave:
        Normal users cannot access it.
    """

    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    user_roles = set(frappe.get_roles(user))

    # HR roles can access all Leave Applications
    if BACKDATE_PRIVILEGED_ROLES & user_roles:
        return True

    # For new documents, creation is handled by
    # validate_leave_creation_permission().
    if not doc.name:
        return True

    # Normal users cannot access backdated Leave Applications
    if doc.from_date and getdate(doc.from_date) < getdate(nowdate()):
        return False

    # Employee can see their own Leave Application
    if doc.owner == user:
        return True

    # Designated Leave Approver can see the Leave Application
    if doc.leave_approver == user:
        return True

    return False