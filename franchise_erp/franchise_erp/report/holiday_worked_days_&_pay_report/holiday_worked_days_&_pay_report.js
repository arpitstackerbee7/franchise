frappe.query_reports["Holiday Worked Days & Pay Report"] = {

    filters: [

        // =================================================
        // HOLIDAY LIST
        // =================================================

        {
            fieldname: "holiday_list",
            label: __("Holiday List"),
            fieldtype: "Link",
            options: "Holiday List",
            reqd: 1,
            default: "TZU Holiday List (26-27)",

            onchange: function () {

                // -----------------------------------------
                // Clear Employee
                // -----------------------------------------

                frappe.query_report.set_filter_value(
                    "employee",
                    ""
                );

                // -----------------------------------------
                // Update Employee Query
                // -----------------------------------------

                set_employee_query();

                // -----------------------------------------
                // Set Holiday List Dates
                // -----------------------------------------

                set_holiday_list_dates();
            }
        },


        // =================================================
        // EMPLOYEE
        // =================================================

        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",

            get_query: function () {

                let holiday_list =
                    frappe.query_report.get_filter_value(
                        "holiday_list"
                    );

                if (!holiday_list) {

                    return {
                        filters: {
                            name: ["is", "not set"]
                        }
                    };
                }

                return {
                    filters: {
                        holiday_list: holiday_list,
                        status: "Active"
                    }
                };
            },

            onchange: function () {

                // -----------------------------------------
                // Employee select / clear
                // -----------------------------------------
                // Always refresh report
                // -----------------------------------------

                setTimeout(function () {

                    frappe.query_report.refresh();

                }, 100);
            }
        },


        // =================================================
        // FROM DATE
        // =================================================

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,

            onchange: function () {

                // -----------------------------------------
                // User changed From Date
                // -----------------------------------------

                setTimeout(function () {

                    frappe.query_report.refresh();

                }, 100);
            }
        },


        // =================================================
        // TO DATE
        // =================================================

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,

            onchange: function () {

                // -----------------------------------------
                // User changed To Date
                // -----------------------------------------

                setTimeout(function () {

                    frappe.query_report.refresh();

                }, 100);
            }
        }
    ],


    // =====================================================
    // ONLOAD
    // =====================================================

    onload: function () {

        setTimeout(function () {

            set_employee_query();

            set_holiday_list_dates();

        }, 300);
    }
};


// =========================================================
// GET HOLIDAY LIST DATES
// =========================================================

function set_holiday_list_dates() {

    let holiday_list =
        frappe.query_report.get_filter_value(
            "holiday_list"
        );

    if (!holiday_list) {

        return;
    }


    frappe.db.get_value(
        "Holiday List",
        holiday_list,
        [
            "from_date",
            "to_date"
        ]
    ).then(function (response) {

        if (
            !response ||
            !response.message
        ) {
            return;
        }


        let from_date =
            response.message.from_date;

        let to_date =
            response.message.to_date;


        // =================================================
        // Set From Date
        // =================================================

        let from_filter =
            frappe.query_report.get_filter(
                "from_date"
            );

        if (from_filter) {

            from_filter.set_value(
                from_date || ""
            );
        }


        // =================================================
        // Set To Date
        // =================================================

        let to_filter =
            frappe.query_report.get_filter(
                "to_date"
            );

        if (to_filter) {

            to_filter.set_value(
                to_date || ""
            );
        }


        // =================================================
        // Refresh after Holiday List change
        // =================================================

        setTimeout(function () {

            frappe.query_report.refresh();

        }, 150);

    });
}


// =========================================================
// SET EMPLOYEE QUERY
// =========================================================

function set_employee_query() {

    let employee_filter =
        frappe.query_report.get_filter(
            "employee"
        );

    if (!employee_filter) {
        return;
    }


    employee_filter.get_query = function () {

        let holiday_list =
            frappe.query_report.get_filter_value(
                "holiday_list"
            );


        if (!holiday_list) {

            return {
                filters: {
                    name: ["is", "not set"]
                }
            };
        }


        return {
            filters: {

                holiday_list:
                    holiday_list,

                status:
                    "Active"
            }
        };
    };
}