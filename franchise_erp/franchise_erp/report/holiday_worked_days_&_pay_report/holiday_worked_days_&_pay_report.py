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

    # -----------------------------------------------------
    # Always take dates from Holiday List
    # -----------------------------------------------------

    filters.from_date = holiday_list.from_date
    filters.to_date = holiday_list.to_date

    if not filters.from_date:
        frappe.throw(
            _("From Date is missing in Holiday List.")
        )

    if not filters.to_date:
        frappe.throw(
            _("To Date is missing in Holiday List.")
        )


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
            "label": _("Total Earnings"),
            "fieldname": "total_earnings",
            "fieldtype": "Currency",
            "width": 130,
        },

        {
            "label": _("Total Deductions"),
            "fieldname": "total_deductions",
            "fieldtype": "Currency",
            "width": 140,
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
    # Get Holiday List
    # =====================================================

    holiday_list = frappe.get_doc(
        "Holiday List",
        filters.holiday_list
    )

    # =====================================================
    # Create Holiday Date Map
    # =====================================================

    holiday_dates = {}

    for holiday in holiday_list.holidays:

        holiday_date = getdate(
            holiday.holiday_date
        )

        if (
            holiday_date >= getdate(filters.from_date)
            and
            holiday_date <= getdate(filters.to_date)
        ):

            holiday_name = (
                holiday.description
                or holiday_list.name
            )

            holiday_dates[holiday_date] = holiday_name

    # No holidays found
    if not holiday_dates:
        return []

    # =====================================================
    # Get Employees
    # =====================================================

    employee_filters = {
        "holiday_list": filters.holiday_list,
        "status": "Active",
    }

    # -----------------------------------------------------
    # If Employee filter is selected
    # only that employee will be processed
    # -----------------------------------------------------

    if filters.get("employee"):
        employee_filters["name"] = filters.employee

    employees = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name",
            "employee_name",
            "holiday_list",
        ],
    )

    # No employees found
    if not employees:
        return []

    # =====================================================
    # Employee Names
    # =====================================================

    employee_names = [
        employee.name
        for employee in employees
    ]

    # =====================================================
    # Employee Map
    # =====================================================

    employee_map = {
        employee.name: employee
        for employee in employees
    }

    # =====================================================
    # Attendance Filters
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
    # Get Attendance
    #
    # Attendance.working_hours
    # will be displayed as Actual Hours
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

    # No attendance
    if not attendance_records:
        return []

    # =====================================================
    # Salary Cache
    # =====================================================

    salary_cache = {}

    # =====================================================
    # Report Data
    # =====================================================

    data = []

    # =====================================================
    # Process Attendance
    # =====================================================

    for attendance in attendance_records:

        attendance_date = getdate(
            attendance.attendance_date
        )

        # -------------------------------------------------
        # Check Whether Attendance Date Is Holiday
        # -------------------------------------------------

        if attendance_date not in holiday_dates:
            continue

        # -------------------------------------------------
        # Get Employee
        # -------------------------------------------------

        employee = employee_map.get(
            attendance.employee
        )

        if not employee:
            continue

        # -------------------------------------------------
        # Standard Working Hours
        # -------------------------------------------------

        standard_working_hours = 8

        # -------------------------------------------------
        # Actual Hours
        #
        # Attendance working_hours
        # -------------------------------------------------

        actual_hours = flt(
            attendance.working_hours
        )

        # -------------------------------------------------
        # Extra Working Hours
        # -------------------------------------------------

        extra_working_hours = max(
            actual_hours - standard_working_hours,
            0
        )

        # -------------------------------------------------
        # Get Employee Salary
        # -------------------------------------------------

        salary_details = get_employee_salary(
            employee=attendance.employee,
            attendance_date=attendance_date,
            salary_cache=salary_cache,
        )

        # -------------------------------------------------
        # Salary Values
        # -------------------------------------------------

        total_earnings = flt(
            salary_details.get("earnings", 0)
        )

        total_deductions = flt(
            salary_details.get("deductions", 0)
        )

        per_day_salary = flt(
            salary_details.get("per_day_salary", 0)
        )

        # -------------------------------------------------
        # Double Holiday Pay
        # -------------------------------------------------

        holiday_pay = per_day_salary * 2

        # -------------------------------------------------
        # Add Report Row
        # -------------------------------------------------

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
                holiday_dates[attendance_date],

            "total_earnings":
                total_earnings,

            "total_deductions":
                total_deductions,

            "per_day_salary":
                per_day_salary,

            "holiday_pay":
                holiday_pay,
        })

    # =====================================================
    # Return Data
    # =====================================================

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
    # Cache Key
    # =====================================================

    cache_key = (
        f"{employee}:{attendance_date}"
    )

    # -----------------------------------------------------
    # Return Cached Result
    # -----------------------------------------------------

    if cache_key in salary_cache:

        return salary_cache[cache_key]

    # =====================================================
    # Get Applicable Salary Structure Assignment
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
    # No Salary Assignment
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
    # Get Salary Structure Name
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
    # Get Salary Structure
    # =====================================================

    salary_structure = frappe.get_doc(
        "Salary Structure",
        salary_structure_name
    )

    # =====================================================
    # Calculate Total Earnings
    # =====================================================

    total_earnings = 0

    for earning in salary_structure.earnings:

        total_earnings += flt(
            earning.amount
        )

    # =====================================================
    # Calculate Total Deductions
    # =====================================================

    total_deductions = 0

    for deduction in salary_structure.deductions:

        total_deductions += flt(
            deduction.amount
        )

    # =====================================================
    # Net Salary
    # =====================================================

    net_salary = (
        total_earnings
        -
        total_deductions
    )

    # =====================================================
    # Per Day Salary
    # =====================================================

    per_day_salary = (
        net_salary / 30
    )

    # =====================================================
    # Result
    # =====================================================

    result = {

        "earnings":
            total_earnings,

        "deductions":
            total_deductions,

        "per_day_salary":
            per_day_salary,
    }

    # =====================================================
    # Save In Cache
    # =====================================================

    salary_cache[cache_key] = result

    return result