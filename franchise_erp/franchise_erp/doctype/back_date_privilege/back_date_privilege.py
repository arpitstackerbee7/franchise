# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BackDatePrivilege(Document):
    def validate(self):
        existing = frappe.db.exists(
            "Back Date Privilege",
            {
                "user": self.user,
                "name": ["!=", self.name]
            }
        )

        if existing:
            frappe.throw("Back Date Privilege already exists for this user.")