import frappe
from frappe.utils import flt
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment

ENCASHABLE_LEAVE_TYPES = ["Earned Leave", "Casual Leave", "Sick Leave"]

SLAB_TABLE = [
    (30, 0), (40, 1.13), (50, 2.26), (60, 3.39),
    (70, 4.52), (80, 5.65), (90, 6.78),
]


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
        self.calculate_slab_deduction()
        self.set_encashment_amount()

    def set_leave_balance(self):
        self.leave_balance = sum(self.get_leave_type_balance(lt) for lt in ENCASHABLE_LEAVE_TYPES)

    def set_actual_encashable_days(self):
        self.actual_encashable_days = self.leave_balance

    def calculate_slab_deduction(self):
        total_taken = flt(self.custom_total_leaves_taken)
        deduction = 6.78
        for limit, ded in SLAB_TABLE:
            if total_taken <= limit:
                deduction = ded
                break
        self.custom_encashment_deduction = deduction
        self.encashment_days = max(flt(self.actual_encashable_days) - flt(deduction), 0)

    def create_leave_ledger_entry(self, submit=True):
        """Override: EL -> CL -> SL priority-wise deduction + breakdown table."""
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