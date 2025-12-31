import frappe
from frappe.model.naming import make_autoname

def generate_serials_on_po_submit(doc, method):
    for item in doc.items:

        item_info = frappe.db.get_value("Item", item.item_code, ["has_serial_no", "serial_no_series"], as_dict=True)
        
        if item_info and item_info.has_serial_no:
            generated = []
            
            series_prefix = item_info.serial_no_series if item_info.serial_no_series else f"{item.item_code}-.#####"
            
            for i in range(int(item.qty)):
                sn = make_autoname(series_prefix)
                generated.append(sn)
            
            
            item.custom_generated_serials = "\n".join(generated)
            frappe.db.set_value("Purchase Order Item", item.name, "custom_generated_serials", item.custom_generated_serials)


def apply_purchase_term(doc, method):
    if not doc.custom_purchase_term:
        return

    term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

    total_flat_discount = 0.0
    header_discount_percent = 0.0

    # -------------------------------
    # 1️⃣ ITEM LEVEL : RATE DIFF ONLY
    # -------------------------------
    for item in doc.items:

        # store base rate once (idempotent)
        if not item.custom_base_rate_new:
            item.custom_base_rate_new = item.rate

        adjusted_rate = item.custom_base_rate_new

        for row in sorted(term.purchase_term_charges, key=lambda x: x.sequence):
            if row.charge_type == "Rate Diff":
                adjusted_rate += row.value

        item.rate = adjusted_rate


    # -----------------------------------
    # 2️⃣ DOCUMENT LEVEL : DISCOUNT ONLY
    # -----------------------------------
    for row in term.purchase_term_charges:
        if row.charge_type == "Discount":

            # Percentage discount on Net Total / Grand Total
            if row.value_type == "Percentage":
                header_discount_percent = row.value

            # Flat amount discount
            elif row.value_type == "Amount":
                total_flat_discount += row.value


    # -----------------------------------
    # 3️⃣ PUSH TO ERPNext STANDARD FIELDS
    # -----------------------------------
    if header_discount_percent:
        doc.apply_discount_on = row.apply_on
        doc.additional_discount_percentage = header_discount_percent


    elif total_flat_discount:
        doc.apply_discount_on = row.apply_on
        print(row.value_type)
        print(row.apply_on)
        doc.discount_amount = total_flat_discount


def apply_purchase_term_freight(doc, method):
    if not doc.custom_purchase_term:
        return

    freight_account = get_freight_account(doc.company)

    term = frappe.get_doc("Purchase Term Template", doc.custom_purchase_term)

    for row in term.purchase_term_charges:
        if row.charge_type != "Freight":
            continue

        if any(
            t.account_head == freight_account
            and t.charge_type == "Actual"
            for t in doc.taxes
        ):
            continue

        tax = doc.append("taxes", {})
        tax.charge_type = "Actual"
        tax.category = "Total"
        tax.add_deduct_tax = "Add"
        tax.account_head = freight_account
        tax.tax_amount = row.value
        tax.total=row.value+doc.total
        tax.description = "Freight Charges (Purchase Term)"



def get_freight_account(company):
    account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "custom_is_freight_account": 1,
            "is_group": 0
        },
        "name"
    )

    if not account:
        frappe.throw(
            f"No Freight Account configured for company {company}"
        )

    return account
