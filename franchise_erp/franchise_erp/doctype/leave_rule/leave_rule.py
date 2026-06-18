# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, getdate, get_last_day
from frappe.utils import flt, nowdate
from frappe.utils import get_first_day, getdate, flt
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

class LeaveRule(Document):
	pass

def validate(doc, method=None):
    if doc.enable and doc.rule_type:
        exists = frappe.db.exists(
            "Leave Rule",
            {
                "rule_type": doc.rule_type,
                "enable": 1,
                "name": ["!=", doc.name],  # exclude current doc
            }
        )
        if exists:
            frappe.throw(
                _("Only one Leave Rule can be enabled for Rule Type: {0}. Please disable the other first.")
                .format(doc.rule_type)
            )

def attendance_rule_checker(doc, method):
    # Fetch all active rules
    rules = frappe.get_all("Leave Rule", filters={"enable": 1, "docstatus":1}, fields="*")

    # 1. Check for Daily Hours Fulfilment rule
    daily_hours_rule = next((r for r in rules if r["rule_type"] == "Daily Hours Fulfilment"), None)
    if daily_hours_rule and not doc.leave_application:
        check_daily_hours_fulfilment(doc, daily_hours_rule)
        return  # stop further checks

    # 2. Check for Monthly Late Time Allowance rule
    monthly_late_rule = next((r for r in rules if r["rule_type"] == "Monthly Late Time Allowance"), None)
    if monthly_late_rule and not doc.leave_application:
        check_monthly_late_allowance(doc, monthly_late_rule)
        return  # stop further checks

    # 3. Check for Late Entry Count and Early Exit Count rules (they can work together)
    for rule in rules:
        if rule["rule_type"] == "Late Entry Count" and not doc.leave_application:
            apply_late_entry_rule(doc, rule)
        elif rule["rule_type"] == "Early Exit Count" and not doc.leave_application:
            apply_early_exit_rule(doc, rule)

    # 4. Sandwich rule is excluded here, 
    # since it is handled independently from Leave Application side.



def apply_late_entry_rule(attendance, rule):
    att_date = getdate(attendance.attendance_date)
    month_start = get_first_day(att_date)
    month_key = month_start.strftime("%Y-%m")

    # Count total late entries this month till current attendance date
    late_count = frappe.db.count(
        "Attendance",
        {
            "employee": attendance.employee,
            "docstatus": 1,
            "late_entry": 1,
            "attendance_date": ("between", [month_start, att_date]),
        },
    )

    # ----------------------------
    # PATH 1: Affect Leave Balance
    # ----------------------------
    if rule.affect_leave_balance:
        deduction_unit = flt(rule.deduction_unit or 1)

        # Existing leave deductions for this rule + month
        existing_deductions = frappe.db.count(
            "Leave Deduction Log",
            {
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        # Expected new deductions
        expected_deductions = late_count // rule.violations
        new_deductions = expected_deductions - existing_deductions

        if new_deductions <= 0:
            return  # Already up to date

        # Fetch leave priorities (in order)
        priorities = frappe.db.sql(
            """
            SELECT leave_type, priority
            FROM `tabLeave Priority`
            WHERE parent = %s
            AND parenttype = 'Leave Rule'
            ORDER BY COALESCE(priority, 9999)
            """,
            (rule.name,),
            as_dict=True
        )

        if not priorities:
            frappe.log_error(f"No leave priority found for rule {rule.name}", "Leave Rule Warning")

        # Process each new deduction block
        for _ in range(new_deductions):
            remaining_deduction = deduction_unit

            for row in priorities:
                leave_type = row.leave_type
                if not leave_type or remaining_deduction <= 0:
                    continue

                # Fetch current leave balance
                leave_balance = get_leave_balance_on(attendance.employee, leave_type, att_date)
                if leave_balance <= 0:
                    continue

                # Deduct partial if not enough balance
                deduction_now = min(leave_balance, remaining_deduction)

                # Create Leave Deduction Log
                leave_deduction_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": attendance.employee,
                    "leave_type": leave_type,
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": deduction_now,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                leave_deduction_log.insert(ignore_permissions=True)
                leave_deduction_log.submit()

                remaining_deduction -= deduction_now

            # If still remaining → fallback to LWP
            if remaining_deduction > 0:
                lwp_doc = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": attendance.employee,
                    "leave_type": "Leave Without Pay",
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": remaining_deduction,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                lwp_doc.insert(ignore_permissions=True)
                lwp_doc.submit()

    # ----------------------------
    # PATH 2: Payroll Direct Deduction
    # ----------------------------
    if rule.affect_payroll_directly:
        deduction_unit = flt(rule.deduction_unit or 1)

        existing_deductions = frappe.db.count(
            "Payroll Deduction Log",
            {
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        expected_deductions = late_count // rule.violations
        new_deductions = expected_deductions - existing_deductions

        if new_deductions <= 0:
            return  # Already up to date

        for _ in range(new_deductions):
            log = frappe.get_doc({
                "doctype": "Payroll Deduction Log",
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "deduction_days": 1,
                "deduction_unit": deduction_unit,
                "reference_doctype": "Attendance",
                "reference_name": attendance.name,
            })
            log.insert(ignore_permissions=True)
            log.submit()


def apply_early_exit_rule(attendance, rule):
    att_date = getdate(attendance.attendance_date)
    month_start = get_first_day(att_date)
    month_key = month_start.strftime("%Y-%m")
    deduction_unit = flt(rule.deduction_unit or 1)

    # ----------------------------------
    # PATH 1: Payroll Direct Deduction
    # ----------------------------------
    if rule.affect_payroll_directly:
        early_exit_count = frappe.db.count(
            "Attendance",
            {
                "employee": attendance.employee,
                "docstatus": 1,
                "early_exit": 1,
                "attendance_date": ("between", [month_start, att_date]),
            },
        )

        existing_deductions = frappe.db.count(
            "Payroll Deduction Log",
            {
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        expected_deductions = early_exit_count // rule.violations
        new_deductions = expected_deductions - existing_deductions

        if new_deductions <= 0:
            return  # Nothing new to add

        for _ in range(new_deductions):
            log = frappe.get_doc({
                "doctype": "Payroll Deduction Log",
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "deduction_days": 1,
                "deduction_unit": deduction_unit,
                "reference_doctype": "Attendance",
                "reference_name": attendance.name,
            })
            log.insert(ignore_permissions=True)
            log.submit()

    # ----------------------------------
    # PATH 2: Affect Leave Balance
    # ----------------------------------
    if rule.affect_leave_balance:
        early_exit_count = frappe.db.count(
            "Attendance",
            {
                "employee": attendance.employee,
                "docstatus": 1,
                "early_exit": 1,
                "attendance_date": ("between", [month_start, att_date]),
            },
        )

        existing_deductions = frappe.db.count(
            "Leave Deduction Log",
            {
                "employee": attendance.employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        expected_deductions = early_exit_count // rule.violations
        new_deductions = expected_deductions - existing_deductions

        if new_deductions <= 0:
            return

        # Get leave priorities from child table
        priorities = frappe.db.sql(
            """
            SELECT leave_type, priority
            FROM `tabLeave Priority`
            WHERE parent = %s
            AND parenttype = 'Leave Rule'
            ORDER BY COALESCE(priority, 9999)
            """,
            (rule.name,),
            as_dict=True,
        )

        if not priorities:
            frappe.log_error(f"No leave priority found for rule {rule.name}", "Leave Rule Warning")

        for _ in range(new_deductions):
            remaining_to_deduct = deduction_unit

            # Go through each leave type in order
            for row in priorities:
                leave_type = row.leave_type
                if not leave_type or remaining_to_deduct <= 0:
                    continue

                # Check available balance
                leave_balance = get_leave_balance_on(attendance.employee, leave_type, att_date)

                if leave_balance <= 0:
                    continue

                # Deduct as much as possible from this leave
                deduction_now = min(leave_balance, remaining_to_deduct)

                leave_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": attendance.employee,
                    "leave_type": leave_type,
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": deduction_now,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                leave_log.insert(ignore_permissions=True)
                leave_log.submit()

                remaining_to_deduct -= deduction_now

                # If fully deducted, stop
                if remaining_to_deduct <= 0:
                    break

            # If still pending deduction → use Leave Without Pay
            if remaining_to_deduct > 0:
                lwp_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": attendance.employee,
                    "leave_type": "Leave Without Pay",
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": remaining_to_deduct,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                lwp_log.insert(ignore_permissions=True)
                lwp_log.submit()


def check_monthly_late_allowance(attendance, rule):

    if not attendance.late_entry or not attendance.custom_late_minutes:
        return

    att_date = getdate(attendance.attendance_date)
    employee = attendance.employee
    month_start = get_first_day(att_date)
    month_key = month_start.strftime("%Y-%m")
    deduction_unit = flt(rule.deduction_unit or 1)

    # ----------------------------------
    # Calculate total late minutes in the month
    # ----------------------------------
    records = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "docstatus": 1,
            "attendance_date": ("between", [month_start, att_date]),
            "late_entry": 1,
        },
        fields=["attendance_date", "custom_late_minutes"],
        order_by="attendance_date asc"
    )

    # ----------------------------------
    # Step 1: Identify which late entries actually exceed the monthly limit
    # ----------------------------------
    cumulative_minutes = 0
    exceed_records = []

    for rec in records:
        cumulative_minutes += rec.custom_late_minutes or 0
        if cumulative_minutes > rule.allowed_late_minutes:
            exceed_records.append(rec)

    if not exceed_records:
        return  # Limit not crossed yet

    # Number of deductions based on rule.violations
    required_deductions = len(exceed_records) // rule.violations
    if required_deductions <= 0:
        return

    # ----------------------------------
    # PATH 1: Payroll Direct Deduction
    # ----------------------------------
    if rule.affect_payroll_directly:
        existing_deductions = frappe.db.count(
            "Payroll Deduction Log",
            {
                "employee": employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        to_create = required_deductions - existing_deductions
        if to_create <= 0:
            return

        for _ in range(to_create):
            log = frappe.get_doc({
                "doctype": "Payroll Deduction Log",
                "employee": employee,
                "rule": rule.name,
                "month": month_key,
                "deduction_days": 1,
                "deduction_unit": deduction_unit,
                "reference_doctype": "Attendance",
                "reference_name": attendance.name,
            })
            log.insert(ignore_permissions=True)
            log.submit()

    # ----------------------------------
    # PATH 2: Affect Leave Balance
    # ----------------------------------
    if rule.affect_leave_balance:
        existing_deductions = frappe.db.count(
            "Leave Deduction Log",
            {
                "employee": employee,
                "rule": rule.name,
                "month": month_key,
                "docstatus": 1,
            },
        )

        to_create = required_deductions - existing_deductions
        if to_create <= 0:
            return

        # Fetch leave priorities from child table
        priorities = frappe.db.sql(
            """
            SELECT leave_type, priority
            FROM `tabLeave Priority`
            WHERE parent = %s
            AND parenttype = 'Leave Rule'
            ORDER BY COALESCE(priority, 9999)
            """,
            (rule.name,),
            as_dict=True,
        )

        if not priorities:
            frappe.log_error(f"No leave priority found for rule {rule.name}", "Leave Rule Warning")

        for _ in range(to_create):
            remaining_to_deduct = deduction_unit

            # Deduct from each leave type in order
            for row in priorities:
                leave_type = row.leave_type
                if not leave_type or remaining_to_deduct <= 0:
                    continue

                leave_balance = get_leave_balance_on(employee=employee, leave_type=leave_type, date=att_date)

                if leave_balance <= 0:
                    continue

                # Deduct only up to available balance
                deduction_now = min(leave_balance, remaining_to_deduct)

                leave_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": employee,
                    "leave_type": leave_type,
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": deduction_now,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                leave_log.insert(ignore_permissions=True)
                leave_log.submit()

                remaining_to_deduct -= deduction_now

                if remaining_to_deduct <= 0:
                    break

            # Fallback to LWP if leave exhausted
            if remaining_to_deduct > 0:
                lwp_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": employee,
                    "leave_type": "Leave Without Pay",
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": remaining_to_deduct,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                lwp_log.insert(ignore_permissions=True)
                lwp_log.submit()


def check_daily_hours_fulfilment(attendance, rule):
    """Hook: Runs on Attendance submit. Enforces minimum daily working hours."""
    employee = attendance.employee
    att_date = getdate(attendance.attendance_date)
    month_start = get_first_day(att_date)
    month_key = month_start.strftime("%Y-%m")
    deduction_unit = flt(rule.deduction_unit or 1)

    worked = attendance.working_hours or 0
    shortfall = max(0, rule.min_hours_required - worked)

    # If requirement met, skip
    if shortfall <= 0:
        return

    # -------------------------------
    # Count total violations this month
    # -------------------------------
    total_violations = frappe.db.count(
        "Attendance",
        {
            "employee": employee,
            "docstatus": 1,
            "attendance_date": ("between", [month_start, att_date]),
            "working_hours": ("<", rule.min_hours_required),
        },
    )

    if total_violations < rule.violations:
        return  # Threshold not reached yet

    # -------------------------------
    # Calculate required vs existing deductions
    # -------------------------------
    required_deductions = total_violations // rule.violations

    # ----------------------------------
    # PATH 1: Payroll Direct Deduction
    # ----------------------------------
    if rule.affect_payroll_directly:
        existing_deductions = frappe.db.count(
            "Payroll Deduction Log",
            {"employee": employee, "rule": rule.name, "month": month_key, "docstatus": 1},
        )

        to_create = required_deductions - existing_deductions
        if to_create <= 0:
            return

        for _ in range(to_create):
            log = frappe.get_doc({
                "doctype": "Payroll Deduction Log",
                "employee": employee,
                "rule": rule.name,
                "month": month_key,
                "deduction_days": 1,
                "deduction_unit": deduction_unit,
                "reference_doctype": "Attendance",
                "reference_name": attendance.name,
            })
            log.insert(ignore_permissions=True)
            log.submit()

    # ----------------------------------
    # PATH 2: Affect Leave Balance
    # ----------------------------------
    if rule.affect_leave_balance:
        existing_deductions = frappe.db.count(
            "Leave Deduction Log",
            {"employee": employee, "rule": rule.name, "month": month_key, "docstatus": 1},
        )

        to_create = required_deductions - existing_deductions
        if to_create <= 0:
            return

        # Fetch Leave Priorities
        priorities = frappe.db.sql(
            """
            SELECT leave_type, priority
            FROM `tabLeave Priority`
            WHERE parent = %s
            AND parenttype = 'Leave Rule'
            ORDER BY COALESCE(priority, 9999)
            """,
            (rule.name,),
            as_dict=True
        )

        if not priorities:
            frappe.log_error(f"No leave priority found for rule {rule.name}", "Leave Rule Warning")

        for _ in range(to_create):
            remaining = deduction_unit  # total units to deduct for this violation set

            for row in priorities:
                leave_type = row.leave_type
                if not leave_type:
                    continue

                balance = get_leave_balance_on(employee=employee, leave_type=leave_type, date=att_date)

                if balance <= 0:
                    continue

                deduct_amount = min(remaining, balance)
                if deduct_amount <= 0:
                    continue

                # Create partial log for this leave type
                leave_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": employee,
                    "leave_type": leave_type,
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": deduct_amount,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                leave_log.insert(ignore_permissions=True)
                leave_log.submit()

                remaining -= deduct_amount
                if remaining <= 0:
                    break  # done fully

            # Fallback: Deduct remaining as Leave Without Pay
            if remaining > 0:
                lwp_log = frappe.get_doc({
                    "doctype": "Leave Deduction Log",
                    "employee": employee,
                    "leave_type": "Leave Without Pay",
                    "rule": rule.name,
                    "month": month_key,
                    "deduction_unit": remaining,
                    "reference_doctype": "Attendance",
                    "reference_name": attendance.name,
                })
                lwp_log.insert(ignore_permissions=True)
                lwp_log.submit()