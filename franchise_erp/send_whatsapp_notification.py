import frappe
import requests

def send_text_msg_on_whatsapp_sales_invoice(doc, method=None):

    mobile = frappe.db.get_value("Customer", doc.customer, "custom_mobile_no_customer")

    if not mobile:
        return

    chatId = "91" + mobile + "@c.us"

    total_qty = 0
    for item in doc.items:
        total_qty += item.qty

    # message
    message = f"""
        Hello {doc.customer},

        Your Sales Invoice has been generated.

        Invoice No : {doc.name}
        Total Qty : {total_qty}
        Grand Total : {doc.grand_total}

        Thank you!
        """

    url = "https://7103.api.greenapi.com/waInstance7103539592/sendMessage/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

    payload = {
        "chatId": chatId,
        "message": message
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        frappe.log_error(str(e), "Whatsapp Error")




import frappe
import os
import requests

# --- PDF Generate function ---
def generate_pdf(doc):
    """
    Generate PDF from Sales Invoice Print Format
    """
    pdf_data = frappe.get_print(
        doctype=doc.doctype,
        name=doc.name,
        print_format="Sales Invoice Print Format",
        no_letterhead=1,
        as_pdf=True
    )
    return pdf_data

# --- WhatsApp PDF Send function ---
def send_pdf_on_whatsapp_sales_invoice(doc, method=None):
    """
    Send Sales Invoice PDF to Customer WhatsApp after submit
    """
    # Get customer's mobile number
    mobile = frappe.db.get_value("Customer", doc.customer, "custom_mobile_no_customer")
    if not mobile:
        frappe.log_error(f"No mobile number for customer {doc.customer}", "WhatsApp PDF Error")
        return

    chatId = f"91{mobile}@c.us"
    pdf = generate_pdf(doc)

    file_name = f"{doc.name}.pdf"
    file_path = f"/tmp/{file_name}"

    # Save PDF temporarily
    with open(file_path, "wb") as f:
        f.write(pdf)

    # Green API URL
    url = "https://7103.api.greenapi.com/waInstance7103539592/sendFileByUpload/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

    # Simple string caption (avoid JSON / objects)
    caption = f"Sales Invoice {doc.name}"

    data = {
        "chatId": chatId,
        "caption": caption,
        "fileName": file_name
    }

    files = {"file": open(file_path, "rb")}

    try:
        response = requests.post(url, data=data, files=files)

        # Convert response to string before logging to avoid Value too big
        response_text = str(response.json() if response.headers.get("Content-Type") == "application/json" else response.text)
        frappe.log_error(response_text, f"WhatsApp PDF Response - {doc.name}")

    except Exception as e:
        frappe.log_error(f"Error sending WhatsApp PDF: {str(e)}", f"WhatsApp PDF Error - {doc.name}")

    finally:
        # Remove temp file
        files["file"].close()
        if os.path.exists(file_path):
            os.remove(file_path)


import frappe
import os
import requests

def send_sales_invoice_pdf_from_outgoing_logistics(doc, method=None):

    for row in doc.references:

        if row.source_doctype != "Sales Invoice":
            continue

        sales_invoice = row.source_name
        if not sales_invoice:
            continue

        # Sales Invoice doc
        si_doc = frappe.get_doc("Sales Invoice", sales_invoice)

        # Mobile
        mobile = frappe.db.get_value("Customer", si_doc.customer, "custom_mobile_no_customer")

        if not mobile:
            frappe.log_error(f"No mobile for {si_doc.customer}", f"WhatsApp Skip {sales_invoice}")
            continue

        chatId = f"91{mobile}@c.us"

        # -----------------------------
        # TOTAL QTY CALCULATE
        # -----------------------------
        total_qty = sum([item.qty for item in si_doc.items])

        # -----------------------------
        # MESSAGE SEND
        # -----------------------------
        message = f"""Hello {si_doc.customer},

Your Sales Invoice has been generated.

Invoice No : {si_doc.name}
Total Qty : {total_qty}
Grand Total : {si_doc.grand_total}

Thank you!"""

        msg_url = "https://7103.api.greenapi.com/waInstance7103539592/sendMessage/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

        msg_payload = {
            "chatId": chatId,
            "message": message
        }

        try:
            requests.post(msg_url, json=msg_payload)
        except Exception as e:
            frappe.log_error(str(e), f"WhatsApp Msg Error {si_doc.name}")

        # -----------------------------
        # PDF GENERATE
        # -----------------------------
        pdf = frappe.get_print(
            doctype="Sales Invoice",
            name=si_doc.name,
            print_format="Sales Invoice Print Format",
            no_letterhead=1,
            as_pdf=True
        )

        file_name = f"{si_doc.name}.pdf"
        file_path = f"/tmp/{file_name}"

        with open(file_path, "wb") as f:
            f.write(pdf)

        # -----------------------------
        # PDF SEND
        # -----------------------------
        file_url = "https://7103.api.greenapi.com/waInstance7103539592/sendFileByUpload/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

        data = {
            "chatId": chatId,
            "caption": f"Invoice {si_doc.name}",
            "fileName": file_name
        }

        files = {"file": open(file_path, "rb")}

        try:
            response = requests.post(file_url, data=data, files=files)

            if response.status_code != 200:
                frappe.log_error(response.text, f"WhatsApp PDF Failed {si_doc.name}")

        except Exception as e:
            frappe.log_error(str(e), f"WhatsApp PDF Error {si_doc.name}")

        finally:
            files["file"].close()
            if os.path.exists(file_path):
                os.remove(file_path)