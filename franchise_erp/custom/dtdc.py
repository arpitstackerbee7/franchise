import frappe
import requests


# 🔹 1. PINCODE CHECK
@frappe.whitelist()
def check_pincode(org_pincode=None, des_pincode=None):

    if not org_pincode or not des_pincode:
        frappe.throw("Pincode missing")

    url = "http://smarttrack.ctbsplus.dtdc.com/ratecalapi/PincodeApiCall"

    payload = {
        "orgPincode": org_pincode,
        "desPincode": des_pincode
    }

    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    return res.json()


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

    url = "https://alphademodashboardapi.shipsy.io/api/customer/integration/consignment/softdata"

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
    doc.db_set("awb_number", awb)

    update_status(doc, "Created")
    update_delivery_notes_awb(doc, awb)

    frappe.db.commit()

    return awb


# 🔹 2. TRACK SHIPMENT
@frappe.whitelist()
def track(awb):

    settings = frappe.get_single("DTDC Settings")

    url = "https://dtdcstagingapi.dtdc.com/dtdc-tracking-api/dtdc-api/rest/JSONCnTrk/getTrackDetails"

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


# 🔹 3. DOWNLOAD LABEL
@frappe.whitelist()
def download_label(awb):

    settings = frappe.get_single("DTDC Settings")

    url = f"https://alphademodashboardapi.shipsy.io/api/customer/integration/consignment/shippinglabel/stream?reference_number={awb}&label_code=SHIP_LABEL_4X6&label_format=pdf"

    headers = {"api-key": settings.api_key}

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        frappe.throw("Failed to download label")

    frappe.local.response.filename = f"{awb}.pdf"
    frappe.local.response.filecontent = res.content
    frappe.local.response.type = "download"


# 🔹 4. CANCEL SHIPMENT
@frappe.whitelist()
def cancel_shipment(shipment_name):

    doc = frappe.get_doc("Shipment", shipment_name)
    settings = frappe.get_single("DTDC Settings")

    if not doc.awb_number:
        frappe.throw("No AWB found")

    url = "https://alphademodashboardapi.shipsy.io/api/customer/integration/consignment/cancel"

    payload = {
        "AWBNo": [doc.awb_number],
        "customerCode": settings.customer_code
    }

    headers = {
        "api-key": settings.api_key,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    data = res.json()

    if not data.get("success"):
        frappe.throw("Cancel failed")

    update_status(doc, "Cancelled")

    # Clear AWB from DN
    if doc.shipment_delivery_note:
        for row in doc.shipment_delivery_note:
            if row.delivery_note:
                frappe.db.set_value(
                    "Delivery Note",
                    row.delivery_note,
                    {
                        "custom_awb_number": "",
                        "custom_courier": ""
                    }
                )

    frappe.db.commit()

    return "Cancelled Successfully"