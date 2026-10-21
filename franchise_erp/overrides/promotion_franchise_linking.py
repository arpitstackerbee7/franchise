import json
import frappe


@frappe.whitelist()
def merge_franchises_upload(docname, rows):
    doc = frappe.get_doc("Promotion Franchise linking", docname)
    doc.check_permission("write")

    if isinstance(rows, str):
        rows = json.loads(rows)

    if not isinstance(rows, list) or len(rows) > 5000:
        frappe.throw("Invalid CSV data or more than 5000 rows.")

    existing = {
        str(row.franchise).strip().casefold()
        for row in doc.franchises
        if row.franchise
    }

    added = 0
    skipped = 0

    for item in rows:
        if not isinstance(item, dict):
            continue

        company = str(item.get("franchise") or "").strip()

        if not company:
            continue

        key = company.casefold()

        if key in existing:
            skipped += 1
            continue

        # Validate the Link field against Company
        company_name = frappe.db.get_value(
            "Company", {"name": company}, "name"
        )

        if not company_name:
            frappe.throw(
                f"Company '{frappe.utils.escape_html(company)}' does not exist."
            )

        raw_disable = str(item.get("disable") or "").strip().lower()
        disable = 1 if raw_disable in ("1", "true", "yes", "y") else 0

        doc.append("franchises", {
            "franchise": company_name,
            "disable": disable
        })

        existing.add(key)
        added += 1

    if added:
        doc.save()

    return {"added": added, "skipped": skipped}
