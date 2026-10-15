frappe.query_reports["Custom E-Way Bill Report"] = {
    filters: [
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