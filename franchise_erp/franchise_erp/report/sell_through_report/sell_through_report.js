frappe.query_reports["Sell Through Report"] = {
    filters: [
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

    formatter: function(value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        if (!data) {
            return value;
        }

        // Total Row Highlight
        if (data.is_total) {
            value = `<span style="
                font-weight: bold;
                background-color: #FFE699;
                display: block;
                padding: 4px;
            ">${value}</span>`;
        }

        // Status Color
        if (column.fieldname === "status") {

            if (data.status === "GREEN") {
                value = `<span style="
                    background-color: #28a745;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                ">${data.status}</span>`;
            }

            else if (data.status === "YELLOW") {
                value = `<span style="
                    background-color: #ffc107;
                    color: black;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                ">${data.status}</span>`;
            }

            else if (data.status === "RED") {
                value = `<span style="
                    background-color: #dc3545;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                ">${data.status}</span>`;
            }
        }

        return value;
    }
};