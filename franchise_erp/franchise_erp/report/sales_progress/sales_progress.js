// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Progress"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        }
    ],

    onload: function (report) {
        report.page.set_title(__("Sales Progress"));

        // Auto refresh when report loads first time
        report.refresh();

        // Optional: add quick refresh button
        report.page.add_inner_button(__("Refresh"), function () {
            report.refresh();
        });
    },

    after_datatable_render: function (report) {
        // Ensures chart updates properly after table renders
        if (report.chart) {
            report.chart.draw(true);
        }
    }
};