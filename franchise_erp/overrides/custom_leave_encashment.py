import frappe
import math
from frappe.utils import flt
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment

ENCASHABLE_LEAVE_TYPES = ["Earned Leave", "Casual Leave", "Sick Leave"]


class CustomLeaveEncashment(LeaveEncashment):
    def get_leave_type_balance(self, leave_type):
        return flt(frappe.db.get_value(
            "Leave Ledger Entry",
            {"employee": self.employee, "leave_type": leave_type, "docstatus": 1},
            "sum(leaves)",
        ) or 0)

    @frappe.whitelist()
    def get_leave_details_for_encashment(self):
        self.set_leave_balance()
        self.set_actual_encashable_days()
        self.calculate_total_leaves_taken()
        self.calculate_slab_deduction()
        self.set_encashment_amount()

    def set_leave_balance(self):
        self.leave_balance = sum(self.get_leave_type_balance(lt) for lt in ENCASHABLE_LEAVE_TYPES)

    def set_actual_encashable_days(self):
        self.actual_encashable_days = self.leave_balance

    def get_lwp_days(self):
        leave_period = frappe.get_doc("Leave Period", self.leave_period)
        lwp_types = frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")
        if not lwp_types:
            return 0

        applications = frappe.get_all(
            "Leave Application",
            filters={
                "employee": self.employee,
                "status": "Approved",
                "leave_type": ["in", lwp_types],
                "from_date": [">=", leave_period.from_date],
                "to_date": ["<=", leave_period.to_date],
            },
            fields=["total_leave_days"],
        )
        return sum(flt(a.total_leave_days) for a in applications)

    def calculate_total_leaves_taken(self):
        leave_period = frappe.get_doc("Leave Period", self.leave_period)

        paid_applications = frappe.get_all(
            "Leave Application",
            filters={
                "employee": self.employee,
                "status": "Approved",
                "leave_type": ["in", ENCASHABLE_LEAVE_TYPES],
                "from_date": [">=", leave_period.from_date],
                "to_date": ["<=", leave_period.to_date],
            },
            fields=["total_leave_days"],
        )
        paid_leaves_availed = sum(flt(a.total_leave_days) for a in paid_applications)

        lwp_days = self.get_lwp_days()

        self.custom_lwp_days = lwp_days
        self.custom_total_leaves_taken = paid_leaves_availed + lwp_days

    def calculate_slab_deduction(self):
        total_taken = flt(self.custom_total_leaves_taken)
        if total_taken <= 30:
            deduction = 0
        else:
            slab_count = min(math.ceil((total_taken - 30) / 10), 6)
            deduction = round(slab_count * 1.13, 2)

        self.custom_encashment_deduction = deduction
        self.encashment_days = max(flt(self.actual_encashable_days) - flt(deduction), 0)

    def create_leave_ledger_entry(self, submit=True):
        remaining = flt(self.encashment_days) if submit else 0
        self.set("custom_encashment_breakdown", [])

        for leave_type in ENCASHABLE_LEAVE_TYPES:
            balance = self.get_leave_type_balance(leave_type)
            deduct_amount = min(balance, remaining) if remaining > 0 else 0

            if balance > 0 and submit:
                self.append("custom_encashment_breakdown", {
                    "leave_type": leave_type,
                    "balance_available": balance,
                    "days_encashed": deduct_amount,
                })

            if deduct_amount > 0:
                frappe.get_doc({
                    "doctype": "Leave Ledger Entry",
                    "employee": self.employee,
                    "leave_type": leave_type,
                    "leaves": -1 * deduct_amount,
                    "transaction_type": "Leave Encashment",
                    "transaction_name": self.name,
                    "is_carry_forward": 0,
                    "is_expired": 0,
                    "company": self.company,
                    "docstatus": 1,
                }).insert(ignore_permissions=True)
                remaining -= deduct_amount

        if submit:
            self.db_update_all()