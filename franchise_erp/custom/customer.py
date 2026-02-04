import frappe
from frappe.model.naming import make_autoname
from erpnext.selling.doctype.customer.customer import Customer

class CustomCustomer(Customer):
    def autoname(self):
        if not self.custom_company_abbrevation:
            frappe.throw("Company Abbreviation is required for Customer naming")

        self.name = make_autoname(f"{self.custom_company_abbrevation}-.#####")


def before_save(doc, method):

    if doc.mobile_no:
        if not doc.mobile_no.isdigit() or len(doc.mobile_no) != 10:
            frappe.throw("Mobile Number must be a 10-digit number.")

    if doc.custom_mobile_no_customer:
        if not doc.custom_mobile_no_customer.isdigit() or len(doc.custom_mobile_no_customer) != 10:
            frappe.throw("Mobile Number  must be a 10-digit number.")

    conditions = []
    params = {"current_doc": doc.name}

    if doc.mobile_no:
        conditions.append("(mobile_no = %(mobile)s OR custom_mobile_no_customer = %(mobile)s)")
        params["mobile"] = doc.mobile_no
    elif doc.custom_mobile_no_customer:
        conditions.append("(custom_mobile_no_customer = %(custom_mobile)s OR mobile_no = %(custom_mobile)s)")
        params["custom_mobile"] = doc.custom_mobile_no_customer

    if conditions:
        where_clause = " AND ".join(conditions)
        customer_exists = frappe.db.sql(
            f"""
            SELECT name FROM `tabCustomer`
            WHERE {where_clause}
            AND name != %(current_doc)s
            LIMIT 1
            """,
            params,
        )
        if customer_exists:
            error_message = ""
            if doc.mobile_no:
                error_message = f"Customer with mobile number '{doc.mobile_no}' already exists."
            elif doc.custom_mobile_no_customer:
                error_message = f"Customer with reference mobile number '{doc.custom_mobile_no_customer}' already exists."
            frappe.throw(error_message)

    elif not doc.custom_mobile_no_customer:
        doc.custom_mobile_no_customer = doc.mobile_no








import frappe

def validate_customer_counter_rules(doc, method):
    if not doc.custom_company:
        return

    disable_counter = frappe.db.get_value(
        "Company",
        doc.custom_company,
        "custom_disable_validation_for_counter"
    )

    # --------------------------------------------------
    # WHEN COUNTER VALIDATION IS DISABLED (unchecked)
    # --------------------------------------------------
    if not disable_counter:

        # 🔹 1. BYPASS CREDIT LIMIT VALIDATION
        # ERP throws error if row exists but credit_limit is empty
        for row in doc.get("credit_limits") or []:
            row.credit_limit = row.credit_limit or 0

        # 🔹 2. CHECK MRP PRICE LIST (exist + enabled)
        enabled = frappe.db.get_value(
            "Price List",
            "MRP",
            "enabled"
        )

        if not enabled or enabled != 1:
            frappe.throw(
                "Please create and enable <b>MRP</b> Price List",
                frappe.ValidationError
            )

        # 🔹 3. SET DEFAULT PRICE LIST
        if not doc.default_price_list:
            doc.default_price_list = "MRP"
