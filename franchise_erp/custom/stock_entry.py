import frappe

@frappe.whitelist()
def get_items_from_material_issues(stock_entry_names):
    if isinstance(stock_entry_names, str):
        stock_entry_names = frappe.parse_json(stock_entry_names)

    if not stock_entry_names:
        return []

    # Fetch items with serial_no and warehouse info
    items = frappe.db.sql("""
        SELECT
            sed.item_code,
            sed.item_name,
            sed.uom,
            sed.qty,
            sed.s_warehouse,
            sed.serial_no,
            se.name as custom_material_issue_id,
            sed.name as custom_material_issue_item_id
        FROM
            `tabStock Entry Detail` sed
        INNER JOIN
            `tabStock Entry` se ON se.name = sed.parent
        WHERE
            se.name IN %(stock_entry_names)s
            AND (sed.custom_material_receipt_id_ IS NULL OR sed.custom_material_receipt_id_ = '')
    """, {"stock_entry_names": tuple(stock_entry_names)}, as_dict=True)

    return items


def validate_intercompany_transfer(doc, method):
    if doc.get("custom_intercompany_stock_transfer"):
        from_company = doc.get("company")
        to_company = doc.get("custom_to_company")

        if not to_company:
            frappe.throw("Target Company should not be empty for Intercompany Stock Transfer.")
        if from_company == to_company:
            frappe.throw("From Company and To Company cannot be the same for Intercompany Stock Transfer.")
        if doc.custom_transaction_type:
            frappe.throw("Transaction type should be empty for Intercompany Stock Transfer.")


def on_submit_stock_entry(doc, method):
    if doc.stock_entry_type == "Material Issue" and doc.custom_intercompany_stock_transfer:
        custom_status = "In Transit"

    elif doc.stock_entry_type == "Material Receipt":
        custom_status = "Transferred"
        updated_mi = set()

        for row in doc.items:
            if row.custom_material_issue_id and row.custom_material_issue_item_id:
                # ✅ update Material Issue child row with receipt reference
                frappe.db.set_value(
                    "Stock Entry Detail",
                    row.custom_material_issue_item_id,
                    {
                        "custom_material_receipt_id_": doc.name,
                        "custom_material_receipt_item_id": row.name
                    }
                )
                updated_mi.add(row.custom_material_issue_id)

                # ✅ parent Material Issue pe bhi reference save karo
                frappe.db.set_value(
                    "Stock Entry",
                    row.custom_material_issue_id,
                    "custom_material_receipt_reference",
                    doc.name
                )

        # ✅ Status check: Delivered / Partially Delivered / In Transit
        for mi in updated_mi:
            total_rows = frappe.db.count("Stock Entry Detail", {"parent": mi})
            linked_rows = frappe.db.count(
                "Stock Entry Detail",
                {"parent": mi, "custom_material_receipt_id_": ["!=", ""]}
            )
            if total_rows == linked_rows:
                frappe.db.set_value("Stock Entry", mi, "custom_status", "Delivered")
            elif linked_rows > 0:
                frappe.db.set_value("Stock Entry", mi, "custom_status", "Partially Delivered")
            else:
                frappe.db.set_value("Stock Entry", mi, "custom_status", "In Transit")

    elif doc.stock_entry_type == "Material Transfer":
        custom_status = "Fully Submitted"

    else:
        custom_status = "Submitted"

    doc.custom_status = custom_status
    frappe.db.set_value("Stock Entry", doc.name, "custom_status", custom_status)


