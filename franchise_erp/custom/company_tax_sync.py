import frappe


@frappe.whitelist()
def update_gst_hsn_code_taxes(docname, company):

    if not company:
        frappe.throw("Company is required")

    if not docname:
        frappe.throw("Document name is required")

    # Get company abbreviation
    company_abbr = frappe.db.get_value("Company", company, "abbr")

    if not company_abbr:
        frappe.throw(f"Abbreviation not found for Company: {company}")

    # Get HSN SAC and Tax Categories document
    main_doc = frappe.get_doc("Bulk Update HSN SAC and Tax Categories", docname)

    if not main_doc.hsn__and_taxes:
        return "No HSN Codes found to process"

    total_added = 0

    # Remove duplicate HSN codes from child table
    unique_hsn_codes = list(set([row.hsn_code for row in main_doc.hsn__and_taxes if row.hsn_code]))

    for hsn_code in unique_hsn_codes:

        if not frappe.db.exists("GST HSN Code", hsn_code):
            frappe.msgprint(f"GST HSN Code not found: {hsn_code}")
            continue

        gst_doc = frappe.get_doc("GST HSN Code", hsn_code)

        if not gst_doc.taxes:
            continue

        existing_rows = list(gst_doc.taxes)

        for row in existing_rows:

            if not row.item_tax_template:
                continue

            # Remove old company abbreviation
            base_template = row.item_tax_template.split(" - ")[0].strip()

            # Create new template name
            new_template = f"{base_template} - {company_abbr}"

            # Skip if same template
            if row.item_tax_template == new_template:
                continue

            # Check template exists
            if not frappe.db.exists("Item Tax Template", new_template):
                frappe.msgprint(f"Item Tax Template not found: {new_template}")
                continue

            # Prevent duplicate entry
            already_added = any(
                d.item_tax_template == new_template
                for d in gst_doc.taxes
            )

            if already_added:
                continue

            # Append new row
            gst_doc.append("taxes", {
                "item_tax_template": new_template,
                "minimum_net_rate": row.minimum_net_rate,
                "maximum_net_rate": row.maximum_net_rate
            })

            total_added += 1

        gst_doc.save(ignore_permissions=True)

    frappe.db.commit()

    return f"{total_added} GST HSN Code tax rows added successfully"