import frappe
from decimal import Decimal, ROUND_HALF_UP
from frappe.utils import now_datetime


def round2(v):
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def process_journal_entry(doc, method):

    if doc.voucher_type != "Credit Note":
        return

    sinvoices = []
    for a in doc.accounts:
        if a.custom_penalty_invoice and a.custom_penalty_invoice not in ["Summary"]:
            sinvoices.append(a.custom_penalty_invoice)

    if not sinvoices:
        return

    for inv in sinvoices:
        save_full_invoice(doc.company, doc, inv)


def save_full_invoice(company, doc, sales_invoice_name):

    # Fetch Sales Invoice
    si = frappe.get_doc("Sales Invoice", sales_invoice_name)

    # Fetch SIS config
    sis_config = frappe.get_doc("SIS Configuration", {"company": company})
    if not sis_config:
        frappe.throw(f"SIS Configuration missing for Company: {company}")

    # Create main parent
    parent = frappe.new_doc("SIS Processed Sales Invoice")
    parent.company = company
    parent.journal_entry = doc.name
    parent.voucher_type = doc.voucher_type
    parent.sales_invoice = si.name
    parent.customer = si.customer
    parent.posting_date = doc.posting_date

    # Totals
    tq = tb = tm = tog = tig = tiv = 0

    # ---------------------------
    # ITEM LOOP
    # ---------------------------
    for it in si.items:

        qty = Decimal(it.qty or 0)
        mrp = Decimal(it.price_list_rate or 0)
        disc = Decimal(it.discount_percentage or 0)

        # filter
        if disc <= Decimal(sis_config.discount_threshold):
            continue

        # calculations
        sale = (mrp - (mrp * disc / 100)) * qty

        ogst_p = 0
        if it.item_tax_rate:
            taxes = frappe.parse_json(it.item_tax_rate)
            ogst_p = sum([Decimal(v) for v in taxes.values()])

        ogst_v = (sale * ogst_p) / (100 + ogst_p) if ogst_p else 0
        net = sale - ogst_v

        mar_p = Decimal(sis_config.discounted_margin if disc > 0 else sis_config.fresh_margin)
        mar_v = (net * mar_p) / 100
        base = net - mar_v

        igst_p = Decimal("5.0")
        igst_v = (base * igst_p) / 100
        inv = base + igst_v

        # add child row
        parent.append("items", {
            "item": it.item_code,
            "name1": it.item_name,
            "qty": float(qty),
            "mrp": float(mrp),
            "disc": float(disc),
            "sale": float(sale),
            "ogst_p": float(ogst_p),
            "ogst_v": float(ogst_v),
            "net": float(net),
            "mar_p": float(mar_p),
            "mar_v": float(mar_v),
            "base": float(base),
            "igst_p": float(igst_p),
            "igst_v": float(igst_v),
            "inv": float(inv),
        })

        # Totals
        tq += float(qty)
        tb += float(base)
        tm += float(mar_v)
        tog += float(ogst_v)
        tig += float(igst_v)
        tiv += float(inv)

        # ----------------------------------------
        # UPDATE Sales Invoice Item AT SAME TIME
        # ----------------------------------------
        frappe.db.set_value(
            "Sales Invoice Item",
            it.name,
            {
                "custom_sis_processed": 1,
                "custom_sis_processed_on": now_datetime()
            }
        )

    # Assign totals
    parent.total_qty = tq
    parent.total_base = tb
    parent.total_margin = tm
    parent.total_ogst = tog
    parent.total_igst = tig
    parent.total_inv = tiv

    # Save
    parent.insert(ignore_permissions=True)
    frappe.db.commit()
