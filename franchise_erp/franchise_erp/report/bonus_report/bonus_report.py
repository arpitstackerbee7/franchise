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

import frappe

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


BONUS_COMPONENT = "Bonus"


def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Salary Structure", "fieldname": "salary_structure", "fieldtype": "Link", "options": "Salary Structure", "width": 130},
    ]

    for month in MONTH_ORDER:
        columns.append({
            "label": f"{month}-PD",
            "fieldname": f"{month.lower()}_pd",
            "fieldtype": "Float",
            "width": 80,
            "precision": 2
        })
        columns.append({
            "label": f"{month}-Bonus",
            "fieldname": f"{month.lower()}_bonus",
            "fieldtype": "Currency",
            "width": 90
        })

    # Totals
    columns.append({"label": "Total PD", "fieldname": "total_pd", "fieldtype": "Float", "width": 90, "precision": 2})
    columns.append({"label": "TPDA", "fieldname": "tpda", "fieldtype": "Currency", "width": 110})
    columns.append({"label": "Total Bonus", "fieldname": "total_bonus", "fieldtype": "Currency", "width": 110})

    return columns


def get_data(filters):
    conditions = ["ss.docstatus = 1"]
    values = {"bonus_component": BONUS_COMPONENT}

    if filters.get("employee"):
        conditions.append("ss.employee = %(employee)s")
        values["employee"] = filters.get("employee")

    if filters.get("salary_structure"):
        conditions.append("ss.salary_structure = %(salary_structure)s")
        values["salary_structure"] = filters.get("salary_structure")

    if filters.get("department"):
        conditions.append("emp.department = %(department)s")
        values["department"] = filters.get("department")

    if filters.get("from_date"):
        conditions.append("ss.start_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("ss.start_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT
            ss.employee,
            ss.employee_name,
            ss.salary_structure,
            ss.payment_days AS present_days,
            DATE_FORMAT(ss.start_date, '%%b') AS month,
            COALESCE(earn.total_earnings, 0) AS additional_total,
            COALESCE(ded.total_deductions, 0) AS deduction_total
        FROM `tabSalary Slip` ss
        LEFT JOIN `tabEmployee` emp ON emp.name = ss.employee
        LEFT JOIN (
            SELECT parent, SUM(amount) AS total_earnings
            FROM `tabSalary Detail`
            WHERE parentfield = 'earnings' AND parenttype = 'Salary Structure'
            GROUP BY parent
        ) earn ON earn.parent = ss.salary_structure
        LEFT JOIN (
            SELECT parent, SUM(amount) AS total_deductions
            FROM `tabSalary Detail`
            WHERE parentfield = 'deductions' AND parenttype = 'Salary Structure'
            GROUP BY parent
        ) ded ON ded.parent = ss.salary_structure
        WHERE {condition_str}
        ORDER BY ss.employee_name
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)

    employee_map = {}

    for row in raw_data:
        emp = row.employee
        if emp not in employee_map:
            employee_map[emp] = {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "salary_structure": row.salary_structure,
                "total_pd": 0,
                "total_bonus": 0,
                "tpda": 0,
            }
            for month in MONTH_ORDER:
                employee_map[emp][f"{month.lower()}_pd"] = 0
                employee_map[emp][f"{month.lower()}_bonus"] = 0

        month_key = row.month.lower()
        per_day_salary = (row.additional_total - row.deduction_total) / 30
        pda = (row.present_days or 0) * per_day_salary
        employee_map[emp][f"{month_key}_pd"] = row.present_days or 0
        employee_map[emp][f"{month_key}_bonus"] = pda
        employee_map[emp]["total_pd"] += (row.present_days or 0)
        employee_map[emp]["tpda"] += pda
        employee_map[emp]["total_bonus"] = employee_map[emp]["tpda"] * 0.085

    return list(employee_map.values())