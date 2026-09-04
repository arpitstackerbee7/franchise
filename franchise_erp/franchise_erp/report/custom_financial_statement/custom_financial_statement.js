// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Custom Financial Statement"] = {

    filters: [

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },

        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Link",
            options: "Fiscal Year",
            reqd: 1,
            default: frappe.defaults.get_user_default("fiscal_year"),

            on_change: function (report) {

                let fy = report.get_filter_value(
                    "fiscal_year"
                );

                if (!fy) {
                    return;
                }

                frappe.db.get_value(
                    "Fiscal Year",
                    fy,
                    [
                        "year_start_date",
                        "year_end_date"
                    ]
                ).then(r => {

                    if (r.message) {

                        report.set_filter_value(
                            "from_date",
                            r.message.year_start_date
                        );

                        report.set_filter_value(
                            "to_date",
                            r.message.year_end_date
                        );

                    }

                });

            }
        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        },

        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },

        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },

        {
            fieldname: "finance_book",
            label: __("Finance Book"),
            fieldtype: "Link",
            options: "Finance Book"
        },

        {
            fieldname: "show_zero_values",
            label: __("Show Zero Values"),
            fieldtype: "Check",
            default: 1
        }
    ],

    formatter(
        value,
        row,
        column,
        data,
        default_formatter
    ) {

        value = default_formatter(
            value,
            row,
            column,
            data
        );

        if (!data) {
            return value;
        }

        const expense = data.expense || "";
        const income = data.income || "";

        // -------------------------------------------------
        // SECTION HEADERS
        // -------------------------------------------------

        if (
            expense === "TRADING ACCOUNT" ||
            expense === "PROFIT & LOSS ACCOUNT" ||
            expense === "KEY PERFORMANCE METRICS"
        ) {

            return `
                <div style="
                    font-weight:bold;
                    color:#1f4e78;
                    font-size:14px;
                ">
                    ${value}
                </div>
            `;
        }

        // -------------------------------------------------
        // SUBTOTAL / TOTAL
        // -------------------------------------------------

        if (
            expense === "Subtotal" ||
            expense === "Total" ||
            income === "Subtotal" ||
            income === "Total"
        ) {

            return `<b>${value}</b>`;
        }

        // -------------------------------------------------
        // PROFIT / LOSS
        // -------------------------------------------------

        if (
            expense === "Gross Profit" ||
            expense === "Net Profit"
        ) {

            return `
                <span style="
                    color:green;
                    font-weight:bold;
                ">
                    ${value}
                </span>
            `;
        }

        if (
            income === "Gross Loss" ||
            income === "Net Loss"
        ) {

            return `
                <span style="
                    color:red;
                    font-weight:bold;
                ">
                    ${value}
                </span>
            `;
        }

        // -------------------------------------------------
        // KPI
        // -------------------------------------------------

        if (
            expense === "Gross Profit %" ||
            expense === "Net Profit %" ||
            expense === "Operating Expense Ratio %"
        ) {

            return `
                <span style="
                    color:#1976d2;
                    font-weight:bold;
                ">
                    ${value}
                </span>
            `;
        }

        return value;
    },

    onload(report) {

        if (!report.get_filter_value("fiscal_year")) {
            return;
        }

        let fy = report.get_filter_value(
            "fiscal_year"
        );

        frappe.db.get_value(
            "Fiscal Year",
            fy,
            [
                "year_start_date",
                "year_end_date"
            ]
        ).then(r => {

            if (r.message) {

                if (
                    !report.get_filter_value(
                        "from_date"
                    )
                ) {

                    report.set_filter_value(
                        "from_date",
                        r.message.year_start_date
                    );

                }

                if (
                    !report.get_filter_value(
                        "to_date"
                    )
                ) {

                    report.set_filter_value(
                        "to_date",
                        r.message.year_end_date
                    );

                }

            }

        });

    }

};