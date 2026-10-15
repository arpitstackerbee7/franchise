// Copyright (c) 2026
// For license information, please see license.txt


frappe.query_reports["Custom Financial Statement"] = {

    filters: [

        // ====================================================
        // COMPANY
        // ====================================================

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default:
                frappe.defaults.get_user_default(
                    "Company"
                )
        },


        // ====================================================
        // FISCAL YEAR
        // ====================================================

        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Link",
            options: "Fiscal Year",
            reqd: 1,
            default:
                frappe.defaults.get_user_default(
                    "fiscal_year"
                ),

            on_change: function(report) {

                const fy =
                    report.get_filter_value(
                        "fiscal_year"
                    );

                if (!fy) {
                    return;
                }

                frappe.db.get_value(
                    "Fiscal Year",
                    fy,
                    [
                        "year_start_date",
                        "year_end_date"
                    ]
                ).then(r => {

                    if (!r.message) {
                        return;
                    }

                    report.set_filter_value(
                        "from_date",
                        r.message.year_start_date
                    );

                    report.set_filter_value(
                        "to_date",
                        r.message.year_end_date
                    );

                });
            }
        },


        // ====================================================
        // FROM DATE
        // ====================================================

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },


        // ====================================================
        // TO DATE
        // ====================================================

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        },


        // ====================================================
        // COST CENTER
        // ====================================================

        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },


        // ====================================================
        // PROJECT
        // ====================================================

        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },


        // ====================================================
        // FINANCE BOOK
        // ====================================================

        {
            fieldname: "finance_book",
            label: __("Finance Book"),
            fieldtype: "Link",
            options: "Finance Book"
        },


        // ====================================================
        // SHOW ZERO VALUES
        // ====================================================

        {
            fieldname: "show_zero_values",
            label: __("Show Zero Values"),
            fieldtype: "Check",
            default: 1
        }

    ],


    // ========================================================
    // FORMATTER
    // ========================================================

    formatter: function(
        value,
        row,
        column,
        data,
        default_formatter
    ) {

        let formatted_value =
            default_formatter(
                value,
                row,
                column,
                data
            );

        if (!data) {
            return formatted_value;
        }

        const fieldname =
            column.fieldname;


        // ====================================================
        // SECTION HEADER
        // ====================================================

        if (data.is_section_header) {

            if (
                fieldname === "expense" ||
                fieldname === "income"
            ) {

                const label =
                    fieldname === "expense"
                        ? data.expense
                        : data.income;

                if (!label) {
                    return "";
                }

                return `
                    <div
                        style="
                            font-weight:700;
                            color:#1f4e78;
                            font-size:14px;
                            line-height:20px;
                            padding:0;
                            margin:0;
                            white-space:nowrap;
                            overflow:visible;
                        "
                    >
                        ${frappe.utils.escape_html(label)}
                    </div>
                `;
            }

            return "";
        }


        // ====================================================
// STATEMENT TYPE FLAGS
// ====================================================

const expenseStatement =
    cint(
        data.expense_is_statement_type
        || 0
    );

const incomeStatement =
    cint(
        data.income_is_statement_type
        || 0
    );


// ====================================================
// EXPENSE STATEMENT TYPE
// ====================================================

if (
    fieldname === "expense"
    &&
    expenseStatement
) {

    return render_statement_type(
        "expense",
        data
    );
}


// ====================================================
// INCOME STATEMENT TYPE
// ====================================================

if (
    fieldname === "income"
    &&
    incomeStatement
) {

    return render_statement_type(
        "income",
        data
    );
}


        // ====================================================
        // TOTAL / SUBTOTAL / GP / KPI
        // ====================================================

        if (
            data.is_total
            ||
            data.is_subtotal
            ||
            data.is_gross_profit
            ||
            data.is_kpi
        ) {

            if (
                fieldname === "expense"
                &&
                data.expense
            ) {

                return `
                    <span
                        style="
                            font-weight:700;
                        "
                    >
                        ${frappe.utils.escape_html(
                            data.expense
                        )}
                    </span>
                `;
            }

            if (
                fieldname === "income"
                &&
                data.income
            ) {

                return `
                    <span
                        style="
                            font-weight:700;
                        "
                    >
                        ${frappe.utils.escape_html(
                            data.income
                        )}
                    </span>
                `;
            }

            return formatted_value;
        }


        return formatted_value;
    },


    // ========================================================
    // ONLOAD
    // ========================================================

    onload: function(report) {

        const fy =
            report.get_filter_value(
                "fiscal_year"
            );

        if (fy) {

            frappe.db.get_value(
                "Fiscal Year",
                fy,
                [
                    "year_start_date",
                    "year_end_date"
                ]
            ).then(r => {

                if (!r.message) {
                    return;
                }

                if (
                    !report.get_filter_value(
                        "from_date"
                    )
                ) {

                    report.set_filter_value(
                        "from_date",
                        r.message.year_start_date
                    );
                }

                if (
                    !report.get_filter_value(
                        "to_date"
                    )
                ) {

                    report.set_filter_value(
                        "to_date",
                        r.message.year_end_date
                    );
                }

            });
        }

        setTimeout(
            function() {

                install_financial_tree_events(
                    report
                );

            },
            500
        );
    },


    // ========================================================
    // AFTER REFRESH
    // ========================================================

    after_refresh: function(report) {

        setTimeout(
            function() {

                install_financial_tree_events(
                    report
                );

            },
            300
        );
    }

};


// ============================================================
// STATEMENT TYPE RENDER
// ============================================================
function render_statement_type(
    side,
    data
) {

    const treeId =
        data[
            `${side}_tree_id`
        ] || "";

    const treeParent =
        data[
            `${side}_tree_parent`
        ] || "";

    const indent =
        cint(
            data[
                `${side}_indent`
            ] || 0
        );

    const label =
        data[
            side
        ] || "";

    const hasChildren =
        cint(
            data[
                `${side}_has_children`
            ] || 0
        );

    if (!label) {
        return "";
    }


    // ====================================================
    // IMPORTANT:
    // statement_parent IS THE SOURCE FOR BOLDING
    // ====================================================

    const statementParent =
        data.statement_parent
        || data[`${side}_statement_parent`]
        || "";

    const fontWeight =
        statementParent
            ? "400"
            : "700";


    const escapedLabel =
        frappe.utils.escape_html(
            label
        );

    const escapedTreeId =
        frappe.utils.escape_html(
            treeId
        );

    const escapedTreeParent =
        frappe.utils.escape_html(
            treeParent
        );


    return `
        <div
            class="
                custom-financial-statement-type
                custom-financial-tree-toggle
            "
            data-side="${side}"
            data-tree-id="${escapedTreeId}"
            data-tree-parent="${escapedTreeParent}"
            data-expanded="1"
            style="
                padding-left:${indent * 20}px;
                font-weight:${fontWeight} !important;
                cursor:${
                    hasChildren
                        ? "pointer"
                        : "default"
                };
                white-space:nowrap;
            "
        >

            ${
                hasChildren
                    ? `
                        <span
                            class="
                                custom-financial-tree-arrow
                            "
                            style="
                                display:inline-block;
                                width:18px;
                                margin-right:4px;
                                font-weight:400 !important;
                            "
                        >
                            ▼
                        </span>
                    `
                    : `
                        <span
                            style="
                                display:inline-block;
                                width:22px;
                            "
                        ></span>
                    `
            }

            <span
                style="
                    font-weight:${fontWeight} !important;
                "
            >
                ${escapedLabel}
            </span>

        </div>
    `;
}

// ============================================================
// INSTALL EVENTS
// ============================================================

function install_financial_tree_events(
    report
) {

    if (
        !report
        ||
        !report.page
        ||
        !report.page.wrapper
    ) {
        return;
    }

    const wrapper =
        report.page.wrapper;

    $(wrapper).off(
        ".custom_financial_tree"
    );

    $(wrapper).on(
        "click.custom_financial_tree",
        ".custom-financial-tree-toggle",
        function(e) {

            e.preventDefault();
            e.stopPropagation();

            const clicked =
                $(this);

            const side =
                clicked.attr(
                    "data-side"
                );

            const treeId =
                clicked.attr(
                    "data-tree-id"
                );

            if (
                !side
                ||
                !treeId
            ) {
                return;
            }

            const expanded =
                clicked.attr(
                    "data-expanded"
                ) === "1";

            clicked.attr(
                "data-expanded",
                expanded
                    ? "0"
                    : "1"
            );

            update_tree_arrows(
                wrapper,
                side
            );

            refresh_tree_visibility(
                wrapper,
                side
            );
        }
    );


    setTimeout(
        function() {

            update_tree_arrows(
                wrapper,
                "expense"
            );

            update_tree_arrows(
                wrapper,
                "income"
            );

            refresh_tree_visibility(
                wrapper,
                "expense"
            );

            refresh_tree_visibility(
                wrapper,
                "income"
            );

        },
        100
    );
}


// ============================================================
// UPDATE ARROWS
// ============================================================

function update_tree_arrows(
    wrapper,
    side
) {

    $(wrapper)
        .find(
            `.custom-financial-tree-toggle[data-side="${side}"]`
        )
        .each(
            function() {

                const element =
                    $(this);

                const expanded =
                    element.attr(
                        "data-expanded"
                    ) === "1";

                element
                    .find(
                        ".custom-financial-tree-arrow"
                    )
                    .first()
                    .text(
                        expanded
                            ? "▼"
                            : "▶"
                    );
            }
        );
}


// ============================================================
// REFRESH VISIBILITY
// ============================================================

function refresh_tree_visibility(
    wrapper,
    side
) {

    const elements =
        $(wrapper).find(`
            .custom-financial-tree-toggle[data-side="${side}"],
            .custom-financial-tree-leaf[data-side="${side}"]
        `);

    const byId = {};

    elements.each(
        function() {

            const element =
                $(this);

            const treeId =
                element.attr(
                    "data-tree-id"
                );

            if (treeId) {

                byId[
                    treeId
                ] = element;
            }
        }
    );


    elements.each(
        function() {

            const element =
                $(this);

            let parentId =
                element.attr(
                    "data-tree-parent"
                ) || "";

            let visible = true;

            const visited = {};

            while (parentId) {

                if (
                    visited[
                        parentId
                    ]
                ) {
                    break;
                }

                visited[
                    parentId
                ] = true;

                const parent =
                    byId[
                        parentId
                    ];

                if (!parent) {
                    break;
                }

                if (
                    parent.hasClass(
                        "custom-financial-tree-toggle"
                    )
                    &&
                    parent.attr(
                        "data-expanded"
                    ) === "0"
                ) {

                    visible = false;

                    break;
                }

                parentId =
                    parent.attr(
                        "data-tree-parent"
                    ) || "";
            }

            set_tree_element_visibility(
                element,
                visible
            );
        }
    );
}


// ============================================================
// SET ROW VISIBILITY
// ============================================================

function set_tree_element_visibility(
    element,
    visible
) {

    if (
        !element
        ||
        !element.length
    ) {
        return;
    }

    const cell =
        element.closest(
            ".dt-cell"
        );

    if (!cell.length) {

        element.css(
            "display",
            visible
                ? ""
                : "none"
        );

        return;
    }

    const row =
        cell.closest(
            ".dt-row"
        );

    cell.css(
        "display",
        visible
            ? ""
            : "none"
    );

    if (!row.length) {
        return;
    }

    const cells =
        row.find(
            ".dt-cell"
        );

    const cellIndex =
        cells.index(
            cell
        );

    if (
        cellIndex >= 0
        &&
        cellIndex + 1 < cells.length
    ) {

        cells
            .eq(
                cellIndex + 1
            )
            .css(
                "display",
                visible
                    ? ""
                    : "none"
            );
    }
}