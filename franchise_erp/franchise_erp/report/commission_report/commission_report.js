frappe.query_reports["Commission Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
		// CHANGE 20 — Added Agent filter
        {
            fieldname: "agent",
            label: __("Agent"),
            fieldtype: "Link",
            options: "Supplier",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.item_code && data.item_code === "TOTAL") {
            value = `<b>${value}</b>`;
        }

        if (
            column.fieldname === "receipts" ||
            column.fieldname === "receipts_without_gst" ||
            column.fieldname === "collectable_amount"
        ) {
            if (data && flt(data[column.fieldname]) < 0) {
                value = `<span style="color: var(--red-500);">${value}</span>`;
            }
        }

        return value;
    },
};