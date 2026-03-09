import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():

    if not frappe.db.exists("Custom Field", "User-company"):

        custom_fields = {
            "User": [
                {
                    "fieldname": "company",
                    "label": "Company",
                    "fieldtype": "Link",
                    "options": "Company",
                    "insert_after": "username",
                    "in_list_view": 1,
                }
            ]
        }

        create_custom_fields(custom_fields)