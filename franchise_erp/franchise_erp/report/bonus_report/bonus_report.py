# import frappe

# MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# BONUS_COMPONENT = "Bonus"


# def execute(filters=None):
#     filters = filters or {}
#     columns = get_columns(filters)
#     data = get_data(filters)
#     return columns, data


# def get_columns(filters):
#     columns = [
#         {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
#         {"label": "Salary Structure", "fieldname": "salary_structure", "fieldtype": "Link", "options": "Salary Structure", "width": 130},
#     ]
#     selected_month = filters.get("month")
#     months_to_show = [selected_month] if selected_month else MONTH_ORDER

#     for month in months_to_show:
#         columns.append({
#             "label": f"{month}-PD",
#             "fieldname": f"{month.lower()}_pd",
#             "fieldtype": "Float",
#             "width": 80,
#             "precision": 2
#         })
#         columns.append({
#             "label": f"{month}-Bonus",
#             "fieldname": f"{month.lower()}_bonus",
#             "fieldtype": "Currency",
#             "width": 90
#         })

#     # Totals
#     columns.append({"label": "Total PD", "fieldname": "total_pd", "fieldtype": "Float", "width": 90, "precision": 2})
#     columns.append({"label": "Total Bonus", "fieldname": "total_bonus", "fieldtype": "Currency", "width": 110})

#     return columns


# def get_data(filters):
#     conditions = ["ss.docstatus = 1"]
#     values = {"bonus_component": BONUS_COMPONENT}

#     if filters.get("employee"):
#         conditions.append("ss.employee = %(employee)s")
#         values["employee"] = filters.get("employee")

#     if filters.get("salary_structure"):
#         conditions.append("ss.salary_structure = %(salary_structure)s")
#         values["salary_structure"] = filters.get("salary_structure")

#     if filters.get("department"):
#         conditions.append("emp.department = %(department)s")
#         values["department"] = filters.get("department")

#     if filters.get("month"):
#         conditions.append("DATE_FORMAT(ss.start_date, '%%b') = %(month)s")
#         values["month"] = filters.get("month")

#     condition_str = " AND ".join(conditions)

#     query = f"""
#         SELECT
#             ss.employee,
#             ss.employee_name,
#             ss.salary_structure,
#             ss.payment_days AS present_days,
#             DATE_FORMAT(ss.start_date, '%%b') AS month,
#             COALESCE(sd.amount, 0) AS monthly_bonus_amount,
#             CASE
#                 WHEN MONTH(ss.start_date) >= 4 THEN YEAR(ss.start_date)
#                 ELSE YEAR(ss.start_date) - 1
#             END AS bonus_year
#         FROM `tabSalary Slip` ss
#         LEFT JOIN `tabEmployee` emp ON emp.name = ss.employee
#         LEFT JOIN `tabSalary Detail` sd
#             ON sd.parent = ss.name
#             AND sd.parenttype = 'Salary Slip'
#             AND sd.parentfield IN ('earnings', 'deductions')
#             AND sd.salary_component = %(bonus_component)s
#         WHERE {condition_str}
#         ORDER BY ss.employee_name
#     """

#     raw_data = frappe.db.sql(query, values, as_dict=True)

#     if filters.get("bonus_year"):
#         raw_value = str(filters.get("bonus_year"))
#         target_year = int(raw_value.split("-")[0])
#         raw_data = [row for row in raw_data if row.bonus_year == target_year]

#     employee_map = {}

#     for row in raw_data:
#         emp = row.employee
#         if emp not in employee_map:
#             employee_map[emp] = {
#                 "employee": row.employee,
#                 "employee_name": row.employee_name,
#                 "salary_structure": row.salary_structure,
#                 "total_pd": 0,
#                 "total_bonus": 0,
#             }
#             for month in MONTH_ORDER:
#                 employee_map[emp][f"{month.lower()}_pd"] = 0
#                 employee_map[emp][f"{month.lower()}_bonus"] = 0

#         month_key = row.month.lower()
#         employee_map[emp][f"{month_key}_pd"] = row.present_days or 0
#         employee_map[emp][f"{month_key}_bonus"] = row.monthly_bonus_amount or 0
#         employee_map[emp]["total_pd"] += (row.present_days or 0)
#         employee_map[emp]["total_bonus"] += (row.monthly_bonus_amount or 0)

#     return list(employee_map.values())


# import frappe
# import calendar
# from datetime import datetime


# MONTH_ORDER = [
#     "Jan", "Feb", "Mar", "Apr", "May", "Jun",
#     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
# ]

# BONUS_COMPONENT = "Bonus"
# MONTHLY_BONUS = 7000
# BONUS_PERCENTAGE = 0.085


# def execute(filters=None):
#     filters = filters or {}

#     columns = get_columns(filters)
#     data = get_data(filters)

#     return columns, data


# def get_columns(filters):
#     columns = [
#         {
#             "label": "Employee",
#             "fieldname": "employee",
#             "fieldtype": "Link",
#             "options": "Employee",
#             "width": 120
#         },
#         {
#             "label": "Employee Name",
#             "fieldname": "employee_name",
#             "fieldtype": "Data",
#             "width": 150
#         },
#         {
#             "label": "Salary Structure",
#             "fieldname": "salary_structure",
#             "fieldtype": "Link",
#             "options": "Salary Structure",
#             "width": 130
#         }
#     ]

#     # ---------------------------------------------------------
#     # MONTHLY COLUMNS
#     # ---------------------------------------------------------

#     for month in MONTH_ORDER:

#         columns.append({
#             "label": f"{month}-PD",
#             "fieldname": f"{month.lower()}_pd",
#             "fieldtype": "Float",
#             "width": 80,
#             "precision": 2
#         })

#         columns.append({
#             "label": f"{month}-Bonus",
#             "fieldname": f"{month.lower()}_bonus",
#             "fieldtype": "Currency",
#             "width": 90,
#             "precision": 2
#         })

#     # ---------------------------------------------------------
#     # TOTAL COLUMNS
#     # ---------------------------------------------------------

#     columns.append({
#         "label": "Total PD",
#         "fieldname": "total_pd",
#         "fieldtype": "Float",
#         "width": 90,
#         "precision": 2
#     })

#     columns.append({
#         "label": "Total PDA",
#         "fieldname": "tpda",
#         "fieldtype": "Currency",
#         "width": 110,
#         "precision": 2
#     })

#     columns.append({
#         "label": "Total Bonus",
#         "fieldname": "total_bonus",
#         "fieldtype": "Currency",
#         "width": 110,
#         "precision": 2
#     })

#     return columns


# def get_data(filters):

#     # ---------------------------------------------------------
#     # CONDITIONS
#     # ---------------------------------------------------------

#     conditions = [
#         "ss.docstatus = 1"
#     ]

#     values = {
#         "bonus_component": BONUS_COMPONENT
#     }

#     # ---------------------------------------------------------
#     # EMPLOYEE FILTER
#     # ---------------------------------------------------------

#     if filters.get("employee"):
#         conditions.append(
#             "ss.employee = %(employee)s"
#         )

#         values["employee"] = filters.get("employee")

#     # ---------------------------------------------------------
#     # SALARY STRUCTURE FILTER
#     # ---------------------------------------------------------

#     if filters.get("salary_structure"):
#         conditions.append(
#             "ss.salary_structure = %(salary_structure)s"
#         )

#         values["salary_structure"] = filters.get(
#             "salary_structure"
#         )

#     # ---------------------------------------------------------
#     # DEPARTMENT FILTER
#     # ---------------------------------------------------------

#     if filters.get("department"):
#         conditions.append(
#             "emp.department = %(department)s"
#         )

#         values["department"] = filters.get(
#             "department"
#         )

#     # ---------------------------------------------------------
#     # FROM DATE
#     # ---------------------------------------------------------

#     if filters.get("from_date"):
#         conditions.append(
#             "ss.start_date >= %(from_date)s"
#         )

#         values["from_date"] = filters.get(
#             "from_date"
#         )

#     # ---------------------------------------------------------
#     # TO DATE
#     # ---------------------------------------------------------

#     if filters.get("to_date"):
#         conditions.append(
#             "ss.start_date <= %(to_date)s"
#         )

#         values["to_date"] = filters.get(
#             "to_date"
#         )

#     condition_str = " AND ".join(conditions)

#     # ---------------------------------------------------------
#     # SALARY SLIP DATA
#     # ---------------------------------------------------------

#     query = f"""
#         SELECT
#             ss.employee,
#             ss.employee_name,
#             ss.salary_structure,
#             ss.payment_days AS present_days,
#             ss.start_date,
#             DATE_FORMAT(ss.start_date, '%%b') AS month

#         FROM `tabSalary Slip` ss

#         LEFT JOIN `tabEmployee` emp
#             ON emp.name = ss.employee

#         WHERE {condition_str}

#         ORDER BY
#             ss.employee_name,
#             ss.start_date
#     """

#     raw_data = frappe.db.sql(
#         query,
#         values,
#         as_dict=True
#     )

#     employee_map = {}

#     # =========================================================
#     # PROCESS SALARY SLIPS
#     # =========================================================

#     for row in raw_data:

#         emp = row.employee

#         # -----------------------------------------------------
#         # INITIALIZE EMPLOYEE
#         # -----------------------------------------------------

#         if emp not in employee_map:

#             employee_map[emp] = {
#                 "employee": row.employee,
#                 "employee_name": row.employee_name,
#                 "salary_structure": row.salary_structure,

#                 "total_pd": 0,
#                 "tpda": 0,
#                 "total_bonus": 0,
#             }

#             # Initialize all months
#             for month in MONTH_ORDER:

#                 month_key = month.lower()

#                 employee_map[emp][
#                     f"{month_key}_pd"
#                 ] = 0

#                 employee_map[emp][
#                     f"{month_key}_bonus"
#                 ] = 0

#         # -----------------------------------------------------
#         # MONTH
#         # -----------------------------------------------------

#         month_key = row.month.lower()

#         # -----------------------------------------------------
#         # GET START DATE
#         # -----------------------------------------------------

#         start_date = row.start_date

#         if isinstance(start_date, str):

#             start_date = datetime.strptime(
#                 start_date,
#                 "%Y-%m-%d"
#             )

#         year = start_date.year
#         month_number = start_date.month

#         # -----------------------------------------------------
#         # ACTUAL DAYS IN MONTH
#         #
#         # Jan = 31
#         # Feb = 28 / 29
#         # Apr = 30
#         # etc.
#         # -----------------------------------------------------

#         days_in_month = calendar.monthrange(
#             year,
#             month_number
#         )[1]

#         # -----------------------------------------------------
#         # PAYMENT DAYS
#         # -----------------------------------------------------

#         payment_days = float(
#             row.present_days or 0
#         )

#         # -----------------------------------------------------
#         # MONTHLY BONUS CALCULATION
#         #
#         # Full Month:
#         #     ₹7,000
#         #
#         # Partial Month:
#         #     ₹7,000 / Actual Month Days × PD
#         #
#         # Example:
#         # January:
#         # 31 PD = ₹7,000
#         # 30 PD = ₹6,774.19
#         #
#         # February:
#         # 28 PD = ₹7,000
#         # 27 PD = ₹6,750
#         #
#         # April:
#         # 30 PD = ₹7,000
#         # 29 PD = ₹6,766.67
#         # -----------------------------------------------------

#         if payment_days >= days_in_month:

#             monthly_bonus = MONTHLY_BONUS

#         else:

#             monthly_bonus = (
#                 MONTHLY_BONUS
#                 / days_in_month
#             ) * payment_days

#         # -----------------------------------------------------
#         # ROUND MONTHLY BONUS
#         # -----------------------------------------------------

#         monthly_bonus = round(
#             monthly_bonus,
#             2
#         )

#         # -----------------------------------------------------
#         # SET MONTH PD
#         # -----------------------------------------------------

#         employee_map[emp][
#             f"{month_key}_pd"
#         ] += payment_days

#         # -----------------------------------------------------
#         # SET MONTH BONUS
#         # -----------------------------------------------------

#         employee_map[emp][
#             f"{month_key}_bonus"
#         ] += monthly_bonus

#         # -----------------------------------------------------
#         # TOTAL PD
#         # -----------------------------------------------------

#         employee_map[emp][
#             "total_pd"
#         ] += payment_days

#         # -----------------------------------------------------
#         # TOTAL PDA
#         #
#         # Total of all monthly bonuses
#         # -----------------------------------------------------

#         employee_map[emp][
#             "tpda"
#         ] += monthly_bonus

#     # =========================================================
#     # FINAL CALCULATIONS & ROUNDING
#     # =========================================================

#     for emp in employee_map:

#         # -----------------------------------------------------
#         # ROUND MONTHLY PD & BONUS
#         # -----------------------------------------------------

#         for month in MONTH_ORDER:

#             month_key = month.lower()

#             employee_map[emp][
#                 f"{month_key}_pd"
#             ] = round(
#                 employee_map[emp][
#                     f"{month_key}_pd"
#                 ],
#                 2
#             )

#             employee_map[emp][
#                 f"{month_key}_bonus"
#             ] = round(
#                 employee_map[emp][
#                     f"{month_key}_bonus"
#                 ],
#                 2
#             )

#         # -----------------------------------------------------
#         # ROUND TOTAL PD
#         # -----------------------------------------------------

#         employee_map[emp]["total_pd"] = round(
#             employee_map[emp]["total_pd"],
#             2
#         )

#         # -----------------------------------------------------
#         # TOTAL PDA
#         #
#         # Sum of Jan-Bonus to Dec-Bonus
#         # -----------------------------------------------------

#         employee_map[emp]["tpda"] = round(
#             employee_map[emp]["tpda"],
#             2
#         )

#         # -----------------------------------------------------
#         # TOTAL BONUS
#         #
#         # Total Bonus = Total PDA × 8.5%
#         # -----------------------------------------------------

#         employee_map[emp]["total_bonus"] = round(
#             employee_map[emp]["tpda"]
#             * BONUS_PERCENTAGE,
#             2
#         )

#     # =========================================================
#     # RETURN DATA
#     # =========================================================

#     return list(
#         employee_map.values()
#     )

import frappe
import calendar
from datetime import datetime


MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

BONUS_COMPONENT = "Bonus"
MONTHLY_BONUS = 7000
BONUS_PERCENTAGE = 0.085


def execute(filters=None):
    filters = filters or {}

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters):
    columns = [
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": "Employee Name",
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Salary Structure",
            "fieldname": "salary_structure",
            "fieldtype": "Link",
            "options": "Salary Structure",
            "width": 130
        }
    ]

    # ---------------------------------------------------------
    # MONTHLY COLUMNS
    # ---------------------------------------------------------

    for month in MONTH_ORDER:

        columns.append({
            "label": f"{month}-PD",
            "fieldname": f"{month.lower()}_pd",
            "fieldtype": "Float",
            "width": 80
        })

        columns.append({
            "label": f"{month}-Bonus",
            "fieldname": f"{month.lower()}_bonus",
            "fieldtype": "Currency",
            "width": 90,
            "precision": 0
        })

    # ---------------------------------------------------------
    # TOTAL COLUMNS
    # ---------------------------------------------------------

    columns.append({
        "label": "Total PD",
        "fieldname": "total_pd",
        "fieldtype": "Float",
        "width": 90
    })

    columns.append({
        "label": "Total PDA",
        "fieldname": "tpda",
        "fieldtype": "Currency",
        "width": 110,
        "precision": 0
    })

    columns.append({
        "label": "Total Bonus",
        "fieldname": "total_bonus",
        "fieldtype": "Currency",
        "width": 110,
        "precision": 0
    })

    return columns


def get_data(filters):

    # ---------------------------------------------------------
    # CONDITIONS
    # ---------------------------------------------------------

    conditions = [
        "ss.docstatus = 1"
    ]

    values = {
        "bonus_component": BONUS_COMPONENT
    }

    # ---------------------------------------------------------
    # EMPLOYEE FILTER
    # ---------------------------------------------------------

    if filters.get("employee"):
        conditions.append(
            "ss.employee = %(employee)s"
        )

        values["employee"] = filters.get(
            "employee"
        )

    # ---------------------------------------------------------
    # SALARY STRUCTURE FILTER
    # ---------------------------------------------------------

    if filters.get("salary_structure"):
        conditions.append(
            "ss.salary_structure = %(salary_structure)s"
        )

        values["salary_structure"] = filters.get(
            "salary_structure"
        )

    # ---------------------------------------------------------
    # DEPARTMENT FILTER
    # ---------------------------------------------------------

    if filters.get("department"):
        conditions.append(
            "emp.department = %(department)s"
        )

        values["department"] = filters.get(
            "department"
        )

    # ---------------------------------------------------------
    # FROM DATE
    # ---------------------------------------------------------

    if filters.get("from_date"):
        conditions.append(
            "ss.start_date >= %(from_date)s"
        )

        values["from_date"] = filters.get(
            "from_date"
        )

    # ---------------------------------------------------------
    # TO DATE
    # ---------------------------------------------------------

    if filters.get("to_date"):
        conditions.append(
            "ss.start_date <= %(to_date)s"
        )

        values["to_date"] = filters.get(
            "to_date"
        )

    condition_str = " AND ".join(
        conditions
    )

    # ---------------------------------------------------------
    # SALARY SLIP DATA
    # ---------------------------------------------------------

    query = f"""
        SELECT
            ss.employee,
            ss.employee_name,
            ss.salary_structure,
            ss.payment_days AS present_days,
            ss.start_date,
            DATE_FORMAT(ss.start_date, '%%b') AS month

        FROM `tabSalary Slip` ss

        LEFT JOIN `tabEmployee` emp
            ON emp.name = ss.employee

        WHERE {condition_str}

        ORDER BY
            ss.employee_name,
            ss.start_date
    """

    raw_data = frappe.db.sql(
        query,
        values,
        as_dict=True
    )

    employee_map = {}

    # =========================================================
    # PROCESS SALARY SLIPS
    # =========================================================

    for row in raw_data:

        emp = row.employee

        # -----------------------------------------------------
        # INITIALIZE EMPLOYEE
        # -----------------------------------------------------

        if emp not in employee_map:

            employee_map[emp] = {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "salary_structure": row.salary_structure,

                "total_pd": 0,
                "tpda": 0,
                "total_bonus": 0,
            }

            # Initialize all months
            for month in MONTH_ORDER:

                month_key = month.lower()

                employee_map[emp][
                    f"{month_key}_pd"
                ] = 0

                employee_map[emp][
                    f"{month_key}_bonus"
                ] = 0

        # -----------------------------------------------------
        # MONTH
        # -----------------------------------------------------

        month_key = row.month.lower()

        # -----------------------------------------------------
        # GET START DATE
        # -----------------------------------------------------

        start_date = row.start_date

        if isinstance(start_date, str):

            start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            )

        year = start_date.year
        month_number = start_date.month

        # -----------------------------------------------------
        # ACTUAL DAYS IN MONTH
        # -----------------------------------------------------

        days_in_month = calendar.monthrange(
            year,
            month_number
        )[1]

        # -----------------------------------------------------
        # PAYMENT DAYS
        # -----------------------------------------------------

        payment_days = float(
            row.present_days or 0
        )

        # -----------------------------------------------------
        # MONTHLY BONUS
        #
        # Full Month:
        #     ₹7,000
        #
        # Partial Month:
        #     ₹7,000 / Actual Days × PD
        # -----------------------------------------------------

        if payment_days >= days_in_month:

            monthly_bonus = MONTHLY_BONUS

        else:

            monthly_bonus = (
                MONTHLY_BONUS
                / days_in_month
            ) * payment_days

        # -----------------------------------------------------
        # ADD MONTH DATA
        #
        # PD -> NO ROUNDING
        # Bonus -> Round at final stage
        # -----------------------------------------------------

        employee_map[emp][
            f"{month_key}_pd"
        ] += payment_days

        employee_map[emp][
            f"{month_key}_bonus"
        ] += monthly_bonus

        # -----------------------------------------------------
        # TOTAL PD
        #
        # NO ROUNDING
        # -----------------------------------------------------

        employee_map[emp][
            "total_pd"
        ] += payment_days

        # -----------------------------------------------------
        # TOTAL PDA
        #
        # Keep actual value until final rounding
        # -----------------------------------------------------

        employee_map[emp][
            "tpda"
        ] += monthly_bonus

    # =========================================================
    # FINAL CALCULATIONS
    # =========================================================

    for emp in employee_map:

        # -----------------------------------------------------
        # MONTHLY BONUS
        #
        # FULL ROUND OFF
        #
        # Example:
        # 880.50 -> 881
        # 880.49 -> 880
        # -----------------------------------------------------

        for month in MONTH_ORDER:

            month_key = month.lower()

            employee_map[emp][
                f"{month_key}_bonus"
            ] = round(
                employee_map[emp][
                    f"{month_key}_bonus"
                ]
            )

        # -----------------------------------------------------
        # TOTAL PDA
        #
        # FULL ROUND OFF
        # -----------------------------------------------------

        employee_map[emp]["tpda"] = round(
            employee_map[emp]["tpda"]
        )

        # -----------------------------------------------------
        # TOTAL BONUS
        #
        # Total Bonus = Total PDA × 8.5%
        #
        # FULL ROUND OFF
        # -----------------------------------------------------

        employee_map[emp]["total_bonus"] = round(
            employee_map[emp]["tpda"]
            * BONUS_PERCENTAGE
        )

        # -----------------------------------------------------
        # PD & TOTAL PD
        #
        # NO ROUNDING
        # -----------------------------------------------------

    # =========================================================
    # RETURN DATA
    # =========================================================

    return list(
        employee_map.values()
    )