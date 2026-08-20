# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

# import frappe


import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
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
            "label": "Attendance Date",
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": "Company",
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 150
        },
        {
            "label": "Shift",
            "fieldname": "shift",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 100
        },
        {
            "label": "Standard Hours",
            "fieldname": "standard_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 110
        },
        {
            "label": "Actual Hours",
            "fieldname": "working_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 110
        },
        {
            "label": "Extra Hours",
            "fieldname": "extra_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 110
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 90
        },
    ]


def get_data(filters):
    conditions = "att.docstatus = 1"
    values = {}

    if filters.get("from_date"):
        conditions += " AND att.attendance_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND att.attendance_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    if filters.get("employee"):
        conditions += " AND att.employee = %(employee)s"
        values["employee"] = filters["employee"]
    if filters.get("company"):
        conditions += " AND att.company = %(company)s"
        values["company"] = filters["company"]
    if filters.get("shift"):
        conditions += " AND att.shift = %(shift)s"
        values["shift"] = filters["shift"]

    rows = frappe.db.sql(f"""
        SELECT
            att.employee, att.employee_name, att.attendance_date,
            att.company, att.shift, att.working_hours, att.status,
            st.start_time, st.end_time
        FROM `tabAttendance` att
        LEFT JOIN `tabShift Type` st ON st.name = att.shift
        WHERE {conditions}
        ORDER BY att.attendance_date DESC
    """, values, as_dict=True)

    min_extra = flt(filters.get("min_extra_hours") or 0)
    data = []

    for row in rows:
        standard_hours = get_standard_shift_hours(row.start_time, row.end_time)
        working_hours = flt(row.working_hours)
        extra_hours = flt(working_hours - standard_hours, 2) if standard_hours else 0

        if extra_hours > min_extra:
            row["standard_hours"] = standard_hours
            row["extra_hours"] = extra_hours
            data.append(row)

    return data


def get_standard_shift_hours(start_time, end_time):
    if not start_time or not end_time:
        return 0

    start_secs = start_time.total_seconds() if hasattr(start_time, "total_seconds") else start_time
    end_secs = end_time.total_seconds() if hasattr(end_time, "total_seconds") else end_time

    if end_secs < start_secs:
        # midnight crossing shift
        duration_secs = (86400 - start_secs) + end_secs
    else:
        duration_secs = end_secs - start_secs

    return round(duration_secs / 3600, 2)


from frappe.utils import flt