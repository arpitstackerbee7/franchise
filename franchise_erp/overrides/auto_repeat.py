import frappe

from frappe.automation.doctype.auto_repeat.auto_repeat import AutoRepeat as FrappeAutoRepeat
from frappe.utils import add_days, getdate, get_first_day, get_last_day, today


class CustomAutoRepeat(FrappeAutoRepeat):

    def get_next_schedule_date(self, schedule_date, for_full_schedule=False):
        """
        Fortnightly schedule:

        1st  -> 16th of the same month
        16th -> 1st of the next month

        Other frequencies use standard Frappe logic.
        """

        if self.frequency != "Fortnightly":
            return super().get_next_schedule_date(
                schedule_date=schedule_date,
                for_full_schedule=for_full_schedule,
            )

        schedule_date = getdate(schedule_date)


        if schedule_date.day <= 15:
            next_date = schedule_date.replace(day=16)


        else:
            next_date = get_first_day(
                add_days(get_last_day(schedule_date), 1)
            )

        if not for_full_schedule:
            while getdate(next_date) < getdate(today()):
                if next_date.day <= 15:
                    next_date = next_date.replace(day=16)
                else:
                    next_date = get_first_day(
                        add_days(get_last_day(next_date), 1)
                    )

            if self.end_date and getdate(next_date) > getdate(self.end_date):
                return schedule_date

        return next_date

    def set_auto_repeat_period(self, new_doc):
        """
        Fortnightly document periods:

        1st  - 15th
        16th - month end

        Other frequencies use standard Frappe logic.
        """

        if self.frequency != "Fortnightly":
            return super().set_auto_repeat_period(new_doc)

        if not (
            new_doc.meta.get_field("from_date")
            and new_doc.meta.get_field("to_date")
        ):
            return

        last_ref_doc = frappe.get_all(
            self.reference_doctype,
            fields=[
                "name",
                "from_date",
                "to_date",
            ],
            filters=[
                ["auto_repeat", "=", self.name],
                ["docstatus", "<", 2],
            ],
            order_by="creation desc",
            limit=1,
        )

        if not last_ref_doc:
            return

        last_from_date = getdate(last_ref_doc[0].from_date)
        last_to_date = getdate(last_ref_doc[0].to_date)

        if last_from_date.day == 1 and last_to_date.day == 15:
            from_date = last_to_date.replace(day=16)
            to_date = get_last_day(from_date)

        else:
            from_date = get_first_day(
                add_days(last_to_date, 1)
            )

            to_date = from_date.replace(day=15)

        new_doc.set("from_date", from_date)
        new_doc.set("to_date", to_date)