# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PromotionFranchiselinking(Document):
	pass










# @frappe.whitelist()
# def create_promotion_for_companies(promotion_name, companies):
#     if isinstance(companies, str):
#         companies = frappe.parse_json(companies)

#     template = frappe.get_doc("Promotional Scheme", promotion_name)

#     created = []
#     for company in companies:
#         new_doc = frappe.copy_doc(template)
#         new_doc.name = promotion_name + " - " + company             
#         new_doc.company = company   
#         new_doc.custom_is_template = 0    
#         new_doc.insert(ignore_permissions=True)
#         created.append(new_doc.name)

#     return created






import frappe

# CREATE
@frappe.whitelist()
def create_promotion_for_companies(promotion_name, companies, valid_from=None, valid_upto=None):
    if isinstance(companies, str):
        companies = frappe.parse_json(companies)

    template = frappe.get_doc("Promotional Scheme", promotion_name)

    created = []
    skipped = []

    for row in companies:
        company = row.get("company") or row.get("franchise")
        disable = row.get("disable", 0)

        scheme_name = f"{promotion_name} - {company}"

        # 🔴 Agar already exist karta hai to skip
        if frappe.db.exists("Promotional Scheme", scheme_name):
            skipped.append(company)
            continue

        new_doc = frappe.copy_doc(template)
        new_doc.name = scheme_name
        new_doc.company = company
        new_doc.custom_is_template = 0
        new_doc.disable = 1 if disable else 0
        new_doc.valid_from = valid_from
        new_doc.valid_upto = valid_upto

        new_doc.insert(ignore_permissions=True)
        created.append(scheme_name)

    return {
        "created": created,
        "skipped": skipped
    }



# UPDATE (Enable / Disable Sync)
@frappe.whitelist()
def sync_promotion_status(promotion_name, franchises, valid_from=None, valid_upto=None):
    if isinstance(franchises, str):
        franchises = frappe.parse_json(franchises)

    for row in franchises:
        company = row.get("franchise") or row.get("company")
        disable = row.get("disable", 0)

        scheme_name = f"{promotion_name} - {company}"

        if frappe.db.exists("Promotional Scheme", scheme_name):
            frappe.db.set_value(
                "Promotional Scheme",
                scheme_name,
                {
                    "disable": 1 if disable else 0,
                    "valid_from": valid_from,
                    "valid_upto": valid_upto,
                    "custom_is_template": 0
                }
            )

    return True



# DELETE
@frappe.whitelist()
def delete_promotions(promotion_name, franchises):
    if isinstance(franchises, str):
        franchises = frappe.parse_json(franchises)

    deleted = []

    for row in franchises:
        company = row.get("franchise") or row.get("company")
        scheme_name = f"{promotion_name} - {company}"

        if frappe.db.exists("Promotional Scheme", scheme_name):
            frappe.delete_doc("Promotional Scheme", scheme_name, force=1)
            deleted.append(company)

    return deleted
