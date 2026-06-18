

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
    

    if (window._salesTrendListenerAdded) return;
    window._salesTrendListenerAdded = true;

    // document.addEventListener(
    //     'dashboardFilterChanged',
    //     function(e) {
    //         var f = e.detail;
    //         try {
    //             report.set_filter_value('from_date', f.from);
    //             report.set_filter_value('to_date',   f.to);
    //             report.set_filter_value('view_type', f.view);  // 'qty' or 'amt'
    //             report.set_filter_value('company',   f.company || '');
    //             setTimeout(function() {
    //                 report.refresh();
    //             }, 200);
    //         } catch(e) {
    //             console.error('Sales Trend filter error:', e);
    //         }
    //     }
    // );

    document.addEventListener(
        "dashboardFilterChanged",
        function (e) {

            console.log("Received Payload:", e.detail);

            report.set_filter_value("from_date", e.detail.from);
            report.set_filter_value("to_date", e.detail.to);
            report.set_filter_value("view_type", e.detail.view);
            report.set_filter_value("company", e.detail.company || "");

            setTimeout(function () {
                console.log(report.get_values());
                report.refresh();
            }, 200);
        }
    );
    
}

};