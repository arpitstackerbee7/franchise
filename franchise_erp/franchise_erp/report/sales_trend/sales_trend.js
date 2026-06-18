

frappe.query_reports["Sales Trend"] = {

    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
        },
        {
            fieldname: "view_type",
            label: "View Type",
            fieldtype: "Select",
            options: "qty\namt",
            default: "qty",
        },
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company")
        }
    ],

   onload: function(report) {

    if (report._dashboard_listener_added) {
        return;
    }

    report._dashboard_listener_added = true;

   document.addEventListener(
    "dashboardFilterChanged",
    function (e) {

        console.log(e.detail);

        report.set_filter_value("from_date", e.detail.from);
        report.set_filter_value("to_date", e.detail.to);

        // IMPORTANT
        report.set_filter_value("view_type", e.detail.view);

        report.set_filter_value("company", e.detail.company || "");

        report.refresh();
    }
);
}

};