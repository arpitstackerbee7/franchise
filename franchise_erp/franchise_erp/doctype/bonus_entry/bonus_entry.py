import frappe
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day


class BonusEntry(Document):
    def before_save(self):
        self.fetch_salary_structure()
        self.fetch_bonus_rate_and_percent()
        self.fetch_present_days()
        self.check_duplicate()
        self.calculate_bonus()

    def fetch_salary_structure(self):
        if self.employee and not self.salary_structure:
            ss_assignment = frappe.db.get_value(
                "Salary Structure Assignment",
                {"employee": self.employee, "docstatus": 1},
                "salary_structure",
                order_by="from_date desc"
            )
            if ss_assignment:
                self.salary_structure = ss_assignment
            else:
                frappe.throw(f"No active Salary Structure Assignment found for {self.employee_name or self.employee}")

    def fetch_bonus_rate_and_percent(self):
        if self.salary_structure:
            rate, percent = frappe.db.get_value(
                "Salary Structure",
                self.salary_structure,
                ["custom_bonus_wage_rate", "custom_bonus_percent"]
            )
            self.bonus_wage_rate = rate or 0
            self.bonus_percent = percent or 0

    def get_month_date_range(self):
        """Returns start_date and end_date for the selected Month + Bonus Year"""
        # Bonus Year format: "2025-2026" -> Oct 2025 to Sept 2026
        start_year, end_year = self.bonus_year.split("-")

        month_to_calendar = {
            "Oct": (10, start_year), "Nov": (11, start_year), "Dec": (12, start_year),
            "Jan": (1, end_year), "Feb": (2, end_year), "Mar": (3, end_year),
            "Apr": (4, end_year), "May": (5, end_year), "Jun": (6, end_year),
            "Jul": (7, end_year), "Aug": (8, end_year), "Sep": (9, end_year),
        }

        month_num, year = month_to_calendar[self.month]
        date_str = f"{year}-{month_num:02d}-01"
        start_date = get_first_day(date_str)
        end_date = get_last_day(date_str)
        return start_date, end_date

    def fetch_present_days(self):
        if not (self.employee and self.month and self.bonus_year):
            return

        start_date, end_date = self.get_month_date_range()

        # Update Days in Month automatically
        self.days_in_month = (end_date - start_date).days + 1

        # Step 1: Present/Half Day/WFH from Attendance
        present_from_attendance = frappe.db.count("Attendance", {
            "employee": self.employee,
            "attendance_date": ["between", [start_date, end_date]],
            "status": ["in", ["Present", "Half Day", "Work From Home"]],
            "docstatus": 1
        })

        # Step 2: Employee's Holiday List
        holiday_list = frappe.db.get_value("Employee", self.employee, "holiday_list")
        if not holiday_list:
            company = frappe.db.get_value("Employee", self.employee, "company")
            holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

        unattended_holidays = 0
        if holiday_list:
            holidays_in_month = frappe.db.sql("""
                SELECT holiday_date FROM `tabHoliday`
                WHERE parent = %(holiday_list)s
                AND holiday_date BETWEEN %(start)s AND %(end)s
            """, {"holiday_list": holiday_list, "start": start_date, "end": end_date}, as_dict=True)

            attended_dates = set(frappe.db.sql_list("""
                SELECT attendance_date FROM `tabAttendance`
                WHERE employee = %(employee)s
                AND attendance_date BETWEEN %(start)s AND %(end)s
                AND docstatus = 1
            """, {"employee": self.employee, "start": start_date, "end": end_date}))

            unattended_holidays = sum(
                1 for h in holidays_in_month if h.holiday_date not in attended_dates
            )

        self.present_days = present_from_attendance + unattended_holidays

    def check_duplicate(self):
        existing = frappe.db.exists("Bonus Entry", {
            "employee": self.employee,
            "bonus_year": self.bonus_year,
            "month": self.month,
            "name": ["!=", self.name],
            "docstatus": ["!=", 2]
        })
        if existing:
            frappe.throw(f"Bonus Entry already exists for {self.employee_name} - {self.month} {self.bonus_year}")

    def calculate_bonus(self):
        if self.days_in_month and self.bonus_wage_rate and self.present_days is not None:
            self.monthly_bonus_amount = round(
                (self.bonus_wage_rate / self.days_in_month)
                * self.present_days
                * (self.bonus_percent / 100),
                2
            )
        else:
            self.monthly_bonus_amount = 0