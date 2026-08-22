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

            on_change: function (query_report) {

                // -------------------------------------------------
                // Clear Employee completely
                // -------------------------------------------------

                clear_employee_filter();

                // -------------------------------------------------
                // Update Employee Query
                // -------------------------------------------------

                set_employee_query();

                // -------------------------------------------------
                // Get Holiday List Dates
                // -------------------------------------------------

                set_holiday_list_dates(query_report, true);
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

                // -------------------------------------------------
                // No Holiday List
                // -------------------------------------------------

                if (!holiday_list) {

                    return {
                        filters: {
                            name: ["is", "not set"]
                        }
                    };
                }

                // -------------------------------------------------
                // Only Active Employees of Holiday List
                // -------------------------------------------------

                return {
                    filters: {
                        holiday_list: holiday_list,
                        status: "Active"
                    }
                };
            },

            on_change: function (query_report) {

                let employee =
                    frappe.query_report.get_filter_value(
                        "employee"
                    );

                console.log(
                    "Employee filter changed:",
                    employee
                );

                // -------------------------------------------------
                // IMPORTANT
                //
                // If employee is cleared, explicitly remove
                // it from query report filter state.
                // -------------------------------------------------

                if (!employee) {

                    clear_employee_filter();

                    console.log(
                        "Employee cleared - loading all employees"
                    );
                }

                // -------------------------------------------------
                // Refresh report
                // -------------------------------------------------

                query_report.refresh();
            }
        },


        // =================================================
        // FROM DATE
        // =================================================

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            read_only: 1,
            reqd: 1
        },


        // =================================================
        // TO DATE
        // =================================================

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            read_only: 1,
            reqd: 1
        }
    ],


    // =====================================================
    // ONLOAD
    // =====================================================

    onload: function (query_report) {

        setTimeout(function () {

            // -------------------------------------------------
            // Employee Query
            // -------------------------------------------------

            set_employee_query();

            // -------------------------------------------------
            // Holiday List Dates
            // -------------------------------------------------

            set_holiday_list_dates(
                query_report,
                false
            );

        }, 500);
    }
};


// =========================================================
// CLEAR EMPLOYEE FILTER COMPLETELY
// =========================================================

function clear_employee_filter() {

    let employee_filter =
        frappe.query_report.get_filter(
            "employee"
        );

    if (!employee_filter) {
        return;
    }

    // -----------------------------------------------------
    // Set Frappe filter value to blank
    // -----------------------------------------------------

    employee_filter.set_value("");

    // -----------------------------------------------------
    // Explicitly clear input
    // -----------------------------------------------------

    if (employee_filter.$input) {

        employee_filter.$input
            .val("")
            .trigger("change");
    }

    // -----------------------------------------------------
    // IMPORTANT:
    // Clear internal query report filter state
    // -----------------------------------------------------

    if (
        frappe.query_report
        &&
        frappe.query_report.filters_by_name
        &&
        frappe.query_report.filters_by_name.employee
    ) {

        frappe.query_report
            .filters_by_name
            .employee
            .value = "";
    }

    // -----------------------------------------------------
    // Also clear report filters object if available
    // -----------------------------------------------------

    if (
        frappe.query_report
        &&
        frappe.query_report.get_values
    ) {

        // Nothing else required here.
        // set_value("") above updates the report filter.
    }
}


// =========================================================
// SET HOLIDAY LIST DATES
// =========================================================

function set_holiday_list_dates(
    query_report,
    refresh_report
) {

    let holiday_list =
        frappe.query_report.get_filter_value(
            "holiday_list"
        );

    // -----------------------------------------------------
    // No Holiday List
    // -----------------------------------------------------

    if (!holiday_list) {

        set_report_filter_value(
            "from_date",
            ""
        );

        set_report_filter_value(
            "to_date",
            ""
        );

        return;
    }

    // -----------------------------------------------------
    // Fetch Holiday List Dates
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

        // -------------------------------------------------
        // Set From Date
        // -------------------------------------------------

        set_report_filter_value(
            "from_date",
            from_date
        );

        // -------------------------------------------------
        // Set To Date
        // -------------------------------------------------

        set_report_filter_value(
            "to_date",
            to_date
        );

        // -------------------------------------------------
        // Refresh Report
        // -------------------------------------------------

        if (refresh_report) {

            query_report.refresh();
        }

    });
}


// =========================================================
// SET REPORT FILTER VALUE
// =========================================================

function set_report_filter_value(
    fieldname,
    value
) {

    let filter =
        frappe.query_report.get_filter(
            fieldname
        );

    if (!filter) {
        return;
    }

    // -----------------------------------------------------
    // Set value through Frappe
    // -----------------------------------------------------

    filter.set_value(
        value || ""
    );

    // -----------------------------------------------------
    // Update UI
    // -----------------------------------------------------

    if (filter.$input) {

        filter.$input.val(
            value || ""
        );
    }
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
        // No Holiday List
        // -------------------------------------------------

        if (!holiday_list) {

            return {
                filters: {
                    name: ["is", "not set"]
                }
            };
        }

        // -------------------------------------------------
        // Holiday List Employees
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