# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt




import frappe

# Month order for Bonus Year (Oct to Sept)
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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
    selected_month = filters.get("month")
    months_to_show = [selected_month] if selected_month else MONTH_ORDER

    # Month-wise PD and Bonus columns
    for month in months_to_show:
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
    columns.append({"label": "Total Bonus", "fieldname": "total_bonus", "fieldtype": "Currency", "width": 110})

    return columns


def get_data(filters):
    conditions = ["be.docstatus = 1"]
    values = {}

    if filters.get("bonus_year"):
        conditions.append("be.bonus_year = %(bonus_year)s")
        values["bonus_year"] = filters.get("bonus_year")

    if filters.get("employee"):
        conditions.append("be.employee = %(employee)s")
        values["employee"] = filters.get("employee")

    if filters.get("salary_structure"):
        conditions.append("be.salary_structure = %(salary_structure)s")
        values["salary_structure"] = filters.get("salary_structure")

    if filters.get("department"):
        conditions.append("emp.department = %(department)s")
        values["department"] = filters.get("department")
    if filters.get("month"):
        conditions.append("be.month = %(month)s")
        values["month"] = filters.get("month")

    condition_str = " AND ".join(conditions)

    query = f"""
        SELECT
            be.employee,
            be.employee_name,
            be.salary_structure,
            be.month,
            be.present_days,
            be.monthly_bonus_amount
        FROM `tabBonus Entry` be
        LEFT JOIN `tabEmployee` emp ON emp.name = be.employee
        WHERE {condition_str}
        ORDER BY be.employee_name
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)

    # Pivot: group by employee
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
            }
            # Initialize all month columns as 0
            for month in MONTH_ORDER:
                employee_map[emp][f"{month.lower()}_pd"] = 0
                employee_map[emp][f"{month.lower()}_bonus"] = 0

        month_key = row.month.lower()
        employee_map[emp][f"{month_key}_pd"] = row.present_days or 0
        employee_map[emp][f"{month_key}_bonus"] = row.monthly_bonus_amount or 0
        employee_map[emp]["total_pd"] += (row.present_days or 0)
        employee_map[emp]["total_bonus"] += (row.monthly_bonus_amount or 0)

    return list(employee_map.values())