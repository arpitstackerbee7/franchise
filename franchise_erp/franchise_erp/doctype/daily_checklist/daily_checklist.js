// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Daily Checklist", {
//     refresh(frm) {
//         if (!frm.is_new()) return;

//         let current_user = frappe.session.user;

//         frm.set_value("user_id", current_user);

//         frappe.db.get_value("Employee", {
//             user_id: current_user
//         }, "name").then(r => {
//             if (r.message?.name) {
//                 frm.set_value("employee", r.message.name);
//             }
//         });

//         frappe.db.get_doc("User", current_user).then(user => {
//             if (user.company) {
//                 frm.set_value("sis_counter", user.company);

//                 frappe.call({
//                     method: "frappe.contacts.doctype.address.address.get_default_address",
//                     args: {
//                         doctype: "Company",
//                         name: user.company
//                     },
//                     callback(r) {
//                         if (r.message) {
//                             frappe.db.get_doc("Address", r.message).then(address => {
//                                 let full_address = [
//                                     address.address_line1,
//                                     address.address_line2,
//                                     address.city,
//                                     address.state
//                                 ].filter(Boolean).join(", ");

//                                 if (address.pincode) {
//                                     full_address += " - " + address.pincode;
//                                 }

//                                 frm.set_value("location", full_address);
//                             });
//                         }
//                     }
//                 });
//             }
//         });
//     }

// });


// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Franchise Erp and contributors

frappe.ui.form.on("Daily Checklist", {

    refresh(frm) {

        if (!frm.is_new()) return;

        let current_user = frappe.session.user;

        // User
        frm.set_value("user_id", current_user);
        frm.set_value("name_of_the_sales_promoter", current_user);

        // Employee
        frappe.db.get_value(
            "Employee",
            { user_id: current_user },
            "name"
        ).then(r => {

            if (r.message?.name) {
                frm.set_value("employee", r.message.name);
            }
        });

        // User Company
        frappe.db.get_doc("User", current_user).then(user => {

            if (user.company) {
                frm.set_value("sis_counter", user.company);
            }

            // Counter Location
            frappe.db.get_value(
                "Counter Location",
                { user: current_user },
                ["location_name"]
            ).then(r => {

                if (!r.message?.location_name) {

                    frappe.msgprint({
                        title: __("Location Not Assigned"),
                        message: __(
                            "Please assign location from Counter Location Doctype."
                        ),
                        indicator: "red"
                    });

                    return;
                }

                let location_name = r.message.location_name;

                frm.set_value("location", location_name);

            });

        });

    },

    validate(frm) {

        return new Promise((resolve, reject) => {

            if (!frm.doc.location) {
                reject();
                return;
            }

            // Browser GPS Permission
            navigator.geolocation.getCurrentPosition(

                function(position) {

                    let current_lat = position.coords.latitude;
                    let current_lng = position.coords.longitude;

                    // Fetch Location Master
                    frappe.db.get_doc("Location", frm.doc.location)
                    .then(location_doc => {

                        let target_lat = parseFloat(location_doc.latitude || 0);
                        let target_lng = parseFloat(location_doc.longitude || 0);

                        let allowed_radius =
                            parseFloat(location_doc.allow_radius_for_login || 100);

                        // Distance Formula
                        let distance = getDistanceFromLatLonInMeters(
                            current_lat,
                            current_lng,
                            target_lat,
                            target_lng
                        );

                        console.log("Distance:", distance);

                        // Match
                        if (distance <= allowed_radius) {

                            resolve();

                        } else {

                            frappe.validated = false;

                            frappe.msgprint({
                                title: __("Location Not Match"),
                                message: __(
                                    `You are ${Math.round(distance)} meters away from counter location. Please login from counter location.`
                                ),
                                indicator: "red"
                            });

                            reject();
                        }

                    });

                },

                function(error) {

                    frappe.validated = false;

                    frappe.msgprint({
                        title: __("Location Permission Required"),
                        message: __(
                            "Please enable live location/GPS access."
                        ),
                        indicator: "orange"
                    });

                    reject();
                },

                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }

            );

        });

    }

});

// Distance Formula
function getDistanceFromLatLonInMeters(lat1, lon1, lat2, lon2) {

    let R = 6371000;

    let dLat = deg2rad(lat2 - lat1);
    let dLon = deg2rad(lon2 - lon1);

    let a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(deg2rad(lat1)) *
        Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);

    let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
}

function deg2rad(deg) {
    return deg * (Math.PI / 180);
}