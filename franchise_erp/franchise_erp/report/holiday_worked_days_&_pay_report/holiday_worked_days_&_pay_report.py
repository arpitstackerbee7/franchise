import frappe

from frappe import _
from frappe.utils import flt, getdate


# =========================================================
# EXECUTE
# =========================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()

    data = get_data(filters)

    return columns, data


# =========================================================
# VALIDATE FILTERS
# =========================================================

def validate_filters(filters):

    if not filters.get("holiday_list"):
        frappe.throw(
            _("Please select Holiday List.")
        )

    holiday_list = frappe.db.get_value(
        "Holiday List",
        filters.holiday_list,
        [
            "from_date",
            "to_date"
        ],
        as_dict=True
    )

    if not holiday_list:
        frappe.throw(
            _("Invalid Holiday List.")
        )

    if not holiday_list.from_date:
        frappe.throw(
            _("From Date is missing in Holiday List.")
        )

    if not holiday_list.to_date:
        frappe.throw(
            _("To Date is missing in Holiday List.")
        )

    # Always use Holiday List dates
    filters.from_date = holiday_list.from_date
    filters.to_date = holiday_list.to_date


# =========================================================
# COLUMNS
# =========================================================

def get_columns():

    return [

        {
            "label": _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },

        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 180,
        },

        {
            "label": _("Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 110,
        },

        {
            "label": _("In Time"),
            "fieldname": "in_time",
            "fieldtype": "Datetime",
            "width": 150,
        },

        {
            "label": _("Out Time"),
            "fieldname": "out_time",
            "fieldtype": "Datetime",
            "width": 150,
        },

        {
            "label": _("Standard Working Hours"),
            "fieldname": "standard_working_hours",
            "fieldtype": "Float",
            "width": 150,
        },

        {
            "label": _("Actual Hours"),
            "fieldname": "actual_hours",
            "fieldtype": "Float",
            "width": 110,
        },

        {
            "label": _("Extra Working Hours"),
            "fieldname": "extra_working_hours",
            "fieldtype": "Float",
            "width": 140,
        },

        {
            "label": _("Standard Status"),
            "fieldname": "standard_status",
            "fieldtype": "Data",
            "width": 130,
        },

        {
            "label": _("Holiday Name"),
            "fieldname": "holiday_name",
            "fieldtype": "Data",
            "width": 180,
        },

        {
            "label": _("Per Day Salary"),
            "fieldname": "per_day_salary",
            "fieldtype": "Currency",
            "width": 130,
        },

        {
            "label": _("Holiday Pay (2x)"),
            "fieldname": "holiday_pay",
            "fieldtype": "Currency",
            "width": 140,
        },
    ]


# =========================================================
# GET DATA
# =========================================================

def get_data(filters):

    # =====================================================
    # GET HOLIDAY LIST
    # =====================================================

    holiday_list = frappe.get_doc(
        "Holiday List",
        filters.holiday_list
    )

    # =====================================================
    # CREATE HOLIDAY DATE MAP
    # =====================================================

    holiday_dates = {}

    for holiday in holiday_list.holidays:

        if not holiday.holiday_date:
            continue

        holiday_date = getdate(
            holiday.holiday_date
        )

        if (
            holiday_date >= getdate(filters.from_date)
            and
            holiday_date <= getdate(filters.to_date)
        ):

            holiday_dates[holiday_date] = (
                holiday.description
                or holiday_list.name
            )

    if not holiday_dates:
        return []

    # =====================================================
    # EMPLOYEE FILTERS
    # =====================================================

    employee_filters = {
        "holiday_list": filters.holiday_list,
        "status": "Active",
    }

    # =====================================================
    # IMPORTANT
    # Only apply employee filter when value exists
    # =====================================================

    selected_employee = (
        filters.get("employee") or ""
    )

    selected_employee = str(
        selected_employee
    ).strip()

    if selected_employee:
        employee_filters["name"] = selected_employee

    # =====================================================
    # GET EMPLOYEES
    # =====================================================

    employees = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name",
            "employee_name",
            "holiday_list",
        ],
    )

    if not employees:
        return []

    # =====================================================
    # EMPLOYEE NAMES
    # =====================================================

    employee_names = [
        emp.name
        for emp in employees
    ]

    # =====================================================
    # EMPLOYEE MAP
    # =====================================================

    employee_map = {
        emp.name: emp
        for emp in employees
    }

    # =====================================================
    # ATTENDANCE FILTERS
    # =====================================================

    attendance_filters = {

        "employee": [
            "in",
            employee_names
        ],

        "attendance_date": [
            "between",
            [
                filters.from_date,
                filters.to_date
            ]
        ],

        "docstatus": 1,

        "status": "Present",
    }

    # =====================================================
    # GET ATTENDANCE
    # =====================================================

    attendance_records = frappe.get_all(
        "Attendance",

        filters=attendance_filters,

        fields=[
            "name",
            "employee",
            "attendance_date",
            "in_time",
            "out_time",
            "working_hours",
            "status",
        ],

        order_by="attendance_date asc",
    )

    if not attendance_records:
        return []

    # =====================================================
    # SALARY CACHE
    # =====================================================

    salary_cache = {}

    data = []

    # =====================================================
    # PROCESS ATTENDANCE
    # =====================================================

    for attendance in attendance_records:

        attendance_date = getdate(
            attendance.attendance_date
        )

        # -------------------------------------------------
        # Only Holiday Attendance
        # -------------------------------------------------

        if attendance_date not in holiday_dates:
            continue

        # -------------------------------------------------
        # Employee
        # -------------------------------------------------

        employee = employee_map.get(
            attendance.employee
        )

        if not employee:
            continue

        # =================================================
        # STANDARD WORKING HOURS
        # =================================================

        standard_working_hours = 8

        # =================================================
        # ACTUAL HOURS
        # From Attendance.working_hours
        # =================================================

        actual_hours = flt(
            attendance.working_hours
        )

        # =================================================
        # EXTRA WORKING HOURS
        # =================================================

        extra_working_hours = max(
            actual_hours - standard_working_hours,
            0
        )

        # =================================================
        # GET SALARY
        # =================================================

        salary_details = get_employee_salary(
            employee=attendance.employee,
            attendance_date=attendance_date,
            salary_cache=salary_cache,
        )

        # =================================================
        # PER DAY SALARY
        # =================================================

        per_day_salary = flt(
            salary_details.get(
                "per_day_salary",
                0
            )
        )

        # =================================================
        # HOLIDAY PAY
        # =================================================

        holiday_pay = (
            per_day_salary * 2
        )

        # =================================================
        # ADD ROW
        # =================================================

        data.append({

            "employee":
                attendance.employee,

            "employee_name":
                employee.employee_name,

            "attendance_date":
                attendance.attendance_date,

            "in_time":
                attendance.in_time,

            "out_time":
                attendance.out_time,

            "standard_working_hours":
                standard_working_hours,

            "actual_hours":
                actual_hours,

            "extra_working_hours":
                extra_working_hours,

            "standard_status":
                attendance.status,

            "holiday_name":
                holiday_dates[
                    attendance_date
                ],

            "per_day_salary":
                per_day_salary,

            "holiday_pay":
                holiday_pay,
        })

    return data


# =========================================================
# GET EMPLOYEE SALARY
# =========================================================

def get_employee_salary(
    employee,
    attendance_date,
    salary_cache
):

    # =====================================================
    # CACHE KEY
    # =====================================================

    cache_key = (
        f"{employee}:{attendance_date}"
    )

    if cache_key in salary_cache:
        return salary_cache[cache_key]

    # =====================================================
    # SALARY STRUCTURE ASSIGNMENT
    # =====================================================

    assignment = frappe.get_all(
        "Salary Structure Assignment",

        filters={
            "employee": employee,

            "from_date": [
                "<=",
                attendance_date
            ],

            "docstatus": 1,
        },

        fields=[
            "name",
            "salary_structure",
            "from_date",
        ],

        order_by="from_date desc",

        limit=1,
    )

    # =====================================================
    # NO ASSIGNMENT
    # =====================================================

    if not assignment:

        result = {
            "earnings": 0,
            "deductions": 0,
            "per_day_salary": 0,
        }

        salary_cache[cache_key] = result

        return result

    # =====================================================
    # SALARY STRUCTURE
    # =====================================================

    salary_structure_name = (
        assignment[0].salary_structure
    )

    if not salary_structure_name:

        result = {
            "earnings": 0,
            "deductions": 0,
            "per_day_salary": 0,
        }

        salary_cache[cache_key] = result

        return result

    # =====================================================
    # GET SALARY STRUCTURE
    # =====================================================

    salary_structure = frappe.get_doc(
        "Salary Structure",
        salary_structure_name
    )

    # =====================================================
    # EARNINGS
    # =====================================================

    total_earnings = 0

    for earning in salary_structure.earnings:

        total_earnings += flt(
            earning.amount
        )

    # =====================================================
    # DEDUCTIONS
    # =====================================================

    total_deductions = 0

    for deduction in salary_structure.deductions:

        total_deductions += flt(
            deduction.amount
        )

    # =====================================================
    # NET SALARY
    # =====================================================

    net_salary = (
        total_earnings
        - total_deductions
    )

    # =====================================================
    # PER DAY SALARY
    # =====================================================

    per_day_salary = (
        net_salary / 30
    )

    # =====================================================
    # RESULT
    # =====================================================

    result = {
        "earnings": total_earnings,
        "deductions": total_deductions,
        "per_day_salary": per_day_salary,
    }

    # =====================================================
    # CACHE
    # =====================================================

    salary_cache[cache_key] = result

    return result