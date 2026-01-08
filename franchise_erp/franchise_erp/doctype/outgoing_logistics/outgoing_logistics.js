// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Outgoing Logistics", {
	refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Fetch Sales Invoice ID"),
                () => open_sales_invoice_mapper(frm),
                __("Get Items From")
            );
        }
	},
});

function open_sales_invoice_mapper(frm) {
    if (!frm.doc.consignee) frappe.throw({ title: __("Mandatory"), message: __("Please select consignee first") });
    if (!frm.doc.owner_site) frappe.throw({ title: __("Mandatory"), message: __("Please select Owner Site first") });

   new frappe.ui.form.MultiSelectDialog({
    doctype: "Sales Invoice",
    target: frm,
    setters: {
        customer: frm.doc.consignee,
        company: frm.doc.owner_site
    },
    add_filters_group: 1,
    date_field: "transaction_date",
    columns: [  
        { fieldname: "name", label: __("Sales Invoice"), fieldtype: "Link", options: "Sales Invoice" },
        "supplier", "company"
    ],
    get_query() {
        return {
            filters: [
                ["Sales Invoice", "docstatus", "=", 1],
                ["Sales Invoice", "custom_outgoing_logistics_reference", "=", ""],
                ["Sales Invoice", "customer", "=", frm.doc.consignee],
                ["Sales Invoice", "company", "=", frm.doc.owner_site]
            ]
        };
    },
  action(selections) {
    if (!selections || !selections.length) {
        frappe.msgprint(__("Please select at least one Sales Invoice"));
        return;
    }

    // Get list of already added POs
    const existing_sis = (frm.doc.sales_invoice_no || []).map(r => r.sales_invoice);

    selections.forEach(si => {
        // Add only if not already in table
        if (!existing_sis.includes(si)) {
            let row = frm.add_child("sales_invoice_no");
            row.sales_invoice = si;
        }
    });

    frm.refresh_field("sales_invoice_no");
    this.dialog.hide();
}
    });
}