# # import frappe

# # def short_fy_naming(doc, method=None):
# #     try:
# #         if not doc.name:
# #             return

# #         # Only run when FY present
# #         if "202" not in doc.name:
# #             return

# #         name = doc.name
# #         parts = name.split("-")

# #         for i in range(len(parts)-1):
# #             if len(parts[i]) == 4 and parts[i].isdigit():
# #                 if len(parts[i+1]) == 4 and parts[i+1].isdigit():

# #                     short_fy = parts[i][-2:] + "-" + parts[i+1][-2:]
# #                     full_fy = parts[i] + "-" + parts[i+1]

# #                     doc.name = name.replace(full_fy, short_fy)
# #                     break

# #     except Exception:
# #         frappe.log_error(frappe.get_traceback(), "FY Short Naming Error")

# # import frappe

# # def short_fy_naming(doc, method=None):
# #     try:
# #         # ✅ ONLY FOR NEW DOC
# #         if not doc.is_new():
# #             return

# #         if not doc.name:
# #             return

# #         name = doc.name

# #         separators = ["-", "/"]

# #         for sep in separators:
# #             parts = name.split(sep)

# #             for part in parts:
# #                 if len(part) == 9 and "-" in part:
# #                     years = part.split("-")

# #                     if (
# #                         len(years) == 2
# #                         and years[0].isdigit()
# #                         and years[1].isdigit()
# #                         and len(years[0]) == 4
# #                         and len(years[1]) == 4
# #                     ):
# #                         short_fy = years[0][-2:] + "-" + years[1][-2:]
# #                         doc.name = name.replace(part, short_fy)
# #                         return

# #     except Exception:
# #         frappe.log_error(frappe.get_traceback(), "FY Short Naming Error")


# import frappe
# from frappe.utils import getdate

# def get_fy_short(date):
#     year = getdate(date).year

#     if getdate(date).month >= 4:
#         start = year
#         end = year + 1
#     else:
#         start = year - 1
#         end = year

#     return f"{str(start)[2:]}-{str(end)[2:]}"   # no dash = shorter

# def si_autoname(doc, method=None):
#     fy = get_fy_short(doc.posting_date or frappe.utils.today())

#     # SUPER SHORT FORMAT (GST SAFE)
#     series = f"SI/{fy}/"

#     doc.name = frappe.model.naming.make_autoname(series + ".#####")


# def get_fy_short(date):
#     year = getdate(date).year

#     if getdate(date).month >= 4:
#         start = year
#         end = year + 1
#     else:
#         start = year - 1
#         end = year

#     return f"{str(start)[2:]}-{str(end)[2:]}"

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
def get_next_number(doctype, series):
    last = frappe.db.sql(f"""
        SELECT name FROM `tab{doctype}`
        WHERE name LIKE %s
        ORDER BY name DESC
        LIMIT 1
    """, (series + "%",))

    if last:
        last_name = last[0][0]
        last_number = int(last_name.split("/")[-1])
        return str(last_number + 1).zfill(5)
    else:
        return "00001"

import frappe
from frappe.utils import getdate

FY_START_DATE = getdate("2026-04-01")

def get_doc_date(doc):
    # 🔥 priority wise check
    if hasattr(doc, "posting_date") and doc.posting_date:
        return getdate(doc.posting_date)

    if hasattr(doc, "transaction_date") and doc.transaction_date:
        return getdate(doc.transaction_date)

    if hasattr(doc, "custom_posting_date") and doc.schedule_date:
        return getdate(doc.custom_posting_date)

    if hasattr(doc, "invoice_date") and doc.invoice_date:
        return getdate(doc.invoice_date)
    
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