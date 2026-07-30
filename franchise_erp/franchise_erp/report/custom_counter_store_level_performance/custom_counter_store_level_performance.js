// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Counter Store-Level Performance"] = {
    filters: [
        {
            fieldname: "sales_manager",
            label: __("Sales Manager"),
            fieldtype: "Link",
            options: "User"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (
            column.fieldname === "counter_count" &&
            data &&
            data.counter_count
        ) {
            return `
                <a
                    href="#"
                    class="counter-count-link"
                    data-counter-details="${encodeURIComponent(
                        data.counter_details || "[]"
                    )}"
                    style="
                        font-weight: 600;
                        text-decoration: underline;
                        cursor: pointer;
                    "
                >
                    ${data.counter_count}
                </a>
            `;
        }

        return value;
    },

    onload: function (report) {
        $(document)
            .off(
                "click.custom_counter_report",
                ".counter-count-link"
            )
            .on(
                "click.custom_counter_report",
                ".counter-count-link",
                function (e) {
                    e.preventDefault();

                    let counters = [];

                    try {
                        const counter_details = decodeURIComponent(
                            $(this).attr("data-counter-details") || "%5B%5D"
                        );

                        counters = JSON.parse(counter_details);
                    } catch (error) {
                        console.error(
                            "Unable to parse counter details:",
                            error
                        );

                        frappe.msgprint(
                            __("Unable to load counter details.")
                        );

                        return;
                    }

                    show_counter_dialog(counters);
                }
            );
    }
};


function show_counter_dialog(counters) {
    const dialog = new frappe.ui.Dialog({
        title: __("Assigned Counters"),
        size: "small",
        fields: [
            {
                fieldname: "counter_list",
                fieldtype: "HTML"
            }
        ]
    });

    let html = "";

    if (!counters || !counters.length) {
        html = `
            <div class="text-muted">
                ${__("No counters found.")}
            </div>
        `;
    } else {
        html = `
            <div class="counter-list">
                ${counters.map((counter, index) => {

                    const customer_name =
                        frappe.utils.escape_html(
                            counter.customer_name || counter.name
                        );

                    const customer_id =
                        frappe.utils.escape_html(
                            counter.name || ""
                        );

                    const company =
                        frappe.utils.escape_html(
                            counter.represents_company || ""
                        );

                    return `
                        <div
                            style="
                                padding: 12px 4px;
                                border-bottom: ${
                                    index === counters.length - 1
                                        ? "none"
                                        : "1px solid var(--border-color)"
                                };
                            "
                        >
                            <a
                                href="#"
                                class="counter-customer-link"
                                data-customer="${customer_id}"
                                style="
                                    font-weight: 600;
                                    cursor: pointer;
                                "
                            >
                                ${customer_name}
                            </a>

                            ${
                                customer_id !== customer_name
                                    ? `
                                        <div
                                            class="text-muted"
                                            style="
                                                font-size: 12px;
                                                margin-top: 2px;
                                            "
                                        >
                                            ${customer_id}
                                        </div>
                                    `
                                    : ""
                            }

                            ${
                                company
                                    ? `
                                        <div
                                            class="text-muted"
                                            style="
                                                font-size: 12px;
                                                margin-top: 2px;
                                            "
                                        >
                                            ${__("Company")}: ${company}
                                        </div>
                                    `
                                    : ""
                            }
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    dialog.fields_dict.counter_list.$wrapper.html(html);

    dialog.fields_dict.counter_list.$wrapper
        .off("click", ".counter-customer-link")
        .on(
            "click",
            ".counter-customer-link",
            function (e) {
                e.preventDefault();

                const customer = $(this).attr("data-customer");

                if (!customer) {
                    return;
                }

                const route = frappe.utils.get_form_link(
                    "Customer",
                    customer
                );

                window.open(route, "_blank");
            }
        );

    dialog.show();
}