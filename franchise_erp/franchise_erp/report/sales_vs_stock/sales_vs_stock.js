// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt



frappe.query_reports["Sales vs Stock"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                { "value": "", "label": "All" },
                { "value": "1",  "label": "Jan" },
                { "value": "2",  "label": "Feb" },
                { "value": "3",  "label": "Mar" },
                { "value": "4",  "label": "Apr" },
                { "value": "5",  "label": "May" },
                { "value": "6",  "label": "Jun" },
                { "value": "7",  "label": "Jul" },    // document.addEventListener(
                { "value": "8",  "label": "Aug" },
                { "value": "9",  "label": "Sep" },
                { "value": "10", "label": "Oct" },
                { "value": "11", "label": "Nov" },
                { "value": "12", "label": "Dec" }
            ],
            default: ""
        },
        {
            fieldname: "metric",
            label: "View By",
            fieldtype: "Select",
            options: ["qty", "amt"],  
            default: "qty"
        },
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company")
        }
    ],

    // onload: function(report) {
    //     if (!report.page) return;
    //     if (!report.get_filter_value("month")) {
    //         report.set_filter_value("month", (new Date().getMonth() + 1).toString());
    //     }
    // },
onload: function(report) {

    if (report._dashboard_listener_added) {
        return;
    }

    report._dashboard_listener_added = true;

    document.addEventListener(
        "dashboardFilterChanged",
        function(e) {

            const f = e.detail;

            if (report.get_filter("from_date")) {
                report.set_filter_value("from_date", f.from);
            }

            if (report.get_filter("to_date")) {
                report.set_filter_value("to_date", f.to);
            }

            if (report.get_filter("view_type")) {
                report.set_filter_value("view_type", f.view);
            }

            if (report.get_filter("metric")) {
                report.set_filter_value("metric", f.view);
            }

            if (report.get_filter("company")) {
                report.set_filter_value("company", f.company || "");
            }

            report.refresh();
        }
    );
},

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "status" && data) {
            if (data.status === "Low Stock") {
                value = `<span style="color:red;font-weight:bold;">${value}</span>`;
            } else if (data.status === "In Stock") {
                value = `<span style="color:green;">${value}</span>`;
            }
        }

        return value;
    },

    get_chart_data: function(columns, result) {

        if (!result || result.length === 0) {
            return null;
        }

        let labels = [];
        let sales = [];
        let stock = [];

        result.forEach(row => {

            labels.push(
                row.custom_barcode_code ||
                row.item_name ||
                "Unknown"
            );

            sales.push(row.sales_qty || 0);
            stock.push(row.stock_qty || 0);

        });

        return {

            data: {

                labels: labels,

                datasets: [

                    {
                        name: "Sales",
                        values: sales
                    },

                    {
                        name: "Stock",
                        values: stock
                    }

                ]

            },

            type: "bar",

            height: 300

        };

    }

};
