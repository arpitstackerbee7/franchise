import frappe
from helpdesk.helpdesk.doctype.hd_team.hd_team import HDTeam


class CustomHDTeam(HDTeam):

    def update_support_rotations(self):
        if not self.assignment_rule:
            return

        if not frappe.db.exists(
            "Assignment Rule",
            self.assignment_rule
        ):
            frappe.log_error(
                f"Missing Assignment Rule: {self.assignment_rule}",
                "HD Team Support Rotation"
            )
            return

        return super().update_support_rotations()