frappe.query_reports["Replenishment Report - Sales for Slow Moving"] = {

    filters: [

        // --------------------------------------------------
        // FROM DATE
        // --------------------------------------------------

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },

        // --------------------------------------------------
        // TO DATE
        // --------------------------------------------------

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },

        // --------------------------------------------------
        // BRAND
        // --------------------------------------------------

        {
            fieldname: "brand",
            label: __("Brand"),
            fieldtype: "Link",
            options: "Brand"
        },

        // --------------------------------------------------
        // ITEM CODE
        // --------------------------------------------------

        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item"
        },

        // --------------------------------------------------
        // STYLE
        // --------------------------------------------------

        {
            fieldname: "style",
            label: __("Style"),
            fieldtype: "Data"
        },

        // --------------------------------------------------
        // ITEM LIMIT
        //
        // 100 = first 100 items
        // 500 = first 500 items
        // 1000 = first 1000 items
        // 0 = ALL ITEMS
        // --------------------------------------------------

        {
            fieldname: "item_limit",
            label: __("Item Limit"),
            fieldtype: "Int",
            default: 100,
            description: __(
                "Testing ke liye items ki maximum quantity. 0 = All Items."
            )
        },
		{
			fieldname: "sort_order",
			label: __("Sort Order"),
			fieldtype: "Select",
			options: [
				"DESC",
				"ASC"
			].join("\n"),
			default: "DESC"
		},
        // --------------------------------------------------
        // STOCK MOVEMENT OPERATOR
        // --------------------------------------------------

        {
            fieldname: "stock_movement_operator",
            label: __("Stock Movement"),
            fieldtype: "Select",
            options: [
                "",
                "<",
                "<=",
                "=",
                ">=",
                ">"
            ].join("\n")
        },

        // --------------------------------------------------
        // STOCK MOVEMENT VALUE
        // --------------------------------------------------

        {
            fieldname: "stock_movement_value",
            label: __("Stock Movement %"),
            fieldtype: "Float"
        }
    ],

    // ======================================================
    // ONLOAD
    // ======================================================

    onload: function(report) {

        frappe.query_report.get_filter(
            "stock_movement_operator"
        ).$input.on("change", function() {

            const operator =
                frappe.query_report.get_filter_value(
                    "stock_movement_operator"
                );

            if (!operator) {

                frappe.query_report.set_filter_value(
                    "stock_movement_value",
                    null
                );
            }
        });
    },

    // ======================================================
    // FORMATTER
    // ======================================================

    formatter: function(
        value,
        row,
        column,
        data,
        default_formatter
    ) {

        value = default_formatter(
            value,
            row,
            column,
            data
        );

        if (!data) {
            return value;
        }

        // --------------------------------------------------
        // STOCK MOVEMENT %
        // --------------------------------------------------

        if (
            column.fieldname ===
            "stock_movement_percent"
        ) {

            const movement = parseFloat(
                data.stock_movement_percent || 0
            );

            let background = "";
            let text = "";

            if (movement < 30) {

                background = "#F8D7DA";
                text = "#721C24";

            } else if (movement < 60) {

                background = "#FFF3CD";
                text = "#856404";

            } else {

                background = "#D4EDDA";
                text = "#155724";
            }

            return `
                <div style="
                    background:${background};
                    color:${text};
                    text-align:center;
                    font-weight:bold;
                    margin:-8px;
                    padding:8px;
                    min-height:100%;
                ">
                    ${value}
                </div>
            `;
        }

        // --------------------------------------------------
        // AVERAGE STOCK MOVEMENT %
        // --------------------------------------------------

        if (
            column.fieldname ===
            "average_stock_movement_percent"
        ) {

            const movement = parseFloat(
                data.average_stock_movement_percent || 0
            );

            let background = "";
            let text = "";

            if (movement < 30) {

                background = "#F8D7DA";
                text = "#721C24";

            } else if (movement < 60) {

                background = "#FFF3CD";
                text = "#856404";

            } else {

                background = "#D4EDDA";
                text = "#155724";
            }

            return `
                <div style="
                    background:${background};
                    color:${text};
                    text-align:center;
                    font-weight:bold;
                    margin:-8px;
                    padding:8px;
                    min-height:100%;
                ">
                    ${value}
                </div>
            `;
        }

        // --------------------------------------------------
        // SLOW MOVING
        // --------------------------------------------------

        if (
            column.fieldname === "slow_moving"
        ) {

            if (
                data.slow_moving === "YES"
            ) {

                return `
                    <div style="
                        background:#F8D7DA;
                        color:#721C24;
                        text-align:center;
                        font-weight:bold;
                        margin:-8px;
                        padding:8px;
                        min-height:100%;
                    ">
                        YES
                    </div>
                `;

            }

            return `
                <div style="
                    background:#D4EDDA;
                    color:#155724;
                    text-align:center;
                    font-weight:bold;
                    margin:-8px;
                    padding:8px;
                    min-height:100%;
                ">
                    NO
                </div>
            `;
        }

        return value;
    }
};