frappe.pages['selling-dashboard'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper, title: 'Selling Dashboard', single_column: true
    });
    new SellingDashboard(page);
};

const REPORTS = [
    { name: "Sales Trend",          target: "sales-trend-block",    metric_field: "view_type" },
    { name: "Sales Progress",       target: "sales-progress-block", metric_field: "view_type" },
    { name: "Sales vs Stock",       target: "sale-vs-stock-block",  metric_field: "metric" },
    { name: "Top Selling Items 1",  target: "top-selling-block",    metric_field: "metric" },
    { name: "Least Selling Items",  target: "least-selling-block",  metric_field: "metric" }
];

class SellingDashboard {
    constructor(page) {
        this.wrapper = $(page.body);
        this.inject_page_fixes();   
        this.build_skeleton();

        Promise.all([
            this.load_html_block("Date Range", "#block-date-range"),
            this.load_html_block("Selling Items", "#block-selling-items"),
            this.load_html_block("Sales vs Stock", "#block-sales-vs-stock")
        ]).then(() => {
            document.addEventListener("dashboardFilterChanged", (e) => this.refresh_all(e.detail));
            setTimeout(() => { if (typeof applyFilter === "function") applyFilter(); }, 500);
        });
    }

    
    inject_page_fixes() {
    $(`<style>
        .dr-page-wrap { max-width: 1200px; margin: 0 auto; padding: 0 8px; }

        
        .dr-bar { display: flex; align-items: center; width: 100%; }
        .dr-section { flex: 0 0 auto; }
        .dr-toggle-group {
            flex: 1 1 auto;
            display: flex;
            justify-content: center;
            margin: 0 !important;
            position: static !important;
            transform: none !important;
        }
        .dr-company-wrap { flex: 0 0 auto; margin-left: 0 !important; }

        #block-date-range { margin-bottom: 24px; }
        #block-date-range .dr-container { padding-bottom: 12px; }
        .row h5 { margin-top: 8px; margin-bottom: 12px; }
        .report-filter-icon {
            cursor: pointer; margin-left: 8px; color: #888; font-size: 14px;
            display: inline-block; vertical-align: middle;
        }
        .report-filter-icon:hover { color: #1D9E75; }
    </style>`).appendTo("head");
}

    build_skeleton() {
        this.wrapper.append(`
            <div class="dr-page-wrap" id="block-date-range"></div>

            <div class="row">
                <div class="col-md-6"><h5>Sales Trend</h5><div id="sales-trend-block"></div></div>
                <div class="col-md-6"><h5>Sales Progress</h5><div id="sales-progress-block"></div></div>
            </div>

            <div class="row">
                <div class="col-md-6"><h5>Top Selling (Style No.)</h5><div id="top-selling-block"></div></div>
                <div class="col-md-6"><h5>Least Selling (Style No.)</h5><div id="least-selling-block"></div></div>
            </div>

            <div class="dr-page-wrap" id="block-selling-items"></div>

            <div class="row"><div class="col-md-12"><h5>Sales vs Stock</h5><div id="sale-vs-stock-block"></div></div></div>

            <div class="dr-page-wrap" id="block-sales-vs-stock"></div>
        `);
    }

    load_html_block(block_name, target_selector) {
    return new Promise((resolve) => {
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Custom HTML Block", name: block_name },
            callback: (r) => {
                let doc = r.message;
                if (!doc) { resolve(); return; }

                let $target = $(target_selector);
                $target.html(doc.html || "");

                if (doc.style) {
                    $("<style>").text(doc.style).appendTo("head");
                }

                if (doc.javascript || doc.script) {
                    
                    let script = document.createElement("script");
                    script.textContent = `
                        (function() {
                            var root_element = document.querySelector("${target_selector}");
                            ${doc.javascript || doc.script}
                        })();
                    `;
                    document.body.appendChild(script);
                }

                resolve();
            }
        });
    });
}

    refresh_all(payload) {
        payload = payload || {};
        REPORTS.forEach(r => this.run_report(r, payload));
    }

    run_report(report, payload) {
        let filters = {
            from_date: payload.from,
            to_date: payload.to,
            company: payload.company || "",
            [report.metric_field]: payload.view === "amt" ? "amt" : "qty"
        };
        frappe.call({
            method: "frappe.desk.query_report.run",
            args: { report_name: report.name, filters, ignore_prepared_report: 1 },
            callback: (r) => {
                let res = r.message;
                if (!res || !res.chart) return;
                $(`#${report.target}`).empty();
                new frappe.Chart(`#${report.target}`, res.chart);
            }
        });
    }
}