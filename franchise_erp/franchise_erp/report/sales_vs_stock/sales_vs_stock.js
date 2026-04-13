// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.query_reports["Sales vs Stock"] = {
//     filters: [
//         {
//             fieldname: "from_date",
//             label: "From Date",
//             fieldtype: "Date",
//             default: frappe.datetime.month_start()
//         },
//         {
//             fieldname: "to_date",
//             label: "To Date",
//             fieldtype: "Date",
//             default: frappe.datetime.month_end()
//         }
//     ]
// };







// file: monthly_item_chart.js


//neww

// frappe.query_reports["Sales vs Stock"] = {
//     filters: [
//         {
//             fieldname: "month",
//             label: "Month",
//             fieldtype: "Select",
//             options: [
//                 "", "1","2","3","4","5","6","7","8","9","10","11","12"
//             ]
//         }
//     ],

//     onload: function(report) {},

//     formatter: function(value, row, column, data, default_formatter) {
//         return default_formatter(value, row, column, data);
//     },

//     get_chart_data: function(columns, result) {
//         let labels = [];
//         let sales = [];
//         let stock = [];

//         result.forEach(row => {
//             labels.push(row.item_name);
//             sales.push(row.sales_qty);
//             stock.push(row.stock_qty);
//         });

//         return {
//             data: {
//                 labels: labels,
//                 datasets: [
//                     {
//                         name: "Sales",
//                         values: sales
//                     },
//                     {
//                         name: "Stock",
//                         values: stock
//                     }
//                 ]
//             },
//             type: 'bar'
//         };
//     }
// };










frappe.query_reports["Sales vs Stock"] = {
    filters: [
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                { "value": "", "label": "All" },
                { "value": "1", "label": "Jan" },
                { "value": "2", "label": "Feb" },
                { "value": "3", "label": "Mar" },
                { "value": "4", "label": "Apr" },
                { "value": "5", "label": "May" },
                { "value": "6", "label": "Jun" },
                { "value": "7", "label": "Jul" },
                { "value": "8", "label": "Aug" },
                { "value": "9", "label": "Sep" },
                { "value": "10", "label": "Oct" },
                { "value": "11", "label": "Nov" },
                { "value": "12", "label": "Dec" }
            ],
            // ✅ Default = current month
            default: (new Date().getMonth() + 1).toString()
        }
    ],

    // Runs when report loads
    onload: function(report) {
        // Ensure default month is set
        if (!report.get_filter_value("month")) {
            report.set_filter_value("month", (new Date().getMonth() + 1).toString());
        }
    },

    // Optional formatter
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Highlight Low Stock
        if (column.fieldname === "status" && data) {
            if (data.status === "Low Stock") {
                value = `<span style="color:red;font-weight:bold;">${value}</span>`;
            } else if (data.status === "In Stock") {
                value = `<span style="color:green;">${value}</span>`;
            }
        }

        return value;
    },

    // Chart Data (Main Fix for Dashboard)
    get_chart_data: function(columns, result) {
        if (!result || result.length === 0) {
            return null;
        }

        let labels = [];
        let sales = [];
        let stock = [];

        result.forEach(row => {
            labels.push(row.item_name || "Unknown");
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