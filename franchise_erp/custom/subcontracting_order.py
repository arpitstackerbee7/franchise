import frappe

# @frappe.whitelist()
# def get_outgoing_logistics_data(subcontracting_order):
#     sc = frappe.get_doc("Subcontracting Order", subcontracting_order)

#     # Prevent duplicate
#     existing = frappe.db.exists(
#         "Outgoing Logistics",
#         {"document_no": sc.name}
#     )
#     if existing:
#         frappe.throw(f"Outgoing Logistics already exists: {existing}")

#     return {
#         "owner_site": sc.company,
#         "company_abbreviation": frappe.db.get_value("Company", sc.company, "abbr"),
#         "consignee_supplier": sc.supplier,
#         "transporter": sc.supplier,
#         "date": frappe.utils.today(),
#         "document_no": sc.name,
#         # "document_date": sc.transaction_date,
#         "quantity": sc.total_qty,
#         "unit": "Nos",
#         # "type": "S&D: Sales Invoice/Transfer In",
#         "type": "Job Order",
#         "mode": "Land",
#     }
import frappe
from frappe.utils import today

@frappe.whitelist()
def get_outgoing_logistics_data(subcontracting_order):

    if not subcontracting_order:
        frappe.throw("Subcontracting Order is required")

    # ✅ Safe doc fetch
    sc = frappe.get_doc("Subcontracting Order", subcontracting_order)

    return {
        "owner_site": sc.company,
        "company_abbreviation": frappe.db.get_value(
            "Company",
            sc.company,
            "abbr"
        ),
        "consignee_supplier": sc.supplier,
        "transporter": sc.supplier,
        "date": today(),
        "quantity": sc.total_qty,
        "unit": "Nos",
        "type": "Job Order",
        "mode": "Land",
        "references": [
            {
                "source_doctype": "Job Work Order",
                "source_name": sc.name
            }
        ]
    }





import frappe

@frappe.whitelist()
def get_subcontracting_order_city(subcontracting_order):
    so = frappe.get_doc("Subcontracting Order", subcontracting_order)

    # 1️⃣ Shipping Address (priority)
    if so.shipping_address:
        city = frappe.db.get_value(
            "Address",
            so.shipping_address,
            "custom_citytown"
        )
        if city:
            return city

    # 2️⃣ Billing Address (fallback)
    if so.billing_address:
        city = frappe.db.get_value(
            "Address",
            so.billing_address,
            "custom_citytown"
        )
        if city:
            return city

    return None


import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_item_tax_template(item_code, rate, company):
    if not item_code or not company:
        return None

    rate = flt(rate)

    company_abbr = frappe.db.get_value(
        "Company",
        company,
        "abbr"
    )

    if not company_abbr:
        return None

    taxes = frappe.get_all(
        "Item Tax",
        filters={
            "parent": item_code,
            "parenttype": "Item",
            "parentfield": "taxes",
        },
        fields=[
            "item_tax_template",
            "minimum_net_rate",
            "maximum_net_rate",
        ],
        order_by="idx asc",
    )

    for tax in taxes:
        template = tax.item_tax_template

        if not template:
            continue

        min_rate = flt(tax.minimum_net_rate)
        max_rate = flt(tax.maximum_net_rate)

        rate_matches = (
            (not min_rate or rate >= min_rate)
            and
            (not max_rate or rate <= max_rate)
        )

        company_matches = template.endswith(
            f"- {company_abbr}"
        )

        if rate_matches and company_matches:
            return template

    return None


@frappe.whitelist()
def get_job_work_order_taxes_and_charges(purchase_order, company):
    if not purchase_order or not company:
        return None

    po_template = frappe.db.get_value(
        "Purchase Order",
        purchase_order,
        "taxes_and_charges"
    )

    if not po_template:
        return None

    company_abbr = frappe.db.get_value(
        "Company",
        company,
        "abbr"
    )

    if not company_abbr:
        return None

    if "RCM Out-state" in po_template:
        template = f"Output GST RCM Out-state - {company_abbr}"

    elif "RCM In-state" in po_template:
        template = f"Output GST RCM In-state - {company_abbr}"

    elif "Out-state" in po_template:
        template = f"Output GST Out-state - {company_abbr}"

    elif "In-state" in po_template:
        template = f"Output GST In-state - {company_abbr}"

    else:
        return None

    if frappe.db.exists(
        "Sales Taxes and Charges Template",
        template
    ):
        return template

    return None


def set_tax_rows_on_net_total(doc, method=None):
    for tax in doc.get("taxes") or []:
        if tax.charge_type in ("Actual", "On Previous Row Total"):
            tax.charge_type = "On Net Total"
        

