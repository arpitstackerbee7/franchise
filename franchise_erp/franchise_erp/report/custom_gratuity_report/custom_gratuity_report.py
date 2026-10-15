# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


# Copyright (c) 2026, TZU Lifestyle Private Limited
# For license information, please see license.txt

# Copyright (c) 2026, TZU Lifestyle Private Limited
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
    
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link",
         "options": "Employee", "width": 100},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link",
         "options": "Department", "width": 150},
        {"label": "Designation", "fieldname": "designation", "fieldtype": "Link",
         "options": "Designation", "width": 150},
        {"label": "Location", "fieldname": "branch", "fieldtype": "Link",
         "options": "Branch", "width": 150},
        {"label": "Reporting Manager", "fieldname": "reporting_manager", "fieldtype": "Data", "width": 160},
        {"label": "DOJ", "fieldname": "date_of_joining", "fieldtype": "Date", "width": 100},
        {"label": "Service Tenure", "fieldname": "service_tenure", "fieldtype": "Data", "width": 120},
        {"label": "Gross Salary", "fieldname": "gross_salary", "fieldtype": "Currency", "width": 120},
        {"label": "Basic Salary", "fieldname": "basic_salary", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    filters = filters or {}
    as_on_date = getdate(filters.get("as_on_date") or today())

    conditions = ["status = 'Active'"]
    values = {}

    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("department"):
        conditions.append("department = %(department)s")
        values["department"] = filters.get("department")

    if filters.get("employee"):
        conditions.append("name = %(employee)s")
        values["employee"] = filters.get("employee")

    condition_str = " and ".join(conditions)

    employees = frappe.db.sql(f"""
        select
            name as employee,
            employee_name,
            department,
            designation,
            branch,
            reports_to,
            date_of_joining
        from `tabEmployee`
        where {condition_str}
        order by employee_name
    """, values, as_dict=True)

    # bulk-fetch reporting manager names to avoid N+1 queries
    manager_ids = list({e.reports_to for e in employees if e.reports_to})
    manager_names = {}
    if manager_ids:
        for m in frappe.db.get_all(
            "Employee",
            filters={"name": ["in", manager_ids]},
            fields=["name", "employee_name"],
        ):
            manager_names[m.name] = m.employee_name

    data = []
    for idx, emp in enumerate(employees, start=1):
        service_tenure = get_service_tenure(emp.date_of_joining, as_on_date)
        assignment = get_active_salary_structure_assignment(emp.employee, as_on_date)
        gross_salary = get_computed_gross_salary(assignment.salary_structure, assignment.base) if assignment else 0
        basic_salary = get_basic_component_amount(assignment.salary_structure) if assignment else 0

        data.append({
    
            "employee": emp.employee,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "designation": emp.designation,
            "branch": emp.branch,
            "reporting_manager": manager_names.get(emp.reports_to),
            "date_of_joining": emp.date_of_joining,
            "service_tenure": service_tenure,
            "gross_salary": gross_salary,
            "basic_salary": basic_salary,
        })

    return data


def get_service_tenure(doj, as_on_date):
    """Returns tenure as 'XY YM ZD' string, e.g. '9Y 10M 22D'."""
    if not doj:
        return ""

    doj = getdate(doj)
    if doj > as_on_date:
        return ""

    years = as_on_date.year - doj.year
    months = as_on_date.month - doj.month
    days = as_on_date.day - doj.day

    if days < 0:
        months -= 1
        prev_month_last_day = getdate(
            frappe.utils.add_days(
                getdate(f"{as_on_date.year}-{as_on_date.month:02d}-01"), -1
            )
        )
        days += prev_month_last_day.day

    if months < 0:
        years -= 1
        months += 12

    return f"{years}Y {months}M {days}D"


def get_basic_component_amount(salary_structure):
    if not salary_structure:
        return 0
    amount = frappe.db.get_value(
        "Salary Detail",
        {"parent": salary_structure, "parentfield": "earnings", "salary_component": "Basic"},
        "amount",
    )
    return amount or 0


def get_active_salary_structure_assignment(employee, as_on_date):
    assignment = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee, "docstatus": 1, "from_date": ["<=", as_on_date]},
        ["base", "salary_structure"],
        order_by="from_date desc",
        as_dict=True,
    )
    return assignment

def get_computed_gross_salary(salary_structure, base):
    """Evaluates every earning component of the Salary Structure in order
    to compute the true Gross Salary, instead of blindly trusting the
    assignment's 'base' field (which may be 0/unfilled by mistake).
    Handles fixed-amount components (Basic, CA, MA, E) as well as
    formula-based ones (HRA = B * .5, Special Allowance = base - (...))."""
    if not salary_structure:
        return 0

    earnings = frappe.get_all(
        "Salary Detail",
        filters={"parent": salary_structure, "parentfield": "earnings"},
        fields=["salary_component", "abbr", "amount", "formula", "amount_based_on_formula"],
        order_by="idx",
    )

    context = {"base": base or 0}
    total = 0

    for row in earnings:
        if row.amount_based_on_formula and row.formula:
            try:
                value = eval(row.formula, {"__builtins__": {}}, context)
            except Exception:
                value = 0
        else:
            value = row.amount or 0

        value = max(value, 0)  # earnings can't go negative
        context[row.abbr] = value
        total += value

    return total