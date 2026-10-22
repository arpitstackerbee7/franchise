frappe.query_reports["Custom E-Way Bill Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "eway_bill_no",
            label: __("EWB No"),
            fieldtype: "Data",
        },
        {
            fieldname: "eway_bill_date",
            label: __("EWB Date"),
            fieldtype: "Date",
        },
        
        {
            fieldname: "doc_type",
            label: __("Doc Type"),
            fieldtype: "Data",
        },
        {
            fieldname: "doc_no",
            label: __("Doc. No"),
            fieldtype: "Data",
        },
        {
            fieldname: "pending_type",
            label: __("Pending Type"),
            fieldtype: "Select",
            options: [
                "All",
                "E-Way Bill Pending for Gate Entry",
                "Gate Entry Pending for GRC/PRC",
            ].join("\n"),
            default: "All",
        },
    ],

    onload: function (report) {
        report.page.add_inner_button(
            __("Refresh"),
            function () {
                report.refresh();
            }
        );
    },
};