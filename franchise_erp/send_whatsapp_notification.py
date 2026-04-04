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
        # pdf = frappe.get_print(
        #     doctype="Sales Invoice",
        #     name=si_doc.name,
        #     print_format="Sales Invoice Print Format",
        #     no_letterhead=1,
        #     as_pdf=True
        # )

        # file_name = f"{si_doc.name}.pdf"
        # file_path = f"/tmp/{file_name}"

        # with open(file_path, "wb") as f:
        #     f.write(pdf)


        pdf = frappe.get_print(
            doctype="Sales Invoice",
            name=si_doc.name,
            print_format="Sales Invoice Print Format",
            no_letterhead=1,
            as_pdf=True
        )

        # ✅ FIX: safe filename
        safe_name = si_doc.name.replace("/", "-")
        file_name = f"{safe_name}.pdf"
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








# daily sales for countor send to directors
import frappe
from frappe.utils import nowdate, getdate, formatdate
from frappe.utils.pdf import get_pdf
import os
import requests

# for single field mobile no
# @frappe.whitelist()
# def send_daily_counter_sales():
    
#     today = nowdate()
#     formatted_date = formatdate(today, "dd-MMM-yy")
#     # -----------------------------
#     # GET COUNTER SALES DATA
#     # -----------------------------
#     data = frappe.db.sql("""
#         SELECT 
#             c.name AS counter_name,
#             SUM(dni.qty) AS total_qty,
#             SUM(dni.amount) AS total_amount
#         FROM `tabDelivery Note` dn
#         JOIN `tabDelivery Note Item` dni ON dn.name = dni.parent
#         LEFT JOIN `tabCustomer` c 
#             ON c.represents_company = dn.company
#             AND c.is_internal_customer = 1
#         WHERE 
#             dn.docstatus = 1
#             AND DATE(dn.posting_date) = %s
#         GROUP BY dn.company
#     """, (today,), as_dict=True)

#     if not data:
#         return "No data found"

#     # -----------------------------
#     # CALCULATE TOTAL
#     # -----------------------------
#     total_qty = sum([d.total_qty for d in data])
#     total_amount = sum([d.total_amount for d in data])

#     # -----------------------------
#     # HTML FOR PDF
#     # -----------------------------
#     html = f"""
#     <h3 style="text-align:center;">Counter Sale Dt - {formatted_date}</h3>
#     <table border="1" cellspacing="0" cellpadding="5" width="100%">
#         <tr>
#             <th>Date</th>
#             <th>Counter Name</th>
#             <th>Net Sale Qty</th>
#             <th>Net Sale Amount</th>
#         </tr>
#     """

#     for d in data:
#         html += f"""
#         <tr>
#             <td>{formatted_date}</td>
#             <td>{d.counter_name}</td>
#             <td>{int(d.total_qty)}</td>
#             <td>{int(d.total_amount)}</td>
#         </tr>
#         """

#     html += f"""
#         <tr>
#             <td><b>Total</b></td>
#             <td></td>
#             <td><b>{int(total_qty)}</b></td>
#             <td><b>{int(total_amount)}</b></td>
#         </tr>
#     </table>
#     """

#     # -----------------------------
#     # GENERATE PDF
#     # -----------------------------
#     pdf = get_pdf(html)

#     file_name = f"Counter_Sales_{today}.pdf"
#     file_path = frappe.get_site_path("private", "files", file_name)

#     with open(file_path, "wb") as f:
#         f.write(pdf)

#     # -----------------------------
#     # GET WHATSAPP NUMBER FROM SETTINGS
#     # -----------------------------
#     mobile_no = frappe.db.get_single_value("TZU Setting", "mobile_no")

#     if not mobile_no:
#         frappe.log_error("Mobile No not set in TZU Settings")
#         return

#     chatId = f"91{mobile_no}@c.us"

#     # -----------------------------
#     # SEND WHATSAPP PDF
#     # -----------------------------
#     file_url = "https://7103.api.greenapi.com/waInstance7103539592/sendFileByUpload/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

#     data_req = {
#         "chatId": chatId,
#         "caption": f"Daily Counter Sales {today}",
#         "fileName": file_name
#     }

#     files = {"file": open(file_path, "rb")}

#     try:
#         response = requests.post(file_url, data=data_req, files=files)

#         if response.status_code != 200:
#             frappe.log_error(response.text, "WhatsApp PDF Failed")

#     except Exception as e:
#         frappe.log_error(str(e), "WhatsApp Error")

#     finally:
#         files["file"].close()
#         if os.path.exists(file_path):
#             os.remove(file_path)

#     return "Sent Successfully"

# multiple mobile no like child table
@frappe.whitelist()
def send_daily_counter_sales():
    
    today = nowdate()
    formatted_date = formatdate(today, "dd-MMM-yy")
    # -----------------------------
    # GET COUNTER SALES DATA
    # -----------------------------
    data = frappe.db.sql("""
        SELECT 
            c.name AS counter_name,
            SUM(dni.qty) AS total_qty,
            SUM(dni.amount) AS total_amount
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note Item` dni ON dn.name = dni.parent
        LEFT JOIN `tabCustomer` c 
            ON c.represents_company = dn.company
            AND c.is_internal_customer = 1
        WHERE 
            dn.docstatus = 1
            AND DATE(dn.posting_date) = %s
        GROUP BY dn.company
    """, (today,), as_dict=True)

    if not data:
        return "No data found"

    # -----------------------------
    # CALCULATE TOTAL
    # -----------------------------
    total_qty = sum([d.total_qty for d in data])
    total_amount = sum([d.total_amount for d in data])

    # -----------------------------
    # HTML FOR PDF
    # -----------------------------
    html = f"""
    <h3 style="text-align:center;">Counter Sale Dt - {formatted_date}</h3>
    <table border="1" cellspacing="0" cellpadding="5" width="100%">
        <tr>
            <th>Date</th>
            <th>Counter Name</th>
            <th>Net Sale Qty</th>
            <th>Net Sale Amount</th>
        </tr>
    """

    for d in data:
        html += f"""
        <tr>
            <td>{formatted_date}</td>
            <td>{d.counter_name}</td>
            <td>{int(d.total_qty)}</td>
            <td>{int(d.total_amount)}</td>
        </tr>
        """

    html += f"""
        <tr>
            <td><b>Total</b></td>
            <td></td>
            <td><b>{int(total_qty)}</b></td>
            <td><b>{int(total_amount)}</b></td>
        </tr>
    </table>
    """

    # -----------------------------
    # GENERATE PDF
    # -----------------------------
    pdf = get_pdf(html)

    file_name = f"Counter_Sales_{today}.pdf"
    file_path = frappe.get_site_path("private", "files", file_name)

    with open(file_path, "wb") as f:
        f.write(pdf)

    # -----------------------------
    # GET ALL MOBILE NUMBERS (Child Table)
    # -----------------------------
    numbers = frappe.get_all(
        "TZU WhatsApp Numbers",
        filters={"parent": "TZU Setting"},
        fields=["mobile_no"]
    )

    if not numbers:
        frappe.log_error("No Mobile Numbers found in TZU Settings")
        return

    # -----------------------------
    # SEND WHATSAPP TO EACH NUMBER
    # -----------------------------
    file_url = "https://7103.api.greenapi.com/waInstance7103539592/sendFileByUpload/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

    for row in numbers:
        mobile_no = row.mobile_no

        if not mobile_no:
            continue

        # ✅ ensure format (91 prefix)
        if not mobile_no.startswith("91"):
            mobile_no = "91" + mobile_no

        chatId = f"{mobile_no}@c.us"

        data_req = {
            "chatId": chatId,
            "caption": f"Daily Counter Sales {formatted_date}",
            "fileName": file_name
        }

        # ⚠️ IMPORTANT: file har loop me open karo
        files = {"file": open(file_path, "rb")}

        try:
            response = requests.post(file_url, data=data_req, files=files)

            if response.status_code != 200:
                frappe.log_error(response.text, f"WhatsApp Failed: {mobile_no}")
            else:
                frappe.logger().info(f"Sent to {mobile_no}")

        except Exception as e:
            frappe.log_error(str(e), f"WhatsApp Error: {mobile_no}")

        finally:
            files["file"].close()

    # -----------------------------
    # DELETE FILE AFTER ALL SEND
    # -----------------------------
    if os.path.exists(file_path):
        os.remove(file_path)

    return "Sent Successfully"

