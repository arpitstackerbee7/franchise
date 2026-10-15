

import frappe
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest


class CustomAttendanceRequest(AttendanceRequest):
    def create_attendance_records(self):
        if self.custom_missed_checkout:
            return

        
        super().create_attendance_records()