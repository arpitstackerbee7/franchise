frappe.pages["selling-dashboard"].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Selling Dashboard",
        single_column: true
    });

    new SellingDashboard(page);
};


/* =========================================================
   SELLING DASHBOARD
========================================================= */

class SellingDashboard {

    constructor(page) {

        this.page = page;
        this.wrapper = $(page.body);

        this.filters = null;

        this.refresh_timer = null;

        this.is_loading = false;

        this.event_handler = null;

        this.inject_css();

        this.build_html();

        this.bind_events();

        this.load_blocks();
    }


    /* =====================================================
       CSS
    ===================================================== */

    inject_css() {

        if (document.getElementById("selling-dashboard-css")) {
            return;
        }

        $(`
            <style id="selling-dashboard-css">

                .selling-dashboard-wrap {
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 12px;
                }

                .selling-dashboard-section {
                    margin-bottom: 22px;
                }

                .selling-dashboard-section h5 {
                    margin-top: 8px;
                    margin-bottom: 12px;
                    font-weight: 600;
                }

                .selling-dashboard-chart {
                    min-height: 180px;
                }

                .selling-dashboard-loading {
                    min-height: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #888;
                }

                .selling-dashboard-empty {
                    padding: 25px;
                    text-align: center;
                    color: #888;
                }

                .selling-dashboard-error {
                    padding: 20px;
                    text-align: center;
                    color: #d9534f;
                }

            </style>
        `).appendTo("head");
    }


    /* =====================================================
       HTML
    ===================================================== */

    build_html() {

        this.wrapper.html(`

            <div class="selling-dashboard-wrap">

                <!-- DATE RANGE -->

                <div
                    id="block-date-range"
                    class="selling-dashboard-section">
                </div>


                <!-- SALES TREND / SALES PROGRESS -->

                <div class="row">

                    <div class="col-md-6">

                        <div class="selling-dashboard-section">

                            <h5>Sales Trend</h5>

                            <div
                                id="sales-trend-block"
                                class="selling-dashboard-chart">

                                <div class="selling-dashboard-loading">
                                    Loading...
                                </div>

                            </div>

                        </div>

                    </div>


                    <div class="col-md-6">

                        <div class="selling-dashboard-section">

                            <h5>Sales Progress</h5>

                            <div
                                id="sales-progress-block"
                                class="selling-dashboard-chart">

                                <div class="selling-dashboard-loading">
                                    Loading...
                                </div>

                            </div>

                        </div>

                    </div>

                </div>


                <!-- TOP / LEAST -->

                <div class="row">

                    <div class="col-md-6">

                        <div class="selling-dashboard-section">

                            <h5>Top Selling (Style No.)</h5>

                            <div
                                id="top-selling-block"
                                class="selling-dashboard-chart">

                                <div class="selling-dashboard-loading">
                                    Loading...
                                </div>

                            </div>

                        </div>

                    </div>


                    <div class="col-md-6">

                        <div class="selling-dashboard-section">

                            <h5>Least Selling (Style No.)</h5>

                            <div
                                id="least-selling-block"
                                class="selling-dashboard-chart">

                                <div class="selling-dashboard-loading">
                                    Loading...
                                </div>

                            </div>

                        </div>

                    </div>

                </div>


                <!-- TOP / LEAST CUSTOM HTML -->

                <div
                    id="block-selling-items"
                    class="selling-dashboard-section">
                </div>


                <!-- SALES VS STOCK CHART -->

                <div class="selling-dashboard-section">

                    <h5>Sales vs Stock</h5>

                    <div
                        id="sale-vs-stock-block"
                        class="selling-dashboard-chart">

                        <div class="selling-dashboard-loading">
                            Loading...
                        </div>

                    </div>

                </div>


                <!-- SALES VS STOCK TABLE -->

                <div
                    id="block-sales-vs-stock"
                    class="selling-dashboard-section">
                </div>

            </div>

        `);
    }


    /* =====================================================
       EVENTS
    ===================================================== */

    bind_events() {

        this.event_handler = (e) => {

            clearTimeout(this.refresh_timer);

            this.refresh_timer = setTimeout(() => {

                this.refresh_dashboard(
                    e.detail || {}
                );

            }, 100);

        };

        document.addEventListener(
            "dashboardFilterChanged",
            this.event_handler
        );
    }


    /* =====================================================
       LOAD CUSTOM HTML BLOCKS
    ===================================================== */

    async load_blocks() {

        try {

            /*
             * Date Range first
             */

            await this.load_html_block(
                "Date Range",
                "#block-date-range"
            );


            /*
             * Other blocks parallel
             */

            await Promise.all([

                this.load_html_block(
                    "Selling Items",
                    "#block-selling-items"
                ),

                this.load_html_block(
                    "Sales vs Stock",
                    "#block-sales-vs-stock"
                )

            ]);


            /*
             * Allow injected block JS to initialize.
             */

            setTimeout(() => {

                this.initial_load();

            }, 100);


        } catch (error) {

            console.error(
                "Selling Dashboard block loading error",
                error
            );

            this.initial_load();
        }
    }


    /* =====================================================
       INITIAL LOAD
    ===================================================== */

    initial_load() {

        let filters = this.get_filters();


        /*
         * Store filters globally so Custom HTML Blocks
         * can use the exact same filters.
         */

        this.filters = filters;

        frappe.dashboardFilter = {
            from: filters.from_date,
            to: filters.to_date,
            company: filters.company,
            view: filters.view
        };


        /*
         * Do NOT wait for dashboardFilterChanged.
         *
         * Directly refresh everything.
         */

        this.refresh_dashboard(filters);
    }


    /* =====================================================
       GET FILTERS
    ===================================================== */

    get_filters(event_payload) {

        event_payload = event_payload || {};


        let from =
            event_payload.from ||
            event_payload.from_date ||
            sessionStorage.getItem("dr_from") ||
            "";


        let to =
            event_payload.to ||
            event_payload.to_date ||
            sessionStorage.getItem("dr_to") ||
            "";


        let company =
            event_payload.company ||
            sessionStorage.getItem("dr_company") ||
            frappe.defaults.get_default("company") ||
            "";


        /*
         * Default = current month
         */

        if (!from || !to) {

            const today =
                frappe.datetime.get_today();

            from =
                frappe.datetime.month_start(today);

            to =
                frappe.datetime.month_end(today);
        }


        let view =
            event_payload.view ||
            event_payload.view_type ||
            sessionStorage.getItem("dr_view") ||
            "qty";


        if (
            view !== "qty" &&
            view !== "amt"
        ) {

            view = "qty";
        }


        return {

            from_date: from,

            to_date: to,

            company: company,

            view: view
        };
    }


    /* =====================================================
       REFRESH DASHBOARD
    ===================================================== */

    refresh_dashboard(payload) {

        const filters =
            this.get_filters(payload);


        this.filters = filters;


        /*
         * Save globally
         */

        frappe.dashboardFilter = {

            from: filters.from_date,

            to: filters.to_date,

            company: filters.company,

            view: filters.view

        };


        /*
         * Run all independent reports parallel.
         */

        this.run_sales_trend(filters);

        this.run_sales_progress(filters);

        this.run_top_chart(filters);

        this.run_least_chart(filters);

        /*
         * IMPORTANT:
         *
         * Sales vs Stock only ONE API call.
         *
         * Response is sent to table block also.
         */

        this.run_sales_vs_stock(filters);


        /*
         * Tell Custom HTML Blocks about
         * updated filters.
         */

        document.dispatchEvent(
            new CustomEvent(
                "sellingDashboardReady",
                {
                    detail: filters
                }
            )
        );
    }


    /* =====================================================
       COMMON REPORT CALL
    ===================================================== */

    call_report(
        report_name,
        filters,
        callback
    ) {

        frappe.call({

            method:
                "frappe.desk.query_report.run",

            args: {

                report_name:
                    report_name,

                filters:
                    filters,

                ignore_prepared_report:
                    1
            },

            callback: function (r) {

                callback(
                    r && r.message
                        ? r.message
                        : null
                );
            },

            error: function (err) {

                console.error(
                    report_name,
                    err
                );

                callback(null);
            }
        });
    }


    /* =====================================================
       SALES TREND
    ===================================================== */

    run_sales_trend(filters) {

        const target =
            document.getElementById(
                "sales-trend-block"
            );

        if (!target) {
            return;
        }


        this.show_loading(target);


        this.call_report(

            "Sales Trend",

            {

                from_date:
                    filters.from_date,

                to_date:
                    filters.to_date,

                company:
                    filters.company,

                view_type:
                    filters.view === "amt"
                        ? "amt"
                        : "qty"
            },

            (result) => {

                this.render_chart(
                    target,
                    result,
                    "Sales Trend"
                );
            }
        );
    }


    /* =====================================================
       SALES PROGRESS
    ===================================================== */

    run_sales_progress(filters) {

        const target =
            document.getElementById(
                "sales-progress-block"
            );

        if (!target) {
            return;
        }


        this.show_loading(target);


        this.call_report(

            "Sales Progress",

            {

                from_date:
                    filters.from_date,

                to_date:
                    filters.to_date,

                company:
                    filters.company,

                view_type:
                    filters.view === "amt"
                        ? "amt"
                        : "qty"
            },

            (result) => {

                this.render_chart(
                    target,
                    result,
                    "Sales Progress"
                );
            }
        );
    }


    /* =====================================================
       TOP CHART
    ===================================================== */

    run_top_chart(filters) {

        const target =
            document.getElementById(
                "top-selling-block"
            );

        if (!target) {
            return;
        }


        this.show_loading(target);


        this.call_report(

            "Top Selling Items 1",

            {

                from_date:
                    filters.from_date,

                to_date:
                    filters.to_date,

                company:
                    filters.company,

                metric:
                    filters.view === "amt"
                        ? "amt"
                        : "qty"
            },

            (result) => {

                this.render_chart(
                    target,
                    result,
                    "Top Selling Items 1"
                );
            }
        );
    }


    /* =====================================================
       LEAST CHART
    ===================================================== */

    run_least_chart(filters) {

        const target =
            document.getElementById(
                "least-selling-block"
            );

        if (!target) {
            return;
        }


        this.show_loading(target);


        this.call_report(

            "Least Selling Items",

            {

                from_date:
                    filters.from_date,

                to_date:
                    filters.to_date,

                company:
                    filters.company,

                metric:
                    filters.view === "amt"
                        ? "amt"
                        : "qty"
            },

            (result) => {

                this.render_chart(
                    target,
                    result,
                    "Least Selling Items"
                );
            }
        );
    }


    /* =====================================================
       SALES VS STOCK
    ===================================================== */

   run_sales_vs_stock(filters) {

    const target =
        document.getElementById(
            "sale-vs-stock-block"
        );

    if (!target) {
        return;
    }

    this.show_loading(target);

    this.call_report(

        "Sales vs Stock",

        {
            from_date:
                filters.from_date,

            to_date:
                filters.to_date,

            company:
                filters.company,

            metric:
                filters.view === "amt"
                    ? "amt"
                    : "qty"
        },

        (result) => {

            /*
             * Render chart
             */

            this.render_chart(
                target,
                result,
                "Sales vs Stock"
            );


            /*
             * SAME API RESPONSE
             * table ko bhejo.
             */

            document.dispatchEvent(

                new CustomEvent(
                    "sellingDashboardSalesVsStockData",
                    {
                        detail: {
                            result: result,
                            filters: filters
                        }
                    }
                )

            );
        }
    );
}


    /* =====================================================
       RENDER CHART
    ===================================================== */

    render_chart(
        target,
        result,
        report_name
    ) {

        if (!target) {
            return;
        }


        target.innerHTML = "";


        if (
            result &&
            result.chart
        ) {

            try {

                new frappe.Chart(
                    target,
                    result.chart
                );

                return;

            } catch (error) {

                console.error(
                    `${report_name} chart error`,
                    error
                );
            }
        }


        /*
         * If report has result but no chart
         */

        if (
            result &&
            Array.isArray(result.result) &&
            result.result.length
        ) {

            this.render_table(
                target,
                result.result
            );

            return;
        }


        target.innerHTML = `
            <div class="selling-dashboard-empty">
                No data available
            </div>
        `;
    }


    /* =====================================================
       RENDER SIMPLE TABLE
    ===================================================== */

    render_table(target, rows) {

        if (
            !rows ||
            !rows.length
        ) {

            target.innerHTML = `
                <div class="selling-dashboard-empty">
                    No data available
                </div>
            `;

            return;
        }


        const columns =
            Object.keys(rows[0]);


        let html = `
            <div style="overflow-x:auto;">

                <table
                    class="table table-bordered"
                    style="width:100%;">

                    <thead>
                        <tr>
        `;


        columns.forEach(column => {

            html += `
                <th>
                    ${frappe.utils.escape_html(
                        column
                    )}
                </th>
            `;
        });


        html += `
                        </tr>
                    </thead>

                    <tbody>
        `;


        rows.forEach(row => {

            html += `<tr>`;


            columns.forEach(column => {

                const value =
                    row[column] == null
                        ? ""
                        : String(row[column]);


                html += `
                    <td>
                        ${frappe.utils.escape_html(
                            value
                        )}
                    </td>
                `;
            });


            html += `</tr>`;
        });


        html += `
                    </tbody>
                </table>

            </div>
        `;


        target.innerHTML = html;
    }


    /* =====================================================
       LOADING
    ===================================================== */

    show_loading(target) {

        target.innerHTML = `
            <div class="selling-dashboard-loading">
                Loading...
            </div>
        `;
    }


    /* =====================================================
       CUSTOM HTML BLOCK LOADER
    ===================================================== */

    load_html_block(
        block_name,
        target_selector
    ) {

        return new Promise(resolve => {

            frappe.call({

                method:
                    "frappe.client.get",

                args: {

                    doctype:
                        "Custom HTML Block",

                    name:
                        block_name
                },

                callback: r => {

                    const doc =
                        r.message;


                    if (!doc) {

                        console.warn(
                            `Custom HTML Block not found: ${block_name}`
                        );

                        resolve();

                        return;
                    }


                    const target =
                        document.querySelector(
                            target_selector
                        );


                    if (!target) {

                        resolve();

                        return;
                    }


                    /*
                     * HTML
                     */

                    target.innerHTML =
                        doc.html || "";


                    /*
                     * CSS
                     */

                    if (doc.style) {

                        const style =
                            document.createElement(
                                "style"
                            );

                        style.textContent =
                            doc.style;

                        document.head.appendChild(
                            style
                        );
                    }


                    /*
                     * JavaScript
                     */

                    if (
                        doc.javascript ||
                        doc.script
                    ) {

                        const script =
                            document.createElement(
                                "script"
                            );


                        script.type =
                            "text/javascript";


                        script.textContent = `

                            (function() {

                                const root_element =
                                    document.querySelector(
                                        ${JSON.stringify(
                                            target_selector
                                        )}
                                    );

                                try {

                                    ${
                                        doc.javascript ||
                                        doc.script
                                    }

                                } catch (error) {

                                    console.error(
                                        "Custom HTML Block error: ${block_name}",
                                        error
                                    );

                                }

                            })();

                        `;


                        document.body.appendChild(
                            script
                        );
                    }


                    resolve();
                },

                error: err => {

                    console.error(
                        `Unable to load ${block_name}`,
                        err
                    );

                    resolve();
                }
            });
        });
    }
}