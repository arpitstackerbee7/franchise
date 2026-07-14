import frappe
from frappe import _
from frappe.model.document import Document


class BackDatePrivilege(Document):

    def validate(self):
        self.validate_role()
        self.validate_duplicate_user()
        self.validate_duplicate_doctypes()

    def validate_role(self):
        if "Back Date Privilege Manager" not in frappe.get_roles():
            frappe.throw(
                _("Only users with the Back Date Privilege Manager role can create or modify Back Date Privilege.")
            )

    def validate_duplicate_user(self):
        existing = frappe.db.exists(
            "Back Date Privilege",
            {
                "user": self.user,
                "name": ["!=", self.name]
            }
        )

        if existing:
            frappe.throw(_("Back Date Privilege already exists for this user."))

    def validate_duplicate_doctypes(self):
        doctypes = []

        for row in self.permissions:
            if row.document_type in doctypes:
                frappe.throw(
                    _("Document Type <b>{0}</b> is added more than once.")
                    .format(row.document_type)
                )

            doctypes.append(row.document_type)