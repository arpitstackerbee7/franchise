# import frappe
# from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment
# from frappe import _


# class CustomLeavePolicyAssignment(LeavePolicyAssignment):

#     def grant_leave_alloc_for_employee(self):

#         if self.leaves_allocated:
#             frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))

#         leave_allocations = {}
#         leave_type_details = self.get_leave_type_details()

#         leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
#         doj = frappe.db.get_value("Employee", self.employee, "date_of_joining")

#         end_date = self.effective_to
#         remaining_months = self.calculate_remaining_months(doj, end_date)

#         for d in leave_policy.leave_policy_details:

#             leave_details = leave_type_details.get(d.leave_type)

#             if not leave_details or leave_details.is_lwp:
#                 continue

#             allocated_leaves = self.calculate_prorata(
#                 d.annual_allocation,
#                 remaining_months
#             )

#             leave_allocation, new_leaves_allocated = self.create_leave_allocation(
#                 allocated_leaves,
#                 leave_details,
#                 doj,
#             )

#             leave_allocations[leave_details.name] = {
#                 "name": leave_allocation,
#                 "leaves": new_leaves_allocated,
#             }

#         self.db_set("leaves_allocated", 1)
#         return leave_allocations

#     # -----------------------------
#     # PRO-RATA CALCULATION
#     # -----------------------------
#     def calculate_prorata(self, annual_allocation, months):
#         if not months:
#             return 0

#         return round((annual_allocation / 12) * months)

#     # -----------------------------
#     # MONTH CALCULATION
#     # -----------------------------
#     def calculate_remaining_months(self, doj, end_date):

#         if not doj or not end_date:
#             return 0

#         doj = frappe.utils.getdate(doj)
#         end_date = frappe.utils.getdate(end_date)

#         months = (end_date.year - doj.year) * 12 + (end_date.month - doj.month)

#         return months + 1 if months > 0 else 0

#     # -----------------------------
#     # CUSTOM LEAVE TYPE FETCH
#     # -----------------------------
#     def get_leave_type_details(self):

#         leave_types = frappe.get_all(
#             "Leave Type",
#             fields=["name", "is_lwp"]
#         )

#         return {
#             d.name: frappe._dict(d) for d in leave_types
#         }

import frappe
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment
from frappe import _


class CustomLeavePolicyAssignment(LeavePolicyAssignment):

    def grant_leave_alloc_for_employee(self):

        if self.leaves_allocated:
            frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))

        leave_allocations = {}
        leave_type_details = self.get_leave_type_details()

        leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
        doj = frappe.db.get_value("Employee", self.employee, "date_of_joining")

        end_date = self.effective_to

        # ✅ FIXED MONTH CALCULATION (NO +1)
        remaining_months = self.calculate_remaining_months(doj, end_date)

        for d in leave_policy.leave_policy_details:

            leave_details = leave_type_details.get(d.leave_type)

            if not leave_details or leave_details.is_lwp:
                continue

            # ✅ PRO-RATA CALCULATION
            allocated_leaves = self.calculate_prorata(
                d.annual_allocation,
                remaining_months
            )

            leave_allocation, new_leaves_allocated = self.create_leave_allocation(
                allocated_leaves,
                leave_details,
                doj,
            )

            leave_allocations[leave_details.name] = {
                "name": leave_allocation,
                "leaves": new_leaves_allocated,
            }

        self.db_set("leaves_allocated", 1)
        return leave_allocations

    # -----------------------------
    # PRO-RATA CALCULATION
    # -----------------------------
    def calculate_prorata(self, annual_allocation, months):

        if not months:
            return 0

        return round((annual_allocation / 12) * months)

    # -----------------------------
    # FIXED MONTH CALCULATION
    # -----------------------------
    def calculate_remaining_months(self, doj, end_date):

        if not doj or not end_date:
            return 0

        doj = frappe.utils.getdate(doj)
        end_date = frappe.utils.getdate(end_date)

        # ✅ NO +1 BUG HERE
        months = (end_date.year - doj.year) * 12 + (end_date.month - doj.month)

        return max(0, months)

    # -----------------------------
    # LEAVE TYPE FETCH (FIXED FOR HRMS 15)
    # -----------------------------
    def get_leave_type_details(self):

        leave_types = frappe.get_all(
            "Leave Type",
            fields=["name", "is_lwp"]
        )

        return {
            d.name: frappe._dict(d) for d in leave_types
        }