frappe.query_reports["Holiday Worked Days & Pay Report"] = {

    filters: [

        {
            fieldname: "holiday_list",
            label: __("Holiday List"),
            fieldtype: "Link",
            options: "Holiday List",
            reqd: 1,
            default: "TZU Holiday List (26-27)",

            onchange: function () {

                // Clear employee when Holiday List changes
                frappe.query_report.set_filter_value(
                    "employee",
                    ""
                );

                set_employee_filter();

                set_holiday_dates();
            }
        },

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
            }
        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            read_only: 1
        },

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            read_only: 1
        }
    ],

    onload: function () {

        setTimeout(function () {

            set_holiday_dates();

            set_employee_filter();

        }, 300);
    }
};


// =========================================================
// SET HOLIDAY DATES
// =========================================================

function set_holiday_dates() {

    let holiday_list =
        frappe.query_report.get_filter_value(
            "holiday_list"
        );

    if (!holiday_list) {

        frappe.query_report.set_filter_value(
            "from_date",
            null
        );

        frappe.query_report.set_filter_value(
            "to_date",
            null
        );

        return;
    }

    frappe.db.get_value(
        "Holiday List",
        holiday_list,
        [
            "from_date",
            "to_date"
        ],
        function (r) {

            if (!r) {
                return;
            }

            frappe.query_report.set_filter_value(
                "from_date",
                r.from_date
            );

            frappe.query_report.set_filter_value(
                "to_date",
                r.to_date
            );
        }
    );
}


// =========================================================
// SET EMPLOYEE FILTER
// =========================================================

function set_employee_filter() {

    let holiday_list =
        frappe.query_report.get_filter_value(
            "holiday_list"
        );

    let employee_filter =
        frappe.query_report.get_filter(
            "employee"
        );

    if (!employee_filter) {
        return;
    }

    employee_filter.get_query = function () {

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
    };
}