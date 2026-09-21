// frappe.query_reports["Custom Account Receivable"] = {
//     filters: [
//         {
//             fieldname: "company",
//             label: __("Company"),
//             fieldtype: "Link",
//             options: "Company",
//             default: frappe.defaults.get_user_default("Company"),
//             reqd: 1,
//         },
//         {
//             fieldname: "report_date",
//             label: __("As On Date"),
//             fieldtype: "Date",
//             default: frappe.datetime.get_today(),
//             reqd: 1,
//         },
//         {
//             fieldname: "ageing_based_on",
//             label: __("Ageing Based On"),
//             fieldtype: "Select",
//             options: "Due Date\nPosting Date\nSupplier Invoice Date",
//             default: "Due Date",
//         },
//         {
//             fieldname: "party_type",
//             label: __("Party Type"),
//             fieldtype: "Select",
//             options: "\nCustomer\nSupplier\nEmployee\nShareholder\nStudent",
//             default: "Customer",
//         },
//         {
//             fieldname: "party",
//             label: __("Party"),
//             fieldtype: "MultiSelectList",
//             get_data: function(txt) {
//                 if (!frappe.query_report.filters) return;
//                 let party_type = frappe.query_report.get_filter_value("party_type");
//                 if (!party_type) return;
//                 return frappe.db.get_link_options(party_type, txt);
//             },
//         },
//         {
//             fieldname: "customer",
//             label: __("Customer"),
//             fieldtype: "MultiSelectList",
//             get_data: function(txt) {
//                 return frappe.db.get_link_options("Customer", txt);
//             },
//         },
//         {
//             fieldname: "group_by_party",
//             label: __("Group By Party"),
//             fieldtype: "Check",
//             default: 0,
//         },
//         {
//             fieldname: "show_future_payments",
//             label: __("Show Future Payments"),
//             fieldtype: "Check",
//             default: 0,
//         },
//     ],

//     formatter: function(value, row, column, data, default_formatter) {
//         value = default_formatter(value, row, column, data);

//         if (data && data.is_subtotal) {
//             value = `<b>${value || ""}</b>`;
//         } else if (data && data.is_group) {
//             value = `<span style="color:#6c757d;">${value || ""}</span>`;
//         }

//         return value;
//     },
// };


frappe.query_reports["Custom Account Receivable"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "report_date",
            label: __("As On Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "ageing_based_on",
            label: __("Ageing Based On"),
            fieldtype: "Select",
            options: "Due Date\nPosting Date\nSupplier Invoice Date",
            default: "Due Date",
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Select",
            options: "\nCustomer\nSupplier\nEmployee\nShareholder\nStudent",
            default: "Customer",
        },
        {
            fieldname: "customer_group",
            label: __("Customer Group"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer Group", txt);
            },
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                if (!frappe.query_report.filters) return;
                let party_type = frappe.query_report.get_filter_value("party_type");
                if (!party_type) return;
                return frappe.db.get_link_options(party_type, txt);
            },
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Customer", txt);
            },
        },
        {
            fieldname: "payment_terms_template",
            label: __("Payment Terms Template"),
            fieldtype: "Link",
            options: "Payment Terms Template",
        },
        {
            fieldname: "receivable_account",
            label: __("Receivable Account"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Account", txt, {
                    account_type: "Receivable",
                    company: frappe.query_report.get_filter_value("company"),
                });
            },
        },
        {
            fieldname: "group_by_party",
            label: __("Group By Party"),
            fieldtype: "Check",
            default: 0,
        },
        {
            fieldname: "based_on_payment_terms",
            label: __("Based On Payment Terms"),
            fieldtype: "Check",
            default: 0,
        },
        {
            fieldname: "show_future_payments",
            label: __("Show Future Payments"),
            fieldtype: "Check",
            default: 0,
        },
    ],

    onload: function(report) {
        if (!document.getElementById("careceivable-bold-css")) {
            const style = document.createElement("style");
            style.id = "careceivable-bold-css";
            style.innerHTML = `
                .dt-cell__content b,
                .dt-cell__content b a {
                    font-weight: 900 !important;
                    color: #000 !important;
                }
            `;
            document.head.appendChild(style);
        }
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!value) value = "&nbsp;";

        if (data && data.is_subtotal) {
            value = `<b style="display:block; background-color:#ffd6d6;">${value}</b>`;
        } else if (data && data.is_group) {
            value = `<b style="display:block; background-color:#e6e6e6; color:#000; font-weight:900 !important;">${value}</b>`;
        }
        return value;
    },
};