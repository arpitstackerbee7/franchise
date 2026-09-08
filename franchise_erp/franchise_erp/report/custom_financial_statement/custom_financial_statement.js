// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Custom Financial Statement"] = {

    filters: [

        // =================================================
        // COMPANY
        // =================================================

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },

        // =================================================
        // FISCAL YEAR
        // =================================================

        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Link",
            options: "Fiscal Year",
            reqd: 1,
            default: frappe.defaults.get_user_default("fiscal_year"),

            on_change: function (report) {

                let fy = report.get_filter_value("fiscal_year");

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

        // =================================================
        // FROM DATE
        // =================================================

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },

        // =================================================
        // TO DATE
        // =================================================

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        },

        // =================================================
        // COST CENTER
        // =================================================

        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },

        // =================================================
        // PROJECT
        // =================================================

        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },

        // =================================================
        // FINANCE BOOK
        // =================================================

        {
            fieldname: "finance_book",
            label: __("Finance Book"),
            fieldtype: "Link",
            options: "Finance Book"
        },

        // =================================================
        // SHOW ZERO VALUES
        // =================================================

        {
            fieldname: "show_zero_values",
            label: __("Show Zero Values"),
            fieldtype: "Check",
            default: 1
        }
    ],

    // =====================================================
    // FORMATTER
    // =====================================================

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

        // =================================================
        // DYNAMIC SECTION HEADER
        // =================================================
        //
        // Python creates section header like:
        //
        // {
        //     expense: "SECTION NAME",
        //     expense_amount: null,
        //     income: null,
        //     income_amount: null
        // }
        //
        // Therefore ANY statement_section will be
        // automatically highlighted.
        // =================================================

        const is_section_header =
            data.expense &&
            data.expense_amount === null &&
            data.income === null &&
            data.income_amount === null;

        if (is_section_header) {

            return `
                <div style="
                    font-weight:700;
                    color:#1f4e78;
                    font-size:14px;
                ">
                    ${value}
                </div>
            `;
        }

        // =================================================
        // SUBTOTAL / TOTAL
        // =================================================

        if (
            expense === "Subtotal" ||
            expense === "Total" ||
            income === "Subtotal" ||
            income === "Total"
        ) {

            return `<b>${value}</b>`;
        }

        // =================================================
        // PROFIT / LOSS
        // =================================================

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

        // =================================================
        // KPI
        // =================================================

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

    // =====================================================
    // ONLOAD
    // =====================================================

    onload(report) {

        if (!report.get_filter_value("fiscal_year")) {
            return;
        }

        let fy = report.get_filter_value("fiscal_year");

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
                    !report.get_filter_value("from_date")
                ) {

                    report.set_filter_value(
                        "from_date",
                        r.message.year_start_date
                    );

                }

                if (
                    !report.get_filter_value("to_date")
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