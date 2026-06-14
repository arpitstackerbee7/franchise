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
        // if (data.is_total) {
        //     value = `<span style="
        //         font-weight: bold;
        //         background-color: #FFE699;
        //         display: block;
        //         padding: 4px;
        //     ">${value}</span>`;
        // }
        if (data && data.is_total && column.fieldname != "status") {
            return `
                <div style="
                    background:#FFF4B8;
                    font-weight:bold;
                    display:block;
                    margin:-8px;
                    padding:8px;
                    min-height:100%;
                ">
                    ${value}
                </div>
            `;
        }

        // Status Color
        // if (column.fieldname === "status") {

        //     if (data.status === "GREEN") {
        //         value = `<span style="
        //             background-color: #28a745;
        //             color: white;
        //             padding: 3px 8px;
        //             border-radius: 4px;
        //             font-weight: bold;
        //         ">${data.status}</span>`;
        //     }

        //     else if (data.status === "YELLOW") {
        //         value = `<span style="
        //             background-color: #ffc107;
        //             color: black;
        //             padding: 3px 8px;
        //             border-radius: 4px;
        //             font-weight: bold;
        //         ">${data.status}</span>`;
        //     }

        //     else if (data.status === "RED") {
        //         value = `<span style="
        //             background-color: #dc3545;
        //             color: white;
        //             padding: 3px 8px;
        //             border-radius: 4px;
        //             font-weight: bold;
        //         ">${data.status}</span>`;
        //     }
        // }
        if (column.fieldname === "status") {

            let bg = "";
            let text = "#000";

            if (data.status === "GREEN") {
                bg = "#D4EDDA";      // Light Green
                text = "#155724";
            }
            else if (data.status === "YELLOW") {
                bg = "#FFF3CD";      // Light Yellow
                text = "#856404";
            }
            else if (data.status === "RED") {
                bg = "#F8D7DA";      // Light Red
                text = "#721C24";
            }

            value = `
                <div style="
                    background:${bg};
                    color:#222;
                    text-align:center;
                    margin:-8px;
                    padding:8px;
                    min-height:100%;
                ">
                    ${data.status || ""}
                </div>
            `;
        }

        return value;
    }
};