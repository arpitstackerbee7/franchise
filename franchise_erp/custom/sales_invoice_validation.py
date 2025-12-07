import frappe
from frappe.utils import getdate

def before_submit(doc, method):

    posting_date = getdate(doc.posting_date)

    # Step 1 — Fetch Stock Taking parent docs with plan_date
    stock_docs = frappe.db.get_all(
        "Stock Taking",
        filters={"docstatus": 1},
        fields=["name", "plan_date"]
    )

    # Convert to map → { stock_taking_name: plan_date }
    plan_map = {d.name: getdate(d.plan_date) for d in stock_docs}

    # Step 2 — Fetch child table items (item codes)
    child_items = frappe.db.get_all(
        "Stock taking Items",
        filters={"parenttype": "Stock Taking", "docstatus": 1},
        fields=["parent", "item_code"]
    )

    # Create mapping → { item_code : stock_taking_doc_name }
    item_map = {}
    for d in child_items:
        item_map[d.item_code] = d.parent

    # Step 3 — Validate each Sales Invoice item
    for row in doc.items:

        if row.item_code not in item_map:
            continue

        st_doc = item_map[row.item_code]
        plan_date = plan_map.get(st_doc)

        if not plan_date:
            continue

        # ❗BLOCK CONDITION → Posting date < Plan date
        if posting_date < plan_date:

            frappe.throw(f"""
<h3 style='color:red;'>Stock Taking Block</h3>

<b>Item Code:</b> {row.item_code}<br>
<b>Item Name:</b> {row.item_name}<br><br>
<b>Stock Taking Doc:</b> {st_doc}<br>
<b>Stock Taking Plan Date:</b> {plan_date.strftime('%d-%m-%Y')}<br>
<b>Sales Invoice Date:</b> {posting_date.strftime('%d-%m-%Y')}<br><br>

You cannot create a Sales Invoice before the Stock Taking plan date.
            """)
