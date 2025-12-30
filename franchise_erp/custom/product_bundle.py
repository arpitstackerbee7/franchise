import frappe
import random

def set_product_bundle_series(doc, method=None):
    # Do not regenerate if already exists
    if doc.custom_bundle_serial_no:
        return

    # Fetch prefix from Single Doctype
    prefix = frappe.db.get_single_value(
        "TZU Setting",
        "product_bundle_series"
    )

    if not prefix:
        frappe.throw("Product Bundle Series not configured in TZU Setting")

    # Loop until unique value is generated
    while True:
        suffix = str(random.randint(0, 9999)).zfill(4)
        series = f"{prefix}{suffix}"

        # Check duplication
        exists = frappe.db.exists(
            "Product Bundle",
            {"custom_bundle_serial_no": series}
        )

        if not exists:
            # ✅ Persist value in DB
            frappe.db.set_value(
                "Product Bundle",
                doc.name,
                "custom_bundle_serial_no",
                series
            )

            # Also set in memory (for current request)
            doc.custom_bundle_serial_no = series
            break
