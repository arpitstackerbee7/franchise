frappe.ui.form.on("Shipment", {

    // ✅ ADD THIS HERE
    before_save: function(frm) {

        if (!frm.doc.delivery_address_name && frm.doc.customer) {

            frappe.call({
                method: "frappe.contacts.doctype.address.address.get_default_address",
                args: {
                    doctype: "Customer",
                    name: frm.doc.customer
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("delivery_address_name", r.message.name);
                    }
                }
            });
        }
    },

    validate: async function(frm) {

        let org_pincode = await frappe.db.get_single_value("DTDC Settings", "company_pincode");

        let des_pincode = null;

        if (frm.doc.delivery_address_name) {

            try {
                let address_doc = await frappe.db.get_doc("Address", frm.doc.delivery_address_name);
                des_pincode = address_doc.pincode;
            } catch (e) {}
        }

        if (!des_pincode && frm.doc.delivery_address) {

            let match = frm.doc.delivery_address.match(/PIN Code:\s*(\d{6})/);

            if (match) {
                des_pincode = match[1];
            }
        }

        if (!org_pincode || !des_pincode) {
            return;
        }

        let res = await frappe.call({
            method: "franchise_erp.custom.dtdc.check_pincode",
            args: {
                org_pincode: org_pincode,
                des_pincode: des_pincode
            }
        });

        let flag = res.message?.ZIPCODE_RESP?.[0]?.SERVFLAG;

        if (flag !== "Y") {
            frappe.throw("❌ DTDC not serviceable");
        }
    },

    refresh(frm) {

        if (frm.doc.docstatus === 1 && !frm.doc.awb_number) {

            frm.add_custom_button("Create DTDC Shipment", async () => {

                if (frm.doc.awb_number) {
                    frappe.msgprint("⚠️ AWB already generated for this Shipment");
                    return;
                }

                frappe.dom.freeze("Creating Shipment...");

                try {

                    if (frm.is_new()) {
                        await frm.save();
                    }

                    let res = await frappe.call({
                        method: "franchise_erp.custom.dtdc.create_shipment",
                        args: {
                            shipment_name: frm.doc.name
                        }
                    });

                    if (res.message) {
                        await frm.set_value("awb_number", res.message);
                        await frm.save();

                        frappe.msgprint("✅ AWB Generated Successfully");
                    }

                } catch (e) {
                    console.error(e);
                    frappe.msgprint("❌ Failed to create shipment");
                }

                frappe.dom.unfreeze();
            });
        }

        // if (frm.doc.awb_number) {

        // frm.add_custom_button("Track Shipment", async () => {

        //         let res = await frappe.call({
        //             method: "franchise_erp.custom.dtdc.track",
        //             args: {
        //                 awb: frm.doc.awb_number
        //             }
        //         });

        //         let data = res.message;

        //         if (!data || !data.trackHeader) {
        //             frappe.msgprint("❌ No tracking data found");
        //             return;
        //         }

        //         let header = data.trackHeader;
        //         let details = data.trackDetails || [];

        //         // 🔹 HEADER HTML
        //         let html = `
        //             <div style="padding:10px">

        //                 <b>AWB No:</b> ${header.strShipmentNo || "-"}<br>
        //                 <b>Status:</b> <span style="color:green;font-weight:bold">
        //                     ${header.strStatus || "-"}
        //                 </span><br>
        //                 <b>Origin:</b> ${header.strOrigin || "-"}<br>
        //                 <b>Booking Date:</b> ${formatDTDCDate(header.strBookedDate)} ${header.strBookedTime || ""}<br>
        //                 <b>Weight:</b> ${header.strWeight || "-"} ${header.strWeightUnit || ""}<br>

        //                 <hr>
        //                 <h4>📍 Tracking Timeline</h4>

        //                 <table style="width:100%; border-collapse: collapse;">
        //                     <thead>
        //                         <tr style="background:#f5f5f5">
        //                             <th style="padding:8px; border:1px solid #ddd;">Date</th>
        //                             <th style="padding:8px; border:1px solid #ddd;">Time</th>
        //                             <th style="padding:8px; border:1px solid #ddd;">Location</th>
        //                             <th style="padding:8px; border:1px solid #ddd;">Status</th>
        //                         </tr>
        //                     </thead>
        //                     <tbody>
        //         `;

        //         // 🔹 LOOP DETAILS
        //         details.forEach(d => {
        //             html += `
        //                 <tr>
        //                     <td style="padding:8px; border:1px solid #ddd;">${d.strActionDate || "-"}</td>
        //                     <td style="padding:8px; border:1px solid #ddd;">${d.strActionTime || "-"}</td>
        //                     <td style="padding:8px; border:1px solid #ddd;">${d.strOrigin || "-"}</td>
        //                     <td style="padding:8px; border:1px solid #ddd;">${d.strAction || "-"}</td>
        //                 </tr>
        //             `;
        //         });

        //         html += `
        //                     </tbody>
        //                 </table>
        //             </div>
        //         `;

        //         // 🔹 SHOW DIALOG
        //         let d = new frappe.ui.Dialog({
        //             title: "📦 Shipment Tracking",
        //             size: "large",
        //             fields: [
        //                 {
        //                     fieldtype: "HTML",
        //                     fieldname: "tracking_html"
        //                 }
        //             ]
        //         });

        //         d.fields_dict.tracking_html.$wrapper.html(html);
        //         d.show();
        //     });
        // }

        if (frm.doc.docstatus === 1 && frm.doc.awb_number) {

            frm.add_custom_button("Download Label", () => {

                window.open(
                    `/api/method/franchise_erp.custom.dtdc.download_label?awb=${frm.doc.awb_number}`
                );

            });
        }

        if (frm.doc.docstatus === 1 && frm.doc.awb_number) {

            frm.add_custom_button("Cancel DTDC Shipment", async () => {

                frappe.confirm(
                    "Are you sure you want to cancel this shipment?",
                    async () => {

                        frappe.dom.freeze("Cancelling Shipment...");

                        try {

                            let res = await frappe.call({
                                method: "franchise_erp.custom.dtdc.cancel_shipment",
                                args: {
                                    shipment_name: frm.doc.name
                                }
                            });

                            frappe.msgprint("❌ Shipment Cancelled in DTDC");

                            frm.reload_doc();

                        } catch (e) {
                            console.error(e);
                            frappe.msgprint("❌ Cancel failed");
                        }

                        frappe.dom.unfreeze();
                    }
                );

            });
        }
    }
});

function formatDTDCDate(dateStr) {
    if (!dateStr || dateStr.length !== 8) return "-";

    let day = dateStr.substring(0, 2);
    let month = dateStr.substring(2, 4);
    let year = dateStr.substring(4, 8);

    let months = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ];

    return `${parseInt(day)} ${months[parseInt(month) - 1]} ${year}`;
}

function formatDTDCTime(timeStr) {
    if (!timeStr || timeStr.length < 3) return "";

    let hour = parseInt(timeStr.substring(0, 2));
    let min = timeStr.substring(2, 4);

    let ampm = hour >= 12 ? "PM" : "AM";
    hour = hour % 12;
    hour = hour ? hour : 12; // 0 -> 12

    return `${hour}:${min} ${ampm}`;
}