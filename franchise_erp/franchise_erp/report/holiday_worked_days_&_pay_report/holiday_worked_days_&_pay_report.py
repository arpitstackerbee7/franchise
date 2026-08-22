import frappe

from frappe import _
from frappe.utils import flt, getdate, get_time


# =========================================================
# EXECUTE
# =========================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    # -----------------------------------------------------
    # Validate Filters
    # -----------------------------------------------------

    validate_filters(filters)

    # -----------------------------------------------------
    # Columns
    # -----------------------------------------------------

    columns = get_columns()

    # -----------------------------------------------------
    # Data
    # -----------------------------------------------------

    data = get_data(filters)

    return columns, data


# =========================================================
# VALIDATE FILTERS
# =========================================================

def validate_filters(filters):

    # =====================================================
    # FROM DATE
    # =====================================================

    if not filters.get("from_date"):
        frappe.throw(
            _("Please select From Date.")
        )

    # =====================================================
    # TO DATE
    # =====================================================

    if not filters.get("to_date"):
        frappe.throw(
            _("Please select To Date.")
        )

    # =====================================================
    # CONVERT DATES
    # =====================================================

    from_date = getdate(
        filters.from_date
    )

    to_date = getdate(
        filters.to_date
    )

    # =====================================================
    # VALIDATE DATE RANGE
    # =====================================================

    if from_date > to_date:

        frappe.throw(
            _("From Date cannot be greater than To Date.")
        )

    # =====================================================
    # SAVE DATE VALUES
    # =====================================================

    filters.from_date = from_date
    filters.to_date = to_date

    # =====================================================
    # HOLIDAY LIST OPTIONAL
    # =====================================================

    holiday_list = (
        filters.get("holiday_list") or ""
    )

    filters.holiday_list = str(
        holiday_list
    ).strip()

    # =====================================================
    # EMPLOYEE OPTIONAL
    # =====================================================

    employee = (
        filters.get("employee") or ""
    )

    filters.employee = str(
        employee
    ).strip()


# =========================================================
# COLUMNS
# =========================================================

def get_columns():

    return [

        # -------------------------------------------------
        # Employee
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Attendance Date
        # -------------------------------------------------

        {
            "label": _("Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 110,
        },

        # -------------------------------------------------
        # Shift
        # -------------------------------------------------

        {
            "label": _("Shift Type"),
            "fieldname": "shift_type",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 150,
        },

        {
            "label": _("Shift Start Time"),
            "fieldname": "shift_start_time",
            "fieldtype": "Time",
            "width": 130,
        },

        {
            "label": _("Shift End Time"),
            "fieldname": "shift_end_time",
            "fieldtype": "Time",
            "width": 130,
        },

        # -------------------------------------------------
        # Attendance Time
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Working Hours
        # -------------------------------------------------

        {
            "label": _("Standard Working Hours"),
            "fieldname": "standard_working_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 160,
        },

        {
            "label": _("Actual Hours"),
            "fieldname": "actual_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 110,
        },

        {
            "label": _("Extra Working Hours"),
            "fieldname": "extra_working_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        {
            "label": _("Status"),
            "fieldname": "standard_status",
            "fieldtype": "Data",
            "width": 120,
        },

        # -------------------------------------------------
        # Holiday
        # -------------------------------------------------

        {
            "label": _("Holiday Name"),
            "fieldname": "holiday_name",
            "fieldtype": "Data",
            "width": 180,
        },

        # -------------------------------------------------
        # Salary
        # -------------------------------------------------

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
    # EMPLOYEE FILTERS
    # =====================================================

    employee_filters = {
        "status": "Active",
    }

    # -----------------------------------------------------
    # If Employee selected
    # -----------------------------------------------------

    if filters.employee:

        employee_filters["name"] = (
            filters.employee
        )

    # -----------------------------------------------------
    # If Holiday List selected
    # -----------------------------------------------------
    # Only employees belonging to that Holiday List
    # -----------------------------------------------------

    if filters.holiday_list:

        employee_filters["holiday_list"] = (
            filters.holiday_list
        )

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

        order_by="name asc",
    )

    # -----------------------------------------------------
    # No Employees
    # -----------------------------------------------------

    if not employees:
        return []

    # =====================================================
    # EMPLOYEE NAMES
    # =====================================================

    employee_names = [
        employee.name
        for employee in employees
    ]

    # =====================================================
    # EMPLOYEE MAP
    # =====================================================

    employee_map = {

        employee.name:
            employee

        for employee in employees

    }

    # =====================================================
    # HOLIDAY DATE MAP
    # =====================================================
    #
    # IMPORTANT:
    #
    # If Holiday List selected:
    #     Use selected Holiday List.
    #
    # If Holiday List blank:
    #     Use each employee's own Holiday List.
    #
    # Structure:
    #
    # {
    #     employee_name: {
    #         date: holiday_name
    #     }
    # }
    #
    # =====================================================

    holiday_dates_by_employee = {}

    # =====================================================
    # HOLIDAY LIST CACHE
    # =====================================================

    holiday_cache = {}

    # =====================================================
    # BUILD HOLIDAY MAP
    # =====================================================

    for employee in employees:

        # -------------------------------------------------
        # Determine Holiday List
        # -------------------------------------------------

        if filters.holiday_list:

            employee_holiday_list = (
                filters.holiday_list
            )

        else:

            employee_holiday_list = (
                employee.holiday_list
            )

        # -------------------------------------------------
        # No Holiday List
        # -------------------------------------------------

        if not employee_holiday_list:

            holiday_dates_by_employee[
                employee.name
            ] = {}

            continue

        # -------------------------------------------------
        # Cache Holiday List
        # -------------------------------------------------

        if (
            employee_holiday_list
            not in holiday_cache
        ):

            holiday_doc = frappe.get_doc(
                "Holiday List",
                employee_holiday_list
            )

            holiday_map = {}

            for holiday in holiday_doc.holidays:

                if not holiday.holiday_date:
                    continue

                holiday_date = getdate(
                    holiday.holiday_date
                )

                # -----------------------------------------
                # Selected Date Range
                # -----------------------------------------

                if (

                    holiday_date
                    >= getdate(filters.from_date)

                    and

                    holiday_date
                    <= getdate(filters.to_date)

                ):

                    holiday_name = (

                        holiday.description

                        or holiday_doc.name
                    )

                    holiday_map[
                        holiday_date
                    ] = holiday_name

            holiday_cache[
                employee_holiday_list
            ] = holiday_map

        # -------------------------------------------------
        # Assign employee holiday map
        # -------------------------------------------------

        holiday_dates_by_employee[
            employee.name
        ] = holiday_cache[
            employee_holiday_list
        ]

    # =====================================================
    # GET ATTENDANCE
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
    # GET ATTENDANCE RECORDS
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
            "shift",
        ],

        order_by="attendance_date asc",
    )

    # -----------------------------------------------------
    # No Attendance
    # -----------------------------------------------------

    if not attendance_records:
        return []

    # =====================================================
    # SALARY CACHE
    # =====================================================

    salary_cache = {}

    # =====================================================
    # SHIFT CACHE
    # =====================================================

    shift_cache = {}

    # =====================================================
    # REPORT DATA
    # =====================================================

    data = []

    # =====================================================
    # PROCESS ATTENDANCE
    # =====================================================

    for attendance in attendance_records:

        # -------------------------------------------------
        # Attendance Date
        # -------------------------------------------------

        attendance_date = getdate(
            attendance.attendance_date
        )

        # -------------------------------------------------
        # Employee
        # -------------------------------------------------

        employee = employee_map.get(
            attendance.employee
        )

        if not employee:
            continue

        # =================================================
        # CHECK HOLIDAY
        # =================================================

        employee_holidays = (
            holiday_dates_by_employee.get(
                attendance.employee,
                {}
            )
        )

        # -------------------------------------------------
        # Only show attendance on holiday
        # -------------------------------------------------

        if attendance_date not in employee_holidays:

            continue

        # =================================================
        # SHIFT INFORMATION
        # =================================================

        shift_type = (
            attendance.shift
        )

        shift_start_time = None
        shift_end_time = None

        standard_working_hours = 0

        # -------------------------------------------------
        # Get Shift Type
        # -------------------------------------------------

        if shift_type:

            if shift_type not in shift_cache:

                shift_cache[
                    shift_type
                ] = frappe.db.get_value(

                    "Shift Type",

                    shift_type,

                    [
                        "start_time",
                        "end_time",
                    ],

                    as_dict=True,
                )

            shift = shift_cache.get(
                shift_type
            )

            if shift:

                shift_start_time = (
                    shift.start_time
                )

                shift_end_time = (
                    shift.end_time
                )

                standard_working_hours = (
                    calculate_shift_hours(
                        shift_start_time,
                        shift_end_time
                    )
                )

        # =================================================
        # ACTUAL HOURS
        # =================================================
        #
        # ERPNext Attendance.working_hours
        # is decimal hours.
        #
        # Example:
        #
        # 10.166666
        #
        # means:
        #
        # 10 hours 10 minutes
        #
        # Convert it to:
        #
        # 10.10
        #
        # =================================================

        actual_minutes = (
            decimal_hours_to_minutes(
                attendance.working_hours
            )
        )

        actual_hours = (
            minutes_to_hhmm_decimal(
                actual_minutes
            )
        )

        # =================================================
        # EXTRA WORKING HOURS
        # =================================================

        standard_minutes = (
            hhmm_decimal_to_minutes(
                standard_working_hours
            )
        )

        extra_minutes = max(

            actual_minutes
            -
            standard_minutes,

            0
        )

        extra_working_hours = (
            minutes_to_hhmm_decimal(
                extra_minutes
            )
        )

        # =================================================
        # GET EMPLOYEE SALARY
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
        # ADD REPORT ROW
        # =================================================

        data.append({

            # ---------------------------------------------
            # Employee
            # ---------------------------------------------

            "employee":
                attendance.employee,

            "employee_name":
                employee.employee_name,

            # ---------------------------------------------
            # Date
            # ---------------------------------------------

            "attendance_date":
                attendance.attendance_date,

            # ---------------------------------------------
            # Shift
            # ---------------------------------------------

            "shift_type":
                shift_type,

            "shift_start_time":
                shift_start_time,

            "shift_end_time":
                shift_end_time,

            # ---------------------------------------------
            # Attendance Time
            # ---------------------------------------------

            "in_time":
                attendance.in_time,

            "out_time":
                attendance.out_time,

            # ---------------------------------------------
            # Working Hours
            # ---------------------------------------------

            "standard_working_hours":
                standard_working_hours,

            "actual_hours":
                actual_hours,

            "extra_working_hours":
                extra_working_hours,

            # ---------------------------------------------
            # Status
            # ---------------------------------------------

            "standard_status":
                attendance.status,

            # ---------------------------------------------
            # Holiday
            # ---------------------------------------------

            "holiday_name":
                employee_holidays[
                    attendance_date
                ],

            # ---------------------------------------------
            # Salary
            # ---------------------------------------------

            "per_day_salary":
                per_day_salary,

            "holiday_pay":
                holiday_pay,
        })

    # =====================================================
    # RETURN DATA
    # =====================================================

    return data


# =========================================================
# CALCULATE SHIFT HOURS
# =========================================================
#
# 09:30 -> 19:40
#
# Total:
# 10 hours 10 minutes
#
# Return:
# 10.10
#
# NOT:
# 10.166
#
# =========================================================

def calculate_shift_hours(
    start_time,
    end_time
):

    if not start_time or not end_time:
        return 0

    start = get_time(
        start_time
    )

    end = get_time(
        end_time
    )

    # -----------------------------------------------------
    # Start minutes
    # -----------------------------------------------------

    start_minutes = (

        start.hour * 60

        +

        start.minute
    )

    # -----------------------------------------------------
    # End minutes
    # -----------------------------------------------------

    end_minutes = (

        end.hour * 60

        +

        end.minute
    )

    # -----------------------------------------------------
    # Night Shift
    # -----------------------------------------------------

    if end_minutes < start_minutes:

        end_minutes += (
            24 * 60
        )

    # -----------------------------------------------------
    # Total Minutes
    # -----------------------------------------------------

    total_minutes = (

        end_minutes
        -
        start_minutes
    )

    # -----------------------------------------------------
    # Convert Minutes -> HH.MM
    # -----------------------------------------------------

    return minutes_to_hhmm_decimal(
        total_minutes
    )


# =========================================================
# DECIMAL HOURS -> MINUTES
# =========================================================
#
# Example:
#
# 10.166666 hours
#
# = 610 minutes
#
# =========================================================

def decimal_hours_to_minutes(
    decimal_hours
):

    decimal_hours = flt(
        decimal_hours
    )

    return int(
        round(
            decimal_hours * 60
        )
    )


# =========================================================
# MINUTES -> HH.MM
# =========================================================
#
# Example:
#
# 610 minutes
#
# = 10 hours
# = 10 minutes
#
# Return:
# 10.10
#
# =========================================================

def minutes_to_hhmm_decimal(
    total_minutes
):

    total_minutes = int(
        round(total_minutes)
    )

    hours = (
        total_minutes // 60
    )

    minutes = (
        total_minutes % 60
    )

    return float(
        f"{hours}.{minutes:02d}"
    )


# =========================================================
# HH.MM -> MINUTES
# =========================================================
#
# IMPORTANT:
#
# 10.10 is NOT decimal 10.10 hours.
#
# It means:
#
# 10 hours 10 minutes.
#
# =========================================================

def hhmm_decimal_to_minutes(
    value
):

    value = flt(value)

    hours = int(value)

    minutes = int(
        round(
            (value - hours) * 100
        )
    )

    # -----------------------------------------------------
    # Safety
    # -----------------------------------------------------

    if minutes >= 60:

        hours += (
            minutes // 60
        )

        minutes = (
            minutes % 60
        )

    return (
        hours * 60
        +
        minutes
    )


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

    # -----------------------------------------------------
    # Return cached result
    # -----------------------------------------------------

    if cache_key in salary_cache:

        return salary_cache[
            cache_key
        ]

    # =====================================================
    # GET SALARY STRUCTURE ASSIGNMENT
    # =====================================================

    assignment = frappe.get_all(

        "Salary Structure Assignment",

        filters={

            "employee":
                employee,

            "from_date": [
                "<=",
                attendance_date
            ],

            "docstatus":
                1,
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
            "per_day_salary": 0,
        }

        salary_cache[
            cache_key
        ] = result

        return result

    # =====================================================
    # SALARY STRUCTURE
    # =====================================================

    salary_structure_name = (
        assignment[0].salary_structure
    )

    if not salary_structure_name:

        result = {
            "per_day_salary": 0,
        }

        salary_cache[
            cache_key
        ] = result

        return result

    # =====================================================
    # GET SALARY STRUCTURE
    # =====================================================

    salary_structure = frappe.get_doc(

        "Salary Structure",

        salary_structure_name
    )

    # =====================================================
    # TOTAL EARNINGS
    # =====================================================

    total_earnings = 0

    for earning in (
        salary_structure.earnings
    ):

        total_earnings += flt(
            earning.amount
        )

    # =====================================================
    # TOTAL DEDUCTIONS
    # =====================================================

    total_deductions = 0

    for deduction in (
        salary_structure.deductions
    ):

        total_deductions += flt(
            deduction.amount
        )

    # =====================================================
    # NET SALARY
    # =====================================================

    net_salary = (

        total_earnings
        -
        total_deductions
    )

    # =====================================================
    # PER DAY SALARY
    # =====================================================

    per_day_salary = (

        net_salary
        /
        30
    )

    # =====================================================
    # RESULT
    # =====================================================

    result = {

        "per_day_salary":
            round(
                per_day_salary,
                2
            ),
    }

    # =====================================================
    # CACHE
    # =====================================================

    salary_cache[
        cache_key
    ] = result

    return result