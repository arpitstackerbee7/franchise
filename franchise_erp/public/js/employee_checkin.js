frappe.ui.form.on("Employee Checkin", {

    employee: async function(frm) {

        if (!frm.doc.employee) return;

        try {

            // ==============================
            // Employee -> User ID
            // ==============================

            let employee = await frappe.db.get_value(
                "Employee",
                frm.doc.employee,
                "user_id"
            );

            let user_id = employee.message.user_id;

            console.log("USER ID:", user_id);

            if (!user_id) {

                frappe.msgprint({
                    title: __("User Missing"),
                    message: __("User ID not found in Employee."),
                    indicator: "red"
                });

                return;
            }

            // ==============================
            // Counter Location
            // ==============================

            let counter = await frappe.db.get_value(
                "Counter Location",
                {
                    user: user_id
                },
                [
                    "location_name",
                    "enable_location_restriction"
                ]
            );

            console.log("COUNTER:", counter);

            let location_name =
                counter.message.location_name;

            let enable_location_restriction =
                counter.message.enable_location_restriction;

            // ==============================
            // Restriction OFF
            // ==============================

            if (!enable_location_restriction) {

                console.log("Location restriction disabled");

                // Device ID blank/remove
                frm.set_value("device_id", "");

                return;
            }

            // ==============================
            // Location Missing
            // ==============================

            if (!location_name) {

                frappe.msgprint({
                    title: __("Location Missing"),
                    message: __("Counter Location not assigned."),
                    indicator: "red"
                });

                return;
            }

            // ==============================
            // Device ID Set
            // ==============================

            frm.set_value("device_id", location_name);

            console.log("Location Set:", location_name);

        } catch (err) {

            console.error(err);

            frappe.msgprint({
                title: __("Error"),
                message: __("Unable to fetch location."),
                indicator: "red"
            });
        }
    },

    before_save: async function(frm) {

        // ==============================
        // Employee Required
        // ==============================

        if (!frm.doc.employee) return;

        // ==============================
        // Employee -> User ID
        // ==============================

        let employee = await frappe.db.get_value(
            "Employee",
            frm.doc.employee,
            "user_id"
        );

        let user_id = employee.message.user_id;

        // ==============================
        // Counter Location
        // ==============================

        let counter = await frappe.db.get_value(
            "Counter Location",
            {
                user: user_id
            },
            [
                "location_name",
                "enable_location_restriction"
            ]
        );

        let enable_location_restriction =
            counter.message.enable_location_restriction;

        // ==============================
        // Restriction OFF
        // ==============================

        if (!enable_location_restriction) {

            console.log("GPS validation skipped");

            return;
        }

        // ==============================
        // Device ID Required
        // ==============================

        if (!frm.doc.device_id) {

            frappe.throw(__("Location not found."));
        }

        // ==============================
        // GPS Fetch
        // ==============================

        const position = await getCurrentPosition();

        let current_lat = position.coords.latitude;
        let current_lng = position.coords.longitude;

        console.log("Current:", current_lat, current_lng);

        // ==============================
        // Location Fetch
        // ==============================

        let location = await frappe.db.get_doc(
            "Location",
            frm.doc.device_id
        );

        let target_lat = parseFloat(location.latitude || 0);
        let target_lng = parseFloat(location.longitude || 0);

        let allowed_radius = parseFloat(
            location.allow_radius_for_login || 100
        );

        // ==============================
        // Distance
        // ==============================

        let distance = getDistanceFromLatLonInMeters(
            current_lat,
            current_lng,
            target_lat,
            target_lng
        );

        console.log("Distance:", distance);

        // ==============================
        // Validation
        // ==============================

        if (distance > allowed_radius) {

            frappe.throw(
                __(
                    `You are ${Math.round(distance)} meters away from counter location.`
                )
            );
        }
    }
});


// ==============================
// GPS Promise
// ==============================

function getCurrentPosition() {

    return new Promise((resolve, reject) => {

        navigator.geolocation.getCurrentPosition(

            resolve,

            function(error) {

                frappe.msgprint({
                    title: __("GPS Permission Required"),
                    message: __("Please enable GPS access."),
                    indicator: "orange"
                });

                reject(error);
            },

            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    });
}


// ==============================
// Distance Formula
// ==============================

function getDistanceFromLatLonInMeters(
    lat1,
    lon1,
    lat2,
    lon2
) {

    let R = 6371000;

    let dLat = deg2rad(lat2 - lat1);
    let dLon = deg2rad(lon2 - lon1);

    let a =
        Math.sin(dLat / 2) *
        Math.sin(dLat / 2) +

        Math.cos(deg2rad(lat1)) *
        Math.cos(deg2rad(lat2)) *

        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);

    let c = 2 * Math.atan2(
        Math.sqrt(a),
        Math.sqrt(1 - a)
    );

    return R * c;
}

function deg2rad(deg) {

    return deg * (Math.PI / 180);
}