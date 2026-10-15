frappe.query_reports["Brand Level Purchase Sale & Stock Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },

        {
            fieldname: "brand",
            label: __("Brand"),
            fieldtype: "Link",
            options: "Brand"
        },

        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            options: "Item Group"
        },

        {
            fieldname: "item_code",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item"
        },

        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            options: "Warehouse"
        },

        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier"
        },

        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        },

        {
            fieldname: "limit",
            label: __("Limit"),
            fieldtype: "Int",
            default: 100
        },

        {
            fieldname: "order_by",
            label: __("Order By"),
            fieldtype: "Select",
            options: [
                "Brand",
                "Item Code",
                "Item Name",
                "Purchase Qty",
                "Purchase Value",
                "Sale Qty",
                "Sale Value",
                "Closing Qty",
                "Stock Value"
            ].join("\n"),
            default: "Brand"
        },

        {
            fieldname: "order_direction",
            label: __("Order Direction"),
            fieldtype: "Select",
            options: [
                "Ascending",
                "Descending"
            ].join("\n"),
            default: "Ascending"
        }
    ],

    onload: function (report) {
        report.page.add_inner_button(__("Refresh"), function () {
            report.refresh();
        });
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) {
            return value;
        }

        if (
            column.fieldname === "purchase_value" ||
            column.fieldname === "sale_value" ||
            column.fieldname === "opening_value" ||
            column.fieldname === "closing_value" ||
            column.fieldname === "stock_value"
        ) {
            return `<span style="text-align:right;display:block;">
                ${value}
            </span>`;
        }

        return value;
    }
};