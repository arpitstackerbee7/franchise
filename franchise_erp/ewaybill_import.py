
import frappe
from html.parser import HTMLParser
from io import BytesIO
from datetime import datetime
from frappe.utils import getdate


DOCTYPE = "Advance e-Waybill Log"


class TableParser(HTMLParser):
    """Extract table rows and cell text from HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "tr":
            self.row = []

        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell).strip())
            self.cell = None

        elif tag == "tr" and self.row is not None:
            if any(value.strip() for value in self.row):
                self.rows.append(self.row)
            self.row = None


def normalize(value):
    """Normalize column headings for matching."""
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


@frappe.whitelist()
def import_ewaybill_html_xls():
    """Import the GST portal's HTML-based XLS export."""

    frappe.has_permission(DOCTYPE, "create", throw=True)

    uploaded = frappe.request.files.get("file")
    if not uploaded:
        frappe.throw("Please upload the GST E-Way Bill file.")

    raw = uploaded.read()

    # The portal export is HTML despite having an .xls extension.
    sample = raw[:500].lower()
    if b"<html" not in sample and b"<table" not in sample:
        frappe.throw(
            "This file does not appear to contain an HTML table. "
            "Please verify the downloaded file."
        )

    html = raw.decode("utf-8-sig", errors="replace")

    parser = TableParser()
    parser.feed(html)

    if len(parser.rows) < 2:
        frappe.throw("No data rows found in the uploaded HTML file.")

    # Match portal column headings with DocType fieldnames and labels.
    meta = frappe.get_meta(DOCTYPE)
    heading_map = {}

    for field in meta.fields:
        if not field.fieldname:
            continue

        heading_map[normalize(field.fieldname)] = field.fieldname
        if field.label:
            heading_map[normalize(field.label)] = field.fieldname

    # Add aliases after checking the actual GST portal headings.
    aliases = {
        "ewbno": "ewb_no",
        "ewaybillno": "ewb_no",
        "ewaybillnumber": "ewb_no",
        "documentno": "doc_no",
        "docno": "doc_no",
        "documentdate": "doc_date",
        "ewbdate": "ewb_date",
    }

    heading_map.update(aliases)

    # Locate the row containing recognizable column headings.
    header_index = None
    mapped_headers = []

    for index, row in enumerate(parser.rows):
        mapped = [heading_map.get(normalize(cell)) for cell in row]

        if "ewb_no" in mapped and "doc_no" in mapped:
            header_index = index
            mapped_headers = mapped
            break

    if header_index is None:
        frappe.throw(
            "Could not identify the E-Way Bill and Document No columns. "
            "Check the portal's column headings and update the mapping."
        )

    inserted = 0
    skipped = 0
    errors = []

    for row_number, row in enumerate(
        parser.rows[header_index + 1:],
        start=header_index + 2,
    ):
        values = {}

        for index, fieldname in enumerate(mapped_headers):
            if fieldname and index < len(row):
                value = row[index].strip()
                if value:
                    values[fieldname] = value

        ewb_no = values.get("ewb_no")
        if not ewb_no:
            continue

        try:
            # Prevent duplicate E-Way Bill records.
            if frappe.db.exists(DOCTYPE, {"ewb_no": ewb_no}):
                skipped += 1
                continue

            # Convert common portal date formats.
            for fieldname in ("ewb_date", "doc_date", "valid_till_date"):
                value = values.get(fieldname)
                if value:
                    parsed = None
                    for fmt in (
                        "%d/%m/%Y",
                        "%d-%m-%Y",
                        "%d/%m/%Y %H:%M:%S",
                        "%Y-%m-%d",
                    ):
                        try:
                            parsed = datetime.strptime(value, fmt).date()
                            break
                        except ValueError:
                            pass

                    if parsed:
                        values[fieldname] = parsed.isoformat()

            doc = frappe.get_doc({
                "doctype": DOCTYPE,
                **values,
            })
            doc.insert()

            inserted += 1

        except Exception:
            errors.append({
                "row": row_number,
                "ewb_no": ewb_no,
                "error": frappe.get_traceback()[-1000:],
            })

    frappe.db.commit()

    return {
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "failed": len(errors),
        "errors": errors[:20],
    }