
import frappe
from frappe.utils import getdate

FY_START_DATE = getdate("2026-04-01")


def get_fy_short(date):
    date = getdate(date)

    if date < FY_START_DATE:
        return None

    year = date.year

    if date.month >= 4:
        start = year
        end = year + 1
    else:
        start = year - 1
        end = year

    return f"{str(start)[2:]}-{str(end)[2:]}"


DOCTYPE_PREFIX = {
    "Purchase Order": "PO",
    "Purchase Receipt": "PR",
    "Purchase Invoice": "PI",
    "Sales Invoice": "SI",
    "Sales Order": "SO",
    "Payment Entry": "PV",
    "Journal Entry": "JV",
    "Stock Entry": "STV",
    "Subcontracting Order": "JOBO",
    "Subcontracting Receipt": "JOBR",
    "Incoming Logistics": "IL",
    "Gate Entry": "IG",
    "Outgoing Logistics": "OL",
}


RETURN_PREFIX_MAP = {
    "Sales Invoice": "SR",
    "Purchase Receipt": "PRT",
    "Purchase Invoice": "RT",
}


# 🔥 GENERIC FUNCTION (WORKS FOR ALL DOCTYPES)
# def get_next_number(doctype, series):
#     last = frappe.db.sql(f"""
#         SELECT name FROM `tab{doctype}`
#         WHERE name LIKE %s
#         ORDER BY name DESC
#         LIMIT 1
#     """, (series + "%",))

#     if last:
#         last_name = last[0][0]
#         last_number = int(last_name.split("/")[-1])
#         return str(last_number + 1).zfill(5)
#     else:
#         return "00001"

import re

import frappe
import re

import frappe
import re

def get_next_number(doctype, prefix, digits=5):
    names = frappe.db.sql(f"""
        SELECT name FROM `tab{doctype}`
        WHERE name LIKE %s
    """, (f"{prefix}%",), as_dict=True)

    max_no = 0

    for row in names:
        name = row.name

        # ✅ remove amend suffix (-1, -2)
        clean_name = re.sub(r"-\d+$", "", name)

        # ✅ extract last number
        match = re.search(r'(\d+)(?!.*\d)', clean_name)

        if match:
            num = int(match.group(1))
            if num > max_no:
                max_no = num

    next_no = max_no + 1

    return str(next_no).zfill(digits)

import frappe
from frappe.utils import getdate

FY_START_DATE = getdate("2026-04-01")

def get_doc_date(doc):
    # 🔥 priority wise check

    if doc.doctype == "Subcontracting Order":
        if hasattr(doc, "custom_posting_date") and doc.custom_posting_date:
            return getdate(doc.custom_posting_date)
        
    if doc.doctype == "Incoming Logistics":
        if hasattr(doc, "invoice_date") and doc.invoice_date:
            return getdate(doc.invoice_date)
             
    if hasattr(doc, "posting_date") and doc.posting_date:
        return getdate(doc.posting_date)

    if hasattr(doc, "transaction_date") and doc.transaction_date:
        return getdate(doc.transaction_date)

    if hasattr(doc, "custom_posting_date") and doc.schedule_date:
        return getdate(doc.custom_posting_date)

    if hasattr(doc, "document_date") and doc.document_date:
        return getdate(doc.document_date)


    return getdate(frappe.utils.today())

def company_fy_autoname(doc, method=None):

    # 🔥 prevent duplicate execution
    if doc.name and not doc.name.startswith("New"):
        return

    if doc.doctype not in DOCTYPE_PREFIX:
        return

    # ✅ USE GENERIC DATE FUNCTION
    date = get_doc_date(doc)

    # 🔥 backdate → ERPNext default
    if date < FY_START_DATE:
        return

    fy = get_fy_short(date)
    if not fy:
        return

    prefix = DOCTYPE_PREFIX.get(doc.doctype)

    if getattr(doc, "is_return", 0):
        prefix = RETURN_PREFIX_MAP.get(doc.doctype, prefix + "R")

    series = f"{prefix}/{fy}/"

    number = get_next_number(doc.doctype, series)

    doc.name = f"{series}{number}"



# def company_fy_autoname(doc, method=None):

#     if doc.doctype not in DOCTYPE_PREFIX:
#         return

#     fy = get_fy_short(doc.posting_date or frappe.utils.today())

#     prefix = DOCTYPE_PREFIX.get(doc.doctype)

#     # 🔥 CLEAN RETURN HANDLING
#     is_return = getattr(doc, "is_return", 0)

#     if is_return == 1:
#         prefix = RETURN_PREFIX_MAP.get(doc.doctype, prefix + "R")

#     series = f"{prefix}/{fy}/"

#     doc.name = frappe.model.naming.make_autoname(series + ".#####")