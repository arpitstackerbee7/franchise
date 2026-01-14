import frappe

def apply_sales_term(doc, method=None):
    if not doc.custom_sales_term:
        return

    term = frappe.get_doc("Sales Term Template", doc.custom_sales_term)

    for item in doc.items:

        # Store base rate ONCE (idempotent)
        if not item.custom_base_rate_new:
            item.custom_base_rate_new = item.rate

        adjusted_rate = item.custom_base_rate_new

        for row in term.sales_term_charges:
            print(row.charge_type)
            if row.charge_type == "Rate Diff":
                adjusted_rate -= row.value

        item.rate = adjusted_rate

