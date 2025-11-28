import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def create_custom_fields():
    """Create or update custom fields in User DocType"""

    custom_fields = {
        "User": [
            {
                "fieldname": "company",
                "label": "Company",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "username",
                "permlevel": 0,
                "reqd": 1
            },
            # {
            #     "fieldname": "franchise_company",
            #     "label": "Franchise Company",
            #     "fieldtype": "Link",
            #     "options": "Company",
            #     "insert_after": "company",
            #     "permlevel": 0,
            #     "reqd": 1
            # }
        ]
    }

    for doctype, fields in custom_fields.items():
        for field in fields:
            try:
                existing_cf = frappe.get_all(
                    "Custom Field",
                    filters={"dt": doctype, "fieldname": field["fieldname"]},
                    fields=["name"]
                )

                if existing_cf:
                    # UPDATE existing field
                    doc = frappe.get_doc("Custom Field", existing_cf[0].name)
                    doc.update(field)
                    doc.flags.ignore_validate = True
                    doc.save()
                else:
                    # CREATE new field
                    create_custom_field(doctype, field)

                frappe.db.commit()

            except Exception:
                frappe.log_error(message=frappe.get_traceback(),
                                 title="Custom Field Creation Failed")
