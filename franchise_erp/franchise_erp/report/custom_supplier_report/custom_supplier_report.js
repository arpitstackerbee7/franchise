// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt


frappe.query_reports["Custom Supplier Report"] = {
    filters: [
        {
            fieldname: "supplier",
            label: "Supplier",
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "supplier_group",
            label: "Supplier Group",
            fieldtype: "Link",
            options: "Supplier Group"
        },
        {
            fieldname: "supplier_type",
            label: "Supplier Type",
            fieldtype: "Select",
            options: "\nCompany\nIndividual"
        },
        {
            fieldname: "country",
            label: "Country",
            fieldtype: "Link",
            options: "Country"
        },
        {
            fieldname: "city",
            label: "City",
            fieldtype: "Data"
        },
        {
            fieldname: "disabled",
            label: "Disabled",
            fieldtype: "Select",
            options: "\n0\n1"
        }
    ]
};
