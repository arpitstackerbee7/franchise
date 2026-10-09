# import frappe
# from helpdesk.helpdesk.doctype.hd_team.hd_team import HDTeam


# class CustomHDTeam(HDTeam):

#     def validate(self):
#         self.ensure_assignment_rule()

#     def ensure_assignment_rule(self):
#         if not self.assignment_rule:
#             return

#         if frappe.db.exists("Assignment Rule", self.assignment_rule):
#             return

#         rule_name = self.assignment_rule

#         if frappe.db.exists("Assignment Rule", rule_name):
#             return

#         rule_doc = frappe.new_doc("Assignment Rule")
#         rule_doc.name = rule_name
#         rule_doc.document_type = "HD Ticket"
#         rule_doc.assign_condition = (
#             f"status == 'Open' and agent_group == '{self.name}'"
#         )
#         rule_doc.assign_condition_json = (
#             f'[["status","==","Open"],"and",'
#             f'["agent_group","==","{self.name}"]]'
#         )
#         rule_doc.priority = 1
#         rule_doc.disabled = True

#         for day in [
#             "Monday",
#             "Tuesday",
#             "Wednesday",
#             "Thursday",
#             "Friday",
#             "Saturday",
#             "Sunday",
#         ]:
#             rule_doc.append(
#                 "assignment_days",
#                 {
#                     "doctype": "Assignment Rule Day",
#                     "day": day,
#                 },
#             )

#         rule_doc.insert(ignore_permissions=True)

#     def on_update(self):
#         if not self.assignment_rule:
#             return

#         if not frappe.db.exists(
#             "Assignment Rule",
#             self.assignment_rule,
#         ):
#             return

#         self.update_support_rotations()

#     def update_support_rotations(self):
#         if not self.assignment_rule:
#             return

#         if not frappe.db.exists(
#             "Assignment Rule",
#             self.assignment_rule,
#         ):
#             return

#         return super().update_support_rotations()