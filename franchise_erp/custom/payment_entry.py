import frappe
from frappe.utils import getdate
from frappe.utils import today

def apply_early_payment_discount(doc, method):
    if doc.party_type != "Supplier":
        return

    for ref in doc.references:
        if ref.reference_doctype != "Purchase Invoice":
            continue

        pi = frappe.get_doc("Purchase Invoice", ref.reference_name)

        # ✅ Decide last eligible discount date
        discount_upto_date = (
            pi.custom_buffer_due_date or pi.due_date
        )

        # Normalize & compare dates
        if getdate(doc.posting_date) > getdate(discount_upto_date):
            continue

        supplier = frappe.db.get_value(
            "Supplier",
            pi.supplier,
            ["custom_allow_cash_discount_", "custom_applied_on"],
            as_dict=True
        )

        if not supplier or not supplier.custom_allow_cash_discount_:
            continue

        discount_percent = supplier.custom_allow_cash_discount_

        # ✅ Decide discount base
        if supplier.custom_applied_on == "Net Total":
            invoice_base = pi.net_total
        elif supplier.custom_applied_on == "Grand Total":
            invoice_base = pi.grand_total
        else:
            continue

        # ✅ Maximum discount allowed per invoice
        max_discount = invoice_base * discount_percent / 100

        already_used = pi.custom_cash_discount_applied or 0
        remaining = max_discount - already_used

        if remaining <= 0:
            continue

        # ✅ Proportional discount on this payment
        eligible_base = ref.allocated_amount
        discount_on_payment = eligible_base * discount_percent / 100

        discount = min(discount_on_payment, remaining)

        if discount <= 0:
            continue

        # 🔒 Track discount usage (one-time, cumulative)
        pi.db_set(
            "custom_cash_discount_applied",
            already_used + discount,
            update_modified=False
        )

        # 📘 Create Debit Note
        create_discount_debit_note(pi, discount)




def create_discount_debit_note(pi, discount_amount):

    template_name = frappe.db.get_value(
        "Journal Entry Template",
        {
            "voucher_type": "Debit Note"
        },
        "name"
    )

    if not template_name:
        frappe.throw("No Journal Entry Template found with Voucher Type = Debit Note")

    template = frappe.get_doc("Journal Entry Template", template_name)

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Debit Note"
    je.posting_date = today()

    supplier_line_found = False

    for row in template.accounts:
        acc = {
            "account": row.account
        }

        # ✅ Supplier Payable line
        if row.account == pi.credit_to:
            supplier_line_found = True
            acc.update({
                "debit_in_account_currency": discount_amount,
                "party_type": "Supplier",
                "party": pi.supplier,
                "reference_type": "Purchase Invoice",
                "reference_name": pi.name
            })

        # ✅ Discount / Income line
        else:
            acc.update({
                "credit_in_account_currency": discount_amount
            })

        je.append("accounts", acc)

    if not supplier_line_found:
        frappe.throw(
            f"Debit Note template must contain supplier payable account: {pi.credit_to}"
        )

    je.insert()
