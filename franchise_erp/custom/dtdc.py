import frappe
import requests


# 🔹 1. PINCODE CHECK
# 1. PINCODE CHECK
@frappe.whitelist()
def check_pincode(org_pincode=None, des_pincode=None):

    if not org_pincode or not des_pincode:
        frappe.throw("Pincode missing")

    settings = frappe.get_single("DTDC Settings")

    if not settings.pincode_api:
        frappe.throw("Pincode API is not configured in DTDC Settings")

    url = settings.pincode_api

    payload = {
        "orgPincode": org_pincode,
        "desPincode": des_pincode
    }

    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=60
    )

    try:
        return res.json()
    except Exception:
        frappe.throw(
            f"DTDC Pincode API Error: HTTP {res.status_code}"
        )
#for single box
# @frappe.whitelist()
# def create_shipment(shipment_name):

#     import requests

#     doc = frappe.get_doc("Shipment", shipment_name)
#     settings = frappe.get_single("DTDC Settings")

#     # ✅ Address check
#     if not doc.delivery_address_name:
#         frappe.throw("Delivery Address not Linked")

#     address = frappe.get_doc("Address", doc.delivery_address_name)

#     # ✅ CHILD TABLE DATA
#     total_weight = 0
#     total_qty = 0
#     length = width = height = 10

#     if doc.shipment_parcel:
#         for row in doc.shipment_parcel:
#             total_weight += row.weight or 0
#             total_qty += row.count or 1

#             if row.length and row.width and row.height:
#                 length = row.length
#                 width = row.width
#                 height = row.height

#     if not total_weight:
#         total_weight = doc.total_weight or 1

#     if not total_qty:
#         total_qty = 1

#     declared_value = doc.value_of_goods or 1000

#     # ✅ SERVICE TYPE FROM SETTINGS ONLY
#     if not settings.service_type_id:
#         frappe.throw("❌ Service Type not set in DTDC Settings")

#     service_type = settings.service_type_id

#     url = "https://alphademodashboardapi.shipsy.io/api/customer/integration/consignment/softdata"

#     payload = {
#         "consignments": [
#             {
#                 "customer_code": settings.customer_code,
#                 "service_type_id": service_type,
#                 "load_type": settings.load_type or "NON-DOCUMENT",
#                 "consignment_type": settings.consignment_type or "Forward",
#                 "dimension_unit": settings.dimension_unit or "cm",
#                 "length": str(length),
#                 "width": str(width),
#                 "height": str(height),
#                 "weight_unit": settings.weight_unit or "kg",
#                 "weight": str(total_weight),
#                 "declared_value": str(declared_value),
#                 "eway_bill": "", #in case of shipment where invoice value is above 50k
#                 "invoice_number": "", #optional
#                 "invoice_date": "", #optional
#                 "num_pieces": str(total_qty),

#                 "origin_details": {
#                     "name": settings.company_name,
#                     "phone": settings.company_phone,
#                     "address_line_1": settings.company_address,
#                     "pincode": settings.company_pincode,
#                     "city": settings.company_city,
#                     "state": settings.company_state
#                 },

#                 "destination_details": {
#                     "name": address.address_title or "Customer",
#                     "phone": address.phone or "9999999999",
#                     "address_line_1": address.address_line1,
#                     "pincode": address.pincode,
#                     "city": address.city,
#                     "state": address.state
#                 },

#                 "customer_reference_number": doc.name,
#                 "cod_collection_mode": "", #"CASH" in case of COD & blank for prepaid
#                 "cod_amount": "", #collectable amount
#                 "commodity_id": settings.commodity_id, # list attached : https://docs.google.com/spreadsheets/d/158LuKmF8mHXSQfXcSE-U_NVeUpz-O1LuNlc1ualKEeI/edit?gid=1685543408#gid=1685543408
#                 "description": doc.description_of_content, #optional with 250 characters limit
#                 "reference_number": "" #AWB number
#             }
#         ]
#     }

#     headers = {
#         "api-key": settings.api_key,
#         "Content-Type": "application/json"
#     }

#     res = requests.post(url, json=payload, headers=headers)
#     data = res.json()

#     # ✅ ERROR HANDLE
#     if not data.get("data"):
#         frappe.throw(f"DTDC Error: {data}")

#     result = data["data"][0]

#     if not result.get("success"):
#         frappe.throw(result.get("message"))

#     #FIX HERE
#     awb = result.get("reference_number")

#     if not awb:
#         frappe.throw(f"AWB not generated: {data}")

#     #SAVE
#     doc.awb_number = awb
#     doc.db_update()

#     #DELIVERY NOTE UPDATE
#     if doc.shipment_delivery_note:

#         for row in doc.shipment_delivery_note:

#             if row.delivery_note:
#                 dn = frappe.get_doc("Delivery Note", row.delivery_note)

#                 dn.custom_awb_number = awb
#                 dn.custom_courier = "DTDC"

#                 dn.db_update()

#     return awb  


# 🔹 COMMON FUNCTION → Update Status Everywhere
def update_status(doc, status):

    # Prevent invalid overwrite (Delivered final state)
    if doc.custom_dtdc_status == "Delivered":
        return

    doc.db_set("custom_dtdc_status", status)

    # Sync Delivery Notes
    if doc.shipment_delivery_note:
        for row in doc.shipment_delivery_note:
            if row.delivery_note:
                frappe.db.set_value(
                    "Delivery Note",
                    row.delivery_note,
                    "custom_dtdc_status",
                    status
                )


# 🔹 COMMON FUNCTION → Update AWB in Delivery Note
def update_delivery_notes_awb(doc, awb):

    if doc.shipment_delivery_note:
        for row in doc.shipment_delivery_note:
            if row.delivery_note:
                frappe.db.set_value(
                    "Delivery Note",
                    row.delivery_note,
                    {
                        "custom_awb_number": awb,
                        "custom_courier": "DTDC"
                    }
                )

def update_outgoing_logistics_awb(outgoing_logistics, awb, shipment_name):

    if not outgoing_logistics:
        frappe.log_error(
            f"Shipment {shipment_name} me custom_outgoing_logistics set nahi hai.",
            "DTDC Outgoing Logistics Update"
        )
        return

    frappe.db.set_value(
        "Outgoing Logistics",
        outgoing_logistics,
        {
            "awb_number": awb,
            "shipment": shipment_name
        }
    )

# 🔹 1. CREATE SHIPMENT for multiple boxes
@frappe.whitelist()
def create_shipment(shipment_name):

    doc = frappe.get_doc("Shipment", shipment_name)
    settings = frappe.get_single("DTDC Settings")

    # ✅ DUPLICATE PROTECTION
    if doc.awb_number:
        return doc.awb_number

    if not doc.delivery_address_name:
        frappe.throw("Delivery Address not Linked")

    address = frappe.get_doc("Address", doc.delivery_address_name)

    pieces = []
    total_weight = 0
    total_qty = 0
    total_length = total_width = total_height = 0

    # 🔥 MULTI BOX LOGIC
    if doc.shipment_parcel:
        for row in doc.shipment_parcel:

            qty = row.count or 1
            weight = row.weight or 0

            for i in range(qty):
                pieces.append({
                    "description": doc.description_of_content or "Product",
                    "declared_value": "",
                    "weight": str(weight),
                    "height": str(row.height or 1),
                    "length": str(row.length or 1),
                    "width": str(row.width or 1)
                })

            total_weight += weight * qty
            total_qty += qty
            total_length += (row.length or 0) * qty
            total_width += (row.width or 0) * qty
            total_height += (row.height or 0) * qty

    # fallback
    total_weight = total_weight or doc.total_weight or 1
    total_qty = total_qty or 1

    length = total_length / total_qty if total_length else 1
    width = total_width / total_qty if total_width else 1
    height = total_height / total_qty if total_height else 1

    if not settings.service_type_id:
        frappe.throw("Service Type missing in DTDC Settings")

    if not settings.create_shipment_api:
        frappe.throw("Create Shipment API is not configured in DTDC Settings")

    url = settings.create_shipment_api

    payload = {
        "consignments": [
            {
                "customer_code": settings.customer_code,
                "service_type_id": settings.service_type_id,
                "load_type": settings.load_type or "NON-DOCUMENT",
                "consignment_type": settings.consignment_type or "Forward",

                "dimension_unit": settings.dimension_unit or "cm",
                "length": str(round(length, 2)),
                "width": str(round(width, 2)),
                "height": str(round(height, 2)),

                "weight_unit": settings.weight_unit or "kg",
                "weight": str(round(total_weight, 2)),

                "declared_value": str(doc.value_of_goods or 0),
                "num_pieces": str(total_qty),

                "origin_details": {
                    "name": settings.company_name,
                    "phone": settings.company_phone,
                    "address_line_1": settings.company_address,
                    "pincode": settings.company_pincode,
                    "city": settings.company_city,
                    "state": settings.company_state
                },

                "destination_details": {
                    "name": address.address_title or "Customer",
                    "phone": address.phone or "9999999999",
                    "address_line_1": address.address_line1,
                    "pincode": address.pincode,
                    "city": address.city,
                    "state": address.state
                },

                "customer_reference_number": doc.name,
                "commodity_id": settings.commodity_id,
                "description": doc.description_of_content,
                "reference_number": "",
                "pieces_detail": pieces
            }
        ]
    }

    headers = {
        "api-key": settings.api_key,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    data = res.json()

    if not data.get("data"):
        frappe.throw(f"DTDC Error: {data}")

    result = data["data"][0]

    if not result.get("success"):
        frappe.throw(result.get("message"))

    awb = result.get("reference_number")

    if not awb:
        frappe.throw("AWB not generated")

    # ✅ SAVE (SAFE WAY)
   # ---------------------------------------
    # SAVE AWB IN SHIPMENT
    # ---------------------------------------

    doc.db_set("awb_number", awb)

    # ---------------------------------------
    # UPDATE SHIPMENT STATUS
    # ---------------------------------------

    update_status(doc, "Created")

    # ---------------------------------------
    # UPDATE SAME OUTGOING LOGISTICS
    # ---------------------------------------

    update_outgoing_logistics_awb(
        doc.custom_outgoing_logistics,
        awb,
        shipment_name
    )

    frappe.db.commit()

    return awb


# 🔹 2. TRACK SHIPMENT
@frappe.whitelist()
def track(awb):

    settings = frappe.get_single("DTDC Settings")

    if not settings.track_api:
        frappe.throw("Track API is not configured in DTDC Settings")

    url = settings.track_api

    payload = {
        "trkType": "cnno",
        "strcnno": awb,
        "addtnlDtl": "Y"
    }

    headers = {
        "X-Access-Token": settings.tracking_token,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    data = res.json()

    try:
        status_text = data.get("trackHeader", {}).get("strStatus", "")

        mapped = None
        if "Delivered" in status_text:
            mapped = "Delivered"
        elif "Transit" in status_text or "Booked" in status_text:
            mapped = "In Transit"
        elif "Pickup" in status_text:
            mapped = "Created"

        if mapped:
            shipment = frappe.get_all(
                "Shipment",
                filters={"awb_number": awb},
                fields=["name"]
            )

            if shipment:
                doc = frappe.get_doc("Shipment", shipment[0].name)
                update_status(doc, mapped)

    except Exception as e:
        frappe.log_error(str(e), "Tracking Error")

    return data


@frappe.whitelist()
def download_label(awb=None):

    if not awb:
        frappe.throw("AWB number missing")

    settings = frappe.get_single("DTDC Settings")

    if not settings.download_label_api:
        frappe.throw(
            "Download Label API is not configured in DTDC Settings"
        )

    # ---------------------------------------
    # API URL
    # ---------------------------------------

    url = settings.download_label_api

    # ---------------------------------------
    # Query Parameters
    # ---------------------------------------

    params = {
        "reference_number": awb,
        "label_code": "SHIP_LABEL_4X6",
        "label_format": "pdf"
    }

    headers = {
        "api-key": settings.api_key,
        "Accept": "application/pdf"
    }

    # ---------------------------------------
    # API REQUEST
    # ---------------------------------------

    try:
        res = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

    except requests.RequestException as e:

        frappe.log_error(
            f"""
AWB:
{awb}

URL:
{url}

ERROR:
{str(e)}
""",
            "DTDC LABEL REQUEST ERROR"
        )

        frappe.throw(
            f"DTDC Label Request Error: {str(e)}"
        )

    # ---------------------------------------
    # DEBUG ERROR
    # ---------------------------------------

    if res.status_code != 200:

        response_text = res.text

        frappe.log_error(
            f"""
AWB:
{awb}

REQUEST URL:
{res.url}

STATUS:
{res.status_code}

RESPONSE HEADERS:
{dict(res.headers)}

RESPONSE:
{response_text}
""",
            "DTDC LABEL ERROR"
        )

        frappe.throw(
            f"DTDC Label API Error: HTTP {res.status_code}"
        )

    # ---------------------------------------
    # EMPTY RESPONSE CHECK
    # ---------------------------------------

    if not res.content:
        frappe.throw(
            "DTDC returned empty label response"
        )

    # ---------------------------------------
    # CONTENT TYPE CHECK
    # ---------------------------------------

    content_type = (
        res.headers.get("Content-Type", "")
        .lower()
    )

    if "application/json" in content_type:

        frappe.log_error(
            res.text,
            "DTDC LABEL JSON RESPONSE"
        )

        frappe.throw(
            f"DTDC returned JSON instead of PDF: {res.text}"
        )

    # ---------------------------------------
    # PDF DOWNLOAD
    # ---------------------------------------

    frappe.local.response.filename = f"{awb}.pdf"
    frappe.local.response.filecontent = res.content
    frappe.local.response.type = "download"
    
# 🔹 4. CANCEL SHIPMENT
# @frappe.whitelist()
# def cancel_shipment(shipment_name):

#     doc = frappe.get_doc("Shipment", shipment_name)
#     settings = frappe.get_single("DTDC Settings")

#     if not doc.awb_number:
#         frappe.throw("No AWB found")

#     url = "https://alphademodashboardapi.shipsy.io/api/customer/integration/consignment/cancel"

#     payload = {
#         "AWBNo": [doc.awb_number],
#         "customerCode": settings.customer_code
#     }

#     headers = {
#         "api-key": settings.api_key,
#         "Content-Type": "application/json"
#     }

#     res = requests.post(url, json=payload, headers=headers)
#     data = res.json()

#     if not data.get("success"):
#         frappe.throw("Cancel failed")

#     update_status(doc, "Cancelled")

#     # Clear AWB from DN
#     if doc.shipment_delivery_note:
#         for row in doc.shipment_delivery_note:
#             if row.delivery_note:
#                 frappe.db.set_value(
#                     "Delivery Note",
#                     row.delivery_note,
#                     {
#                         "custom_awb_number": "",
#                         "custom_courier": ""
#                     }
#                 )

#     frappe.db.commit()

#     return "Cancelled Successfully"

@frappe.whitelist()
def cancel_shipment(shipment_name):

    doc = frappe.get_doc("Shipment", shipment_name)
    settings = frappe.get_single("DTDC Settings")

    if not doc.awb_number:
        frappe.throw("No AWB found")

    if not settings.cancel_shipment_api:
        frappe.throw("Cancel Shipment API is not configured in DTDC Settings")

    url = settings.cancel_shipment_api

    payload = {
        "AWBNo": [doc.awb_number],
        "customerCode": settings.customer_code
    }

    headers = {
        "api-key": settings.api_key,
        "Content-Type": "application/json"
    }

    res = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=60
    )

    try:
        data = res.json()
    except Exception:
        frappe.throw(
            f"DTDC Cancel API Error: HTTP {res.status_code}"
        )

    if res.status_code != 200 or not data.get("success"):
        frappe.throw(
            f"DTDC Cancel Failed: {data}"
        )

    # ---------------------------------------
    # UPDATE SHIPMENT STATUS
    # ---------------------------------------

    update_status(doc, "Cancelled")

    # ---------------------------------------
    # CLEAR SAME OUTGOING LOGISTICS
    # ---------------------------------------

    outgoing_logistics = getattr(
        doc,
        "custom_outgoing_logistics",
        None
    )

    if outgoing_logistics:

        frappe.db.set_value(
            "Outgoing Logistics",
            outgoing_logistics,
            {
                "awb_number": "",
                "shipment": ""
            }
        )

    # Optional: Shipment ka AWB bhi clear karna hai
    # to ye uncomment kar sakte ho:
    #
    # doc.db_set("awb_number", "")

    frappe.db.commit()

    return "Cancelled Successfully"