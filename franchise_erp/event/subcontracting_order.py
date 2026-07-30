# import frappe
# from frappe.utils import flt


# @frappe.whitelist()
# def get_item_tax_template(item_code, rate, company):
#     if not item_code or not company:
#         return None

#     rate = flt(rate)

#     company_abbr = frappe.db.get_value(
#         "Company",
#         company,
#         "abbr"
#     )

#     if not company_abbr:
#         return None

#     taxes = frappe.get_all(
#         "Item Tax",
#         filters={
#             "parent": item_code,
#             "parenttype": "Item",
#             "parentfield": "taxes",
#         },
#         fields=[
#             "item_tax_template",
#             "minimum_net_rate",
#             "maximum_net_rate",
#         ],
#         order_by="idx asc",
#     )

#     for tax in taxes:
#         template = tax.item_tax_template

#         if not template:
#             continue

#         min_rate = flt(tax.minimum_net_rate)
#         max_rate = flt(tax.maximum_net_rate)

#         rate_matches = (
#             (not min_rate or rate >= min_rate)
#             and
#             (not max_rate or rate <= max_rate)
#         )

#         company_matches = template.endswith(
#             f"- {company_abbr}"
#         )

#         if rate_matches and company_matches:
#             return template

#     return None


# @frappe.whitelist()
# def get_job_work_order_taxes_and_charges(purchase_order, company):
#     if not purchase_order or not company:
#         return None

#     po_template = frappe.db.get_value(
#         "Purchase Order",
#         purchase_order,
#         "taxes_and_charges"
#     )

#     if not po_template:
#         return None

#     company_abbr = frappe.db.get_value(
#         "Company",
#         company,
#         "abbr"
#     )

#     if not company_abbr:
#         return None

#     if "RCM Out-state" in po_template:
#         template = f"Output GST RCM Out-state - {company_abbr}"

#     elif "RCM In-state" in po_template:
#         template = f"Output GST RCM In-state - {company_abbr}"

#     elif "Out-state" in po_template:
#         template = f"Output GST Out-state - {company_abbr}"

#     elif "In-state" in po_template:
#         template = f"Output GST In-state - {company_abbr}"

#     else:
#         return None

#     if frappe.db.exists(
#         "Sales Taxes and Charges Template",
#         template
#     ):
#         return template

#     return None