# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.utils import get_site_path
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter

from franchise_erp.franchise_erp.report.custom_stock_report.custom_stock_report import execute


@frappe.whitelist()
def export_custom_stock_report_with_images(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    columns, data = execute(filters)

    wb = Workbook()
    ws = wb.active
    ws.title = "Custom Stock Report"

    # Write headers
    for col_idx, col in enumerate(columns, start=1):
        ws.cell(row=1, column=col_idx, value=col.get("label"))

    image_col_idx = None
    for idx, col in enumerate(columns):
        if col.get("fieldname") == "image":
            image_col_idx = idx
            break

    # Write data rows
    for row_idx, row in enumerate(data, start=2):
        for col_idx, col in enumerate(columns, start=1):
            fieldname = col.get("fieldname")
            value = row.get(fieldname)

            if image_col_idx is not None and (col_idx - 1) == image_col_idx:
                if value:
                    file_path = None
                    if value.startswith("/files/"):
                        file_path = get_site_path("public", value.lstrip("/"))
                    elif value.startswith("/private/files/"):
                        file_path = get_site_path(value.lstrip("/"))

                    if file_path and os.path.exists(file_path):
                        try:
                            img = XLImage(file_path)
                            img.width = 60
                            img.height = 60
                            cell_ref = f"{get_column_letter(col_idx)}{row_idx}"
                            ws.add_image(img, cell_ref)
                        except Exception:
                            pass
                ws.row_dimensions[row_idx].height = 50
            else:
                ws.cell(row=row_idx, column=col_idx, value=value)

    # Set column widths
    for col_idx, col in enumerate(columns, start=1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(15, (col.get("width", 100) or 100) / 7)

    file_name = f"custom_stock_report_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(get_site_path("private", "files"), file_name)
    wb.save(file_path)

    with open(file_path, "rb") as f:
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "is_private": 1,
            "content": f.read(),
        })
        file_doc.save(ignore_permissions=True)

    os.remove(file_path)

    return file_doc.file_url