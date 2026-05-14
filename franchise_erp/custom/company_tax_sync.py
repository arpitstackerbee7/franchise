# # import frappe


# # @frappe.whitelist()
# # def update_gst_hsn_code_taxes(docname, company):

# #     if not company:
# #         frappe.throw("Company is required")

# #     if not docname:
# #         frappe.throw("Document name is required")

# #     # Get company abbreviation
# #     company_abbr = frappe.db.get_value("Company", company, "abbr")

# #     if not company_abbr:
# #         frappe.throw(f"Abbreviation not found for Company: {company}")

# #     # Get HSN SAC and Tax Categories document
# #     main_doc = frappe.get_doc("Bulk Update HSN SAC and Tax Categories", docname)

# #     if not main_doc.hsn__and_taxes:
# #         return "No HSN Codes found to process"

# #     total_added = 0

# #     # Remove duplicate HSN codes from child table
# #     unique_hsn_codes = list(set([row.hsn_code for row in main_doc.hsn__and_taxes if row.hsn_code]))

# #     for hsn_code in unique_hsn_codes:

# #         if not frappe.db.exists("GST HSN Code", hsn_code):
# #             frappe.msgprint(f"GST HSN Code not found: {hsn_code}")
# #             continue

# #         gst_doc = frappe.get_doc("GST HSN Code", hsn_code)

# #         if not gst_doc.taxes:
# #             continue

# #         existing_rows = list(gst_doc.taxes)

# #         for row in existing_rows:

# #             if not row.item_tax_template:
# #                 continue

# #             # Remove old company abbreviation
# #             base_template = row.item_tax_template.split(" - ")[0].strip()

# #             # Create new template name
# #             new_template = f"{base_template} - {company_abbr}"

# #             # Skip if same template
# #             if row.item_tax_template == new_template:
# #                 continue

# #             # Check template exists
# #             if not frappe.db.exists("Item Tax Template", new_template):
# #                 frappe.msgprint(f"Item Tax Template not found: {new_template}")
# #                 continue

# #             # Prevent duplicate entry
# #             already_added = any(
# #                 d.item_tax_template == new_template
# #                 for d in gst_doc.taxes
# #             )

# #             if already_added:
# #                 continue

# #             # Append new row
# #             gst_doc.append("taxes", {
# #                 "item_tax_template": new_template,
# #                 "minimum_net_rate": row.minimum_net_rate,
# #                 "maximum_net_rate": row.maximum_net_rate
# #             })

# #             total_added += 1

# #         gst_doc.save(ignore_permissions=True)

# #     frappe.db.commit()

# #     return f"{total_added} GST HSN Code tax rows added successfully"



# import frappe


# @frappe.whitelist()
# def update_gst_hsn_code_taxes(docname, company):

#     if not company:
#         frappe.throw("Company is required")

#     if not docname:
#         frappe.throw("Document name is required")

#     process_company_hsn_update(docname, company)

#     return f"GST HSN Code taxes updated successfully for {company}"


# @frappe.whitelist()
# def bulk_update_gst_hsn_code_taxes(docname):

#     if not docname:
#         frappe.throw("Document name is required")

#     # Fetch all non-group companies
#     companies = frappe.get_all(
#         "Company",
#         filters={"is_group": 0},
#         pluck="name"
#     )

#     if not companies:
#         return "No companies found"

#     total_companies = 0
#     total_rows_added = 0

#     for company in companies:

#         added_rows = process_company_hsn_update(docname, company)

#         total_rows_added += added_rows
#         total_companies += 1

#     frappe.db.commit()

#     return f"""
#         GST HSN Code taxes updated successfully.<br><br>
#         Total Companies Processed: {total_companies}<br>
#         Total Tax Rows Added: {total_rows_added}
#     """


# def process_company_hsn_update(docname, company):

#     # Get company abbreviation
#     company_abbr = frappe.db.get_value("Company", company, "abbr")

#     if not company_abbr:
#         return 0

#     # Get Main Doc
#     main_doc = frappe.get_doc("Bulk Update HSN SAC and Tax Categories", docname)

#     if not main_doc.hsn__and_taxes:
#         return 0

#     total_added = 0

#     # Remove duplicate HSN Codes
#     unique_hsn_codes = list(set([
#         row.hsn_code for row in main_doc.hsn__and_taxes
#         if row.hsn_code
#     ]))

#     for hsn_code in unique_hsn_codes:

#         if not frappe.db.exists("GST HSN Code", hsn_code):
#             continue

#         gst_doc = frappe.get_doc("GST HSN Code", hsn_code)

#         if not gst_doc.taxes:
#             continue

#         existing_rows = list(gst_doc.taxes)

#         for row in existing_rows:

#             if not row.item_tax_template:
#                 continue

#             # Remove old company abbreviation
#             base_template = row.item_tax_template.split(" - ")[0].strip()

#             # Create new template
#             new_template = f"{base_template} - {company_abbr}"

#             # Skip if same
#             if row.item_tax_template == new_template:
#                 continue

#             # Check Item Tax Template Exists
#             if not frappe.db.exists("Item Tax Template", new_template):
#                 continue

#             # Prevent Duplicate Entry
#             already_added = any(
#                 d.item_tax_template == new_template
#                 for d in gst_doc.taxes
#             )

#             if already_added:
#                 continue

#             # Append Row
#             gst_doc.append("taxes", {
#                 "item_tax_template": new_template,
#                 "minimum_net_rate": row.minimum_net_rate,
#                 "maximum_net_rate": row.maximum_net_rate
#             })

#             total_added += 1

#         gst_doc.save(ignore_permissions=True)

#     return total_added



import frappe


@frappe.whitelist()
def update_gst_hsn_code_taxes(docname, company):

    if not company:
        frappe.throw("Company is required")

    if not docname:
        frappe.throw("Document name is required")

    added_rows = process_company_hsn_update(docname, company)

    frappe.db.commit()

    return f"""
        GST HSN Code taxes updated successfully for {company}.<br>
        Total Tax Rows Added: {added_rows}
    """


@frappe.whitelist()
def bulk_update_gst_hsn_code_taxes(docname):

    if not docname:
        frappe.throw("Document name is required")

    # Get all companies with abbreviation
    companies = frappe.get_all(
        "Company",
        filters={"is_group": 0},
        fields=["name", "abbr"]
    )

    if not companies:
        return "No companies found"

    # Get main document once
    main_doc = frappe.get_doc(
        "Bulk Update HSN SAC and Tax Categories",
        docname
    )

    if not main_doc.hsn__and_taxes:
        return "No HSN Codes found"

    # Unique HSN Codes
    unique_hsn_codes = list({
        row.hsn_code
        for row in main_doc.hsn__and_taxes
        if row.hsn_code
    })

    total_rows_added = 0

    # Process each HSN only once
    for hsn_code in unique_hsn_codes:

        if not frappe.db.exists("GST HSN Code", hsn_code):
            continue

        gst_doc = frappe.get_doc("GST HSN Code", hsn_code)

        if not gst_doc.taxes:
            continue

        existing_templates = {
            d.item_tax_template
            for d in gst_doc.taxes
            if d.item_tax_template
        }

        rows_to_add = []

        for row in gst_doc.taxes:

            if not row.item_tax_template:
                continue

            base_template = row.item_tax_template.split(" - ")[0].strip()

            for company in companies:

                if not company.abbr:
                    continue

                new_template = f"{base_template} - {company.abbr}"

                # Skip existing
                if new_template in existing_templates:
                    continue

                # Check template exists
                if not frappe.db.exists(
                    "Item Tax Template",
                    new_template
                ):
                    continue

                rows_to_add.append({
                    "item_tax_template": new_template,
                    "minimum_net_rate": row.minimum_net_rate,
                    "maximum_net_rate": row.maximum_net_rate
                })

                existing_templates.add(new_template)

        # Bulk append
        for d in rows_to_add:
            gst_doc.append("taxes", d)

        if rows_to_add:
            gst_doc.save(ignore_permissions=True)
            total_rows_added += len(rows_to_add)

    frappe.db.commit()

    return f"""
        GST HSN Code taxes updated successfully.<br><br>
        Total Companies Processed: {len(companies)}<br>
        Total Tax Rows Added: {total_rows_added}
    """


def process_company_hsn_update(docname, company):

    company_abbr = frappe.db.get_value(
        "Company",
        company,
        "abbr"
    )

    if not company_abbr:
        return 0

    main_doc = frappe.get_doc(
        "Bulk Update HSN SAC and Tax Categories",
        docname
    )

    if not main_doc.hsn__and_taxes:
        return 0

    unique_hsn_codes = list({
        row.hsn_code
        for row in main_doc.hsn__and_taxes
        if row.hsn_code
    })

    total_added = 0

    for hsn_code in unique_hsn_codes:

        if not frappe.db.exists("GST HSN Code", hsn_code):
            continue

        gst_doc = frappe.get_doc("GST HSN Code", hsn_code)

        if not gst_doc.taxes:
            continue

        existing_templates = {
            d.item_tax_template
            for d in gst_doc.taxes
            if d.item_tax_template
        }

        rows_to_add = []

        for row in gst_doc.taxes:

            if not row.item_tax_template:
                continue

            base_template = row.item_tax_template.split(" - ")[0].strip()

            new_template = f"{base_template} - {company_abbr}"

            if new_template in existing_templates:
                continue

            if not frappe.db.exists(
                "Item Tax Template",
                new_template
            ):
                continue

            rows_to_add.append({
                "item_tax_template": new_template,
                "minimum_net_rate": row.minimum_net_rate,
                "maximum_net_rate": row.maximum_net_rate
            })

            existing_templates.add(new_template)

        # Append once
        for d in rows_to_add:
            gst_doc.append("taxes", d)

        if rows_to_add:
            gst_doc.save(ignore_permissions=True)
            total_added += len(rows_to_add)

    return total_added