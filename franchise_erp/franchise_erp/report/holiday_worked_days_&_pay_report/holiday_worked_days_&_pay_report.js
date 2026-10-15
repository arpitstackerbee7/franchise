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

            // Optional
            reqd: 0,

            // default: "TZU Holiday List (26-27)",

            onchange: function () {

                // -----------------------------------------
                // Employee clear
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
                // If Holiday List selected
                // set its dates
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

                // -----------------------------------------
                // Holiday List blank
                // -----------------------------------------
                // Show all Active Employees
                // -----------------------------------------

                if (!holiday_list) {

                    return {
                        filters: {
                            status: "Active"
                        }
                    };
                }

                // -----------------------------------------
                // Holiday List selected
                // -----------------------------------------
                // Only employees of that Holiday List
                // -----------------------------------------

                return {

                    filters: {

                        holiday_list:
                            holiday_list,

                        status:
                            "Active"
                    }
                };
            },

            onchange: function () {

                // -----------------------------------------
                // Employee selected OR cleared
                // -----------------------------------------
                // Immediately refresh report
                // -----------------------------------------

                frappe.query_report.refresh();
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

    // Default value Holiday List se onload/change par set hogi
    default: "2026-04-01",

    onchange: function () {

        // User manually date change kare
        // to selected date ke according report refresh ho
        frappe.query_report.refresh();
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

    // Default value Holiday List se onload/change par set hogi
    default: "2027-03-31",

    onchange: function () {

        // User manually date change kare
        // to selected date ke according report refresh ho
        frappe.query_report.refresh();
    }
}
    ],


    // =====================================================
    // ONLOAD
    // =====================================================

    onload: function () {

        setTimeout(function () {

            // ---------------------------------------------
            // Employee Query
            // ---------------------------------------------

            set_employee_query();

            // ---------------------------------------------
            // Holiday List dates
            // ---------------------------------------------

            set_holiday_list_dates();

        }, 300);
    }
};


// =========================================================
// SET HOLIDAY LIST DATES
// =========================================================

function set_holiday_list_dates() {

    let holiday_list =
        frappe.query_report.get_filter_value(
            "holiday_list"
        );

    // -----------------------------------------------------
    // Holiday List blank
    //
    // Do NOT change user's dates.
    // -----------------------------------------------------

    if (!holiday_list) {

        return;
    }

    // -----------------------------------------------------
    // Get Holiday List
    // -----------------------------------------------------

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

        // ---------------------------------------------
        // Set From Date
        // ---------------------------------------------

        if (from_date) {

            frappe.query_report.set_filter_value(
                "from_date",
                from_date
            );
        }

        // ---------------------------------------------
        // Set To Date
        // ---------------------------------------------

        if (to_date) {

            frappe.query_report.set_filter_value(
                "to_date",
                to_date
            );
        }

        // ---------------------------------------------
        // Update Employee Query
        // ---------------------------------------------

        set_employee_query();

        // ---------------------------------------------
        // Refresh once
        // ---------------------------------------------

        setTimeout(function () {

            frappe.query_report.refresh();

        }, 100);

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

        // -------------------------------------------------
        // Holiday List blank
        // -------------------------------------------------
        // All active employees
        // -------------------------------------------------

        if (!holiday_list) {

            return {

                filters: {

                    status: "Active"
                }
            };
        }

        // -------------------------------------------------
        // Holiday List selected
        // -------------------------------------------------

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