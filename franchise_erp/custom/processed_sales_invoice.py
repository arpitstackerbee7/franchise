import frappe
from decimal import Decimal, ROUND_HALF_UP
from frappe.utils import now_datetime

# -----------------------------
# Helper: round to 2 decimals
# -----------------------------
def round2(v):
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# -----------------------------
# On submit hook for Journal Entry
# -----------------------------
def process_journal_entry(doc, method=None):
    """
    This should be attached to Journal Entry on_submit.
    It finds all accounts lines with custom_penalty_invoice (except 'Summary')
    and saves those Sales Invoices into SIS Processed Sales Invoice.
    """
    # Ensure this runs only for Credit Note JE (as in your logic)
    if getattr(doc, "voucher_type", "") != "Credit Note":
        return

    sinvoices = []
    for a in doc.get("accounts") or []:
        inv = a.get("custom_penalty_invoice")
        if inv and inv != "Summary":
            sinvoices.append(inv)

    if not sinvoices:
        return

    company = getattr(doc, "company", None)
    # Process each invoice once
    for inv_name in list(dict.fromkeys(sinvoices)):
        try:
            save_full_invoice(company, doc, inv_name)
        except Exception:
            # Log and continue, don't break processing for other invoices
            frappe.log_error(frappe.get_traceback(), f"SIS Process Save Error: {inv_name}")

# -----------------------------
# Save full invoice with rounding
# -----------------------------
def save_full_invoice(company, journal_doc, sales_invoice_name):
    # Fetch Sales Invoice doc
    si = frappe.get_doc("Sales Invoice", sales_invoice_name)

    # Fetch SIS Configuration for this company
    sis_config = frappe.db.get_value(
        "SIS Configuration",
        {"company": company},
        ["discounted_margin", "fresh_margin", "discount_threshold"],
        as_dict=True
    )
    if not sis_config:
        frappe.throw(f"SIS Configuration missing for Company: {company}")

    # Create parent doc
    parent = frappe.new_doc("SIS Processed Sales Invoice")
    parent.company = company
    parent.journal_entry = journal_doc.name
    parent.voucher_type = journal_doc.voucher_type
    parent.sales_invoice = si.name
    parent.customer = si.customer
    parent.posting_date = journal_doc.posting_date

    # Totals (Decimal)
    tq = tb = tm = tog = tig = tiv = Decimal("0.00")

    # Loop invoice items
    for it in si.get("items") or []:
        # qty, mrp, discount
        qty = Decimal(str(it.get("qty") or 0))
        # Use price_list_rate if available else rate
        mrp = Decimal(str(it.get("price_list_rate") or it.get("rate") or 0))
        disc = Decimal(str(it.get("discount_percentage") or 0))

        # Skip if below threshold
        if disc <= Decimal(str(sis_config.get("discount_threshold") or 0)):
            continue

        # Sale calculation: (mrp - mrp*disc/100) * qty
        sale = (mrp - (mrp * disc / Decimal("100"))) * qty

        # OGST percent (item_tax_rate may be JSON string mapping tax names to rates)
        ogst_p = Decimal("0.00")
        item_tax_rate = it.get("item_tax_rate")
        if item_tax_rate:
            try:
                taxes = frappe.parse_json(item_tax_rate)
                # taxes might be { "IGST": "18", ... } or { "rate": 18 } - handle sums
                if isinstance(taxes, dict):
                    # sum of values
                    ogst_p = sum([Decimal(str(v)) for v in taxes.values()])
                else:
                    ogst_p = Decimal(str(taxes))
            except Exception:
                # fallback: try cast to Decimal
                try:
                    ogst_p = Decimal(str(item_tax_rate))
                except Exception:
                    ogst_p = Decimal("0.00")

        # OGST value: portion of sale that is tax (sale contains tax included or excluded based on logic)
        ogst_v = (sale * ogst_p) / (Decimal("100") + ogst_p) if ogst_p else Decimal("0.00")
        net = sale - ogst_v

        # margin percent from config
        mar_p = Decimal(str(sis_config.get("discounted_margin"))) if disc > 0 else Decimal(str(sis_config.get("fresh_margin")))
        mar_v = (sale * mar_p) / Decimal("100") if mar_p else Decimal("0.00")
        base = net - mar_v

        # IGST percent (your code used fixed 5 as example); keep same or fetch from somewhere
        igst_p = Decimal("5.0")
        igst_v = (base * igst_p) / Decimal("100") if base else Decimal("0.00")
        inv_val = base + igst_v

        # Round everything
        qty = round2(qty)
        mrp = round2(mrp)
        disc = round2(disc)
        sale = round2(sale)
        ogst_p = round2(ogst_p)
        ogst_v = round2(ogst_v)
        net = round2(net)
        mar_p = round2(mar_p)
        mar_v = round2(mar_v)
        base = round2(base)
        igst_p = round2(igst_p)
        igst_v = round2(igst_v)
        inv_val = round2(inv_val)

        # Append child row (convert to float for float fields)
        parent.append("items", {
            "item": it.get("item_code"),
            "name1": it.get("item_name"),
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
            "inv": float(inv_val),
        })

        # Update totals
        tq += qty
        tb += base
        tm += mar_v
        tog += ogst_v
        tig += igst_v
        tiv += inv_val

        # Mark Sales Invoice Item as processed (fields you already had)
        try:
            frappe.db.set_value("Sales Invoice Item", it.get("name"),
                                {"custom_sis_processed": 1, "custom_sis_processed_on": now_datetime()})
        except Exception:
            frappe.log_error(f"Could not update Sales Invoice Item {it.get('name')} for SI {si.name}")

    # Assign totals to parent (rounded)
    parent.total_qty = float(round2(tq))
    parent.total_base = float(round2(tb))
    parent.total_margin = float(round2(tm))
    parent.total_ogst = float(round2(tog))
    parent.total_igst = float(round2(tig))
    parent.total_inv = float(round2(tiv))

    # Save parent
    parent.insert(ignore_permissions=True)
    frappe.db.commit()
