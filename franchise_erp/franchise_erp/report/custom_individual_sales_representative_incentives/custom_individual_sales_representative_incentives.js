// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Individual Sales Representative Incentives"] = {
    filters: [
        {
            fieldname: "counter",
            label: __("Counter"),
            fieldtype: "Link",
            options: "Customer",
            get_query: function () {
                return {
                    filters: {
                        is_internal_customer: 1,
                        represents_company: ["is", "set"]
                    }
                };
            }
        },
        {
            fieldname: "sales_man",
            label: __("Sales Man"),
            fieldtype: "Link",
            options: "User"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (
            column.fieldname === "user" &&
            data &&
            data.user
        ) {
            return `
                <a
                    href="#"
                    class="dn-user-link"
                    data-user="${encodeURIComponent(data.user)}"
                    style="font-weight: 600; cursor: pointer;"
                >
                    ${frappe.utils.escape_html(data.user)}
                </a>
            `;
        }

        return value;
    },

    onload: function () {
        $(document)
            .off(
                "click.custom_individual_incentive",
                ".dn-user-link"
            )
            .on(
                "click.custom_individual_incentive",
                ".dn-user-link",
                function (e) {
                    e.preventDefault();
                    e.stopPropagation();

                    const user = decodeURIComponent(
                        $(this).attr("data-user")
                    );

                    open_delivery_note_report_view(user);
                }
            );
    }
};


async function open_delivery_note_report_view(user) {
    const counter =
        frappe.query_report.get_filter_value("counter");

    const from_date =
        frappe.query_report.get_filter_value("from_date");

    const to_date =
        frappe.query_report.get_filter_value("to_date");

    if (!user || !from_date || !to_date) {
        frappe.msgprint(
            __("User, From Date and To Date are required.")
        );
        return;
    }

    let company = null;

    if (counter) {
        const response = await frappe.db.get_value(
            "Customer",
            counter,
            "represents_company"
        );

        company =
            response.message &&
            response.message.represents_company
                ? response.message.represents_company
                : null;

        if (!company) {
            frappe.msgprint(
                __("Represented Company is not set for the selected Counter.")
            );
            return;
        }
    }

    const filters = [
        ["Delivery Note", "owner", "=", user],
        ["Delivery Note", "docstatus", "=", 1],
        [
            "Delivery Note",
            "posting_date",
            "Between",
            [from_date, to_date]
        ]
    ];

    if (company) {
        filters.push([
            "Delivery Note",
            "company",
            "=",
            company
        ]);
    }

    const url =
        "/app/delivery-note/view/report?filters=" +
        encodeURIComponent(JSON.stringify(filters));

    window.open(url, "_blank");
}