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

    onload: function (report) {

        // Remove any listener left behind by a previous instance of this report
        if (window._salesTrendFilterHandler) {
            document.removeEventListener('dashboardFilterChanged', window._salesTrendFilterHandler);
        }

        window._salesTrendFilterHandler = function (e) {
            // If a refresh triggered by this same event is still running, skip
            if (report._dashboard_sync_in_progress) return;
            report._dashboard_sync_in_progress = true;

            var f = e.detail;
            try {
                // Single call, single refresh — not 4 separate ones
                report.set_filter_value({
                    from_date: f.from,
                    to_date: f.to,
                    view_type: f.view,   // 'qty' or 'amt'
                    company: f.company || ''
                });
            } catch (err) {
                console.error('Sales Trend filter error:', err);
            } finally {
                setTimeout(function () {
                    report._dashboard_sync_in_progress = false;
                }, 300);
            }
        };

        document.addEventListener('dashboardFilterChanged', window._salesTrendFilterHandler);
    }

};