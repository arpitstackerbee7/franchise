# import frappe
# from frappe.utils import flt, rounded

# def round1(v):
#     return float(f"{v:.1f}")

# def get_sis_margin(company):
#     margin = frappe.db.get_value(
#         "SIS Configuration",
#         {"company": company},
#         "fresh_margin"
#     )
#     return flt(margin or 0)

# def calculate_margin_and_totals(doc, method=None):
#     frappe.log_error("PYTHON CALLED ✔", "MARGIN DEBUG")

#     customer_company = frappe.db.get_value(
#         "Customer", doc.customer, "represents_company"
#     ) if doc.customer else None

#     company = customer_company or doc.company
#     margin_percent = get_sis_margin(company)

#     total_invoice_amount = 0

#     for item in doc.items:
#         rate = flt(item.rate)
#         qty = flt(item.qty)
#         net_rate = flt(item.net_rate)

#         if not net_rate:
#             continue

#         item.custom_margins_ = margin_percent
#         margin_amount = (rate * margin_percent / 100) * qty
#         item.custom_margin_amount = flt(margin_amount)
#         final_amount = (net_rate * qty) - margin_amount
#         item.custom_total_invoice_amount = flt(final_amount)
#         item.rate = flt(final_amount)
#         item.amount = flt(final_amount)
#         total_invoice_amount += final_amount

#     # Call standard calculation first
#     doc.calculate_taxes_and_totals()

#     # Override totals AFTER ERPNext calculation
#     doc.custom_total_invoice_amount = flt(total_invoice_amount)
#     doc.round_total = rounded(total_invoice_amount)
#     doc.rounded_total = rounded(total_invoice_amount)
#     doc.outstanding_amount = rounded(total_invoice_amount)

#     # Also override grand total
#     doc.grand_total = rounded(total_invoice_amount)
#     doc.base_grand_total = rounded(total_invoice_amount)

# # BEFORE SAVE
# def before_save(doc, method=None):
#     calculate_margin_and_totals(doc, method)
import frappe
from frappe.utils import flt, rounded

def round1(v):
    return float(f"{v:.1f}")

def get_sis_margin(company):
    margin = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        "fresh_margin"
    )
    return flt(margin or 0)

# def calculate_margin_and_totals(doc, method=None):

#     # ⛔ DEBUG LOG
#     frappe.log_error("PYTHON CALLED ✔", "MARGIN DEBUG")

#     # -------------------------
#     # 1️⃣ CHECK LOGIN USER COMPANY
#     # -------------------------
#     login_user_company = frappe.db.get_value(
#         "User",
#         frappe.session.user,
#         "company"
#     )

#     # -------------------------
#     # 2️⃣ IF USER COMPANY EXISTS IN SIS CONFIG → NO MARGIN APPLY
#     # -------------------------
#     sis_exists = frappe.db.exists(
#         "SIS Configuration",
#         {"company": login_user_company}
#     )

#     if sis_exists:
#         frappe.log_error("NO MARGIN APPLIED (Branch User)", "MARGIN DEBUG")

#         # Remove margin for branch users
#         for item in doc.items:
#             item.custom_margins_ = 0
#             item.custom_margin_amount = 0
#             item.custom_total_invoice_amount = flt(item.net_amount or item.amount)

#         # Recalculate totals
#         doc.calculate_taxes_and_totals()
#         return   # ⛔ STOP Execution (No margin applied)

#     # -------------------------
#     # 3️⃣ NORMAL (HEAD OFFICE) FLOW → MARGIN APPLY
#     # -------------------------

#     frappe.log_error("MARGIN APPLIED (HO User)", "MARGIN DEBUG")

#     customer_company = frappe.db.get_value(
#         "Customer", doc.customer, "represents_company"
#     ) if doc.customer else None

#     company = customer_company or doc.company
#     margin_percent = get_sis_margin(company)

#     total_invoice_amount = 0

#     for item in doc.items:
#         rate = flt(item.rate)
#         qty = flt(item.qty)
#         net_rate = flt(item.net_rate)

#         if not net_rate:
#             continue

#         item.custom_margins_ = margin_percent
#         margin_amount = (rate * margin_percent / 100) * qty
#         item.custom_margin_amount = flt(margin_amount)

#         final_amount = (net_rate * qty) - margin_amount

#         item.custom_total_invoice_amount = flt(final_amount)
#         item.rate = flt(final_amount)
#         item.amount = flt(final_amount)

#         total_invoice_amount += final_amount

#     # Standard ERPNext recalculation
#     doc.calculate_taxes_and_totals()

#     # Override totals
#     doc.custom_total_invoice_amount = rounded(total_invoice_amount)
#     doc.round_total = rounded(total_invoice_amount)
#     doc.rounded_total = rounded(total_invoice_amount)
#     doc.outstanding_amount = rounded(total_invoice_amount)
#     doc.grand_total = rounded(total_invoice_amount)

def calculate_margin_and_totals(doc, method=None):

    frappe.log_error("PYTHON CALLED ✔", "MARGIN DEBUG")

    # -------------------------
    # 1️⃣ CHECK LOGIN USER COMPANY
    # -------------------------
    login_user_company = frappe.db.get_value(
        "User",
        frappe.session.user,
        "company"
    )

    # -------------------------
    # 2️⃣ BRANCH USER → NO MARGIN
    # -------------------------
    sis_exists = frappe.db.exists(
        "SIS Configuration",
        {"company": login_user_company}
    )

    if sis_exists:
        frappe.log_error("NO MARGIN APPLIED (Branch User)", "MARGIN DEBUG")

        total_invoice_amount = 0

        for item in doc.items:
            item.custom_margins_ = 0
            item.custom_margin_amount = 0

            base_amount = flt(item.net_amount or item.amount)
            item.custom_total_invoice_amount = base_amount
            total_invoice_amount += base_amount

        doc.calculate_taxes_and_totals()

        doc.custom_total_invoice_amount = rounded(total_invoice_amount)
        doc.grand_total = rounded(total_invoice_amount)
        doc.rounded_total = rounded(total_invoice_amount)
        doc.round_total = rounded(total_invoice_amount)
        doc.outstanding_amount = rounded(total_invoice_amount)

        return

    # -------------------------
    # 3️⃣ HEAD OFFICE → APPLY MARGIN
    # -------------------------
    frappe.log_error("MARGIN APPLIED (HO User)", "MARGIN DEBUG")

    customer_company = frappe.db.get_value(
        "Customer", doc.customer, "represents_company"
    ) if doc.customer else None

    company = customer_company or doc.company
    margin_percent = get_sis_margin(company)

    total_invoice_amount = 0

    for item in doc.items:
        net_rate = flt(item.net_rate)
        rate = flt(item.rate)
        qty = flt(item.qty)

        if not net_rate or not qty:
            continue

        item.custom_margins_ = margin_percent

        margin_amount = (rate * margin_percent / 100) * qty
        item.custom_margin_amount = flt(margin_amount)

        # 🔹 FINAL AMOUNT AFTER MARGIN
        final_amount = (net_rate * qty) - margin_amount

        item.custom_total_invoice_amount = flt(final_amount)
        total_invoice_amount += final_amount

        # ❌ DO NOT TOUCH:
        # item.rate
        # item.amount
        # item.net_rate

    # 🔹 Let ERPNext calculate normally
    doc.calculate_taxes_and_totals()

    # -------------------------
    # 4️⃣ OVERRIDE ONLY TOTALS
    # -------------------------
    doc.custom_total_invoice_amount = round(final_amount)
    doc.grand_total = round(final_amount)
    doc.rounded_total = round(final_amount)
    doc.round_total = round(final_amount)
    doc.outstanding_amount = round(final_amount)


# BEFORE SAVE
def before_save(doc, method=None):
    calculate_margin_and_totals(doc, method)

def force_margin_totals_after_submit(doc, method=None):

    if not doc.custom_total_invoice_amount:
        return

    final_total = flt(doc.custom_total_invoice_amount)

    frappe.db.set_value(
        "Sales Invoice",
        doc.name,
        {
            "grand_total": final_total,
            "rounded_total": final_total,
            "outstanding_amount": final_total,
            "base_grand_total": final_total,
            "base_rounded_total": final_total
        },
        update_modified=False
    )
