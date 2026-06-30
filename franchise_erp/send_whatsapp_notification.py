import frappe
import requests
import os
import requests
import frappe

from frappe.utils import nowdate, formatdate
from frappe.utils.pdf import get_pdf


def send_otp_whatsapp(mobile_no, otp):

    chatId = f"91{mobile_no}@c.us"

    message = f"""
Dear User,

Your Login OTP is: {otp}

This OTP is valid for 5 minutes.

Team TZU
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
        response = requests.post(
            url,
            json=payload,
            headers=headers
        )

        frappe.logger().info(
            f"OTP WhatsApp Sent: {response.text}"
        )

        return response.json()

    except Exception as e:

        frappe.log_error(
            str(e),
            "OTP WhatsApp Error"
        )

        return None

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


def send_sales_invoice_pdf_from_outgoing_logistics(doc, method=None):

    # -----------------------------
    # CHECK TZU SETTING
    # -----------------------------
    enabled = frappe.db.get_single_value("TZU Setting", "enable_whatsapp_notification")

    if not enabled:
        return  #Stop execution if unchecked
    
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
    # data = frappe.db.sql("""
    #     SELECT 
    #         c.name AS counter_name,
    #         SUM(dni.qty) AS total_qty,
    #         SUM(dni.amount) AS total_amount
    #     FROM `tabDelivery Note` dn
    #     JOIN `tabDelivery Note Item` dni ON dn.name = dni.parent
    #     LEFT JOIN `tabCustomer` c 
    #         ON c.represents_company = dn.company
    #         AND c.is_internal_customer = 1
    #     WHERE 
    #         dn.docstatus = 1
    #         AND DATE(dn.posting_date) = %s
    #     GROUP BY dn.company
    # """, (today,), as_dict=True)
    data = frappe.db.sql("""
        SELECT 
            c.customer_name AS counter_name,
            SUM(dni.qty) AS total_qty,
            SUM(dni.amount) AS total_amount
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note Item` dni ON dn.name = dni.parent
        JOIN `tabCustomer` c 
            ON c.represents_company = dn.company
        WHERE 
            dn.docstatus = 1
            AND DATE(dn.posting_date) = %s
            AND c.is_internal_customer = 1
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



# send report to counter group
@frappe.whitelist()
def send_daily_counter_sales_group():

    settings = frappe.get_single("TZU Setting")

    if not settings.enable_whatsapp_group_notification:
        return "WhatsApp Group Notification is Disabled"

    today = nowdate()
    formatted_date = formatdate(today, "dd-MMM-yy")

    file_url = "https://7103.api.greenapi.com/waInstance7103539592/sendFileByUpload/9bd7cdb7db404e729b55044c571c040477707783b0da43dda5"

    # ----------------------------------------------------
    # Get all companies having Internal Customer
    # ----------------------------------------------------

    companies = frappe.db.sql("""
        SELECT DISTINCT
            c.name,
            c.company_name
        FROM `tabCompany` c
        INNER JOIN `tabCustomer` cust
            ON cust.represents_company = c.name
        WHERE cust.is_internal_customer = 1
    """, as_dict=True)

    if not companies:
        return "No Company Found"

    sent = 0

    # ----------------------------------------------------
    # Loop Company Wise
    # ----------------------------------------------------

    for company in companies:

        # ----------------------------------------
        # Delivery Note Summary
        # ----------------------------------------

        summary = frappe.db.sql("""
            SELECT
                IFNULL(q.qty, 0) AS total_qty,
                IFNULL(a.amount, 0) AS total_amount
            FROM
            (
                SELECT
                    SUM(dni.qty) AS qty
                FROM `tabDelivery Note` dn
                INNER JOIN `tabDelivery Note Item` dni
                    ON dni.parent = dn.name
                WHERE
                    dn.docstatus = 1
                    AND dn.company = %s
                    AND dn.posting_date = %s
            ) q,
            (
                SELECT
                    SUM(grand_total) AS amount
                FROM `tabDelivery Note`
                WHERE
                    docstatus = 1
                    AND company = %s
                    AND posting_date = %s
            ) a
        """, (company.name, today, company.name, today), as_dict=True)

        if not summary:
            continue

        total_qty = summary[0].total_qty or 0
        total_amount = summary[0].total_amount or 0
        rounded_total_amount = int(round(total_amount))
        if total_qty == 0 and total_amount == 0:
            continue

        # ----------------------------------------
        # PDF HTML
        # ----------------------------------------

        html = f"""
        <div style="font-family:Arial;padding:20px;">
        <h1 style="text-align:center; margin-bottom:5px;">
            {company.company_name}
        </h1>
        <h2 style="text-align:center;">
            Counter Sale Dt - {formatted_date}
        </h2>

        <table
            border="1"
            cellspacing="0"
            cellpadding="8"
            width="100%"
            style="border-collapse:collapse;font-size:14px;">

            <thead>

                <tr>

                    <th width="18%">Date</th>

                    <th width="28%">Counter Name</th>

                    <th width="22%">Net Sale Qty</th>

                    <th width="32%">Net Sale Amount</th>

                </tr>

            </thead>

            <tbody>

                <tr>

                    <td>{formatted_date}</td>

                    <td>{company.company_name}</td>

                    <td>{int(total_qty)}</td>

                    <td style="text-align:left;">{rounded_total_amount:,}</td>

                </tr>

                <tr>

                    <td><b>Total</b></td>

                    <td></td>

                    <td><b>{int(total_qty)}</b></td>

                    <td style="text-align:left;"><b>{rounded_total_amount:,}</b></td>

                </tr>

            </tbody>

        </table>

        </div>
        """

        pdf = get_pdf(html)

        filename = f"Counter_Sales_{company.name}_{today}.pdf"

        filepath = frappe.get_site_path(
            "private",
            "files",
            filename
        )

        with open(filepath, "wb") as f:
            f.write(pdf)

        # ----------------------------------------
        # Fetch WhatsApp Group IDs
        # ----------------------------------------

        groups = frappe.get_all(
            "WhatsApp Group Id",
            filters={
                "parent": company.name
            },
            fields=["whatsapp_group_id"]
        )
        # Skip if no Group IDs configured
        valid_groups = [
            g for g in groups
            if g.whatsapp_group_id and g.whatsapp_group_id.strip()
        ]

        if not valid_groups:
            frappe.logger().info(
                f"Skipping {company.name} - No WhatsApp Group ID Found"
            )

            if os.path.exists(filepath):
                os.remove(filepath)

            continue

        if not valid_groups:

            frappe.log_error(
                f"No Group Found for {company.name}",
                "Counter Sale WhatsApp"
            )

            if os.path.exists(filepath):
                os.remove(filepath)

            continue

        # ----------------------------------------
        # Send PDF
        # ----------------------------------------

        for g in valid_groups:

            if not g.whatsapp_group_id:
                continue

            chatId = g.whatsapp_group_id.strip()

            if "@g.us" not in chatId:
                chatId += "@g.us"

            data = {
                "chatId": chatId,
                "caption": f"Daily Counter Sales - {formatted_date}",
                "fileName": filename
            }

            try:

                with open(filepath, "rb") as pdf_file:

                    response = requests.post(
                        file_url,
                        data=data,
                        files={
                            "file": pdf_file
                        }
                    )

                if response.status_code == 200:

                    sent += 1

                else:

                    frappe.log_error(
                        response.text,
                        f"WhatsApp Failed {chatId}"
                    )

            except Exception:

                frappe.log_error(
                    frappe.get_traceback(),
                    f"WhatsApp Error {chatId}"
                )

        # ----------------------------------------
        # Delete PDF
        # ----------------------------------------

        if os.path.exists(filepath):
            os.remove(filepath)

    return f"Successfully Sent to {sent} Group(s)"