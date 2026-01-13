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

frappe.ui.form.on("Outgoing Logistics", {

    onload: function (frm) {
        // When doc is created from another document
        if (frm.doc.owner_site && !frm.doc.station_from) {
            set_station_from_company(frm);
        }

        if (frm.doc.consignee && !frm.doc.station_to) {
            set_station_to_customer(frm);
        }
    },

    // STATION FROM → COMPANY
    owner_site: function (frm) {
        set_station_from_company(frm);
    },

    // STATION TO → CUSTOMER
    consignee: function (frm) {
        set_station_to_customer(frm);
    }
});


/* ------------------------------
   Helper functions
------------------------------ */

function set_station_from_company(frm) {
    if (!frm.doc.owner_site) {
        frm.set_value("station_from", "");
        return;
    }

    frappe.db.get_list("Address", {
        filters: [
            ["Dynamic Link", "link_doctype", "=", "Company"],
            ["Dynamic Link", "link_name", "=", frm.doc.owner_site]
        ],
        fields: ["name", "custom_citytown"],
        limit: 1
    }).then(addresses => {
        if (!addresses || !addresses.length) {
            frm.set_value("station_from", "");
            return;
        }

        frm.set_value(
            "station_from",
            addresses[0].custom_citytown || ""
        );
    });
}


function set_station_to_customer(frm) {
    if (!frm.doc.consignee) {
        frm.set_value("station_to", "");
        return;
    }

    frappe.db.get_value(
        "Customer",
        frm.doc.consignee,
        "customer_primary_address"
    ).then(r => {
        const address = r.message?.customer_primary_address;
        if (!address) return;

        frappe.db.get_value(
            "Address",
            address,
            "custom_citytown"
        ).then(addr => {
            if (addr.message?.custom_citytown) {
                frm.set_value(
                    "station_to",
                    addr.message.custom_citytown
                );
            }
        });
    });
}

frappe.ui.form.on("Outgoing Logistics", {

    before_save: function (frm) {
        const rows = frm.doc.sales_invoice_no || [];

        const has_sales_invoice = rows.some(row => row.sales_invoice);

        if (!has_sales_invoice) {
            frappe.throw(__(
                "At least one Sales Invoice is required to create Outgoing logistics."
            ));
        }
    }
});

frappe.ui.form.on("Outgoing Logistics", {
    refresh(frm) {
        // Disable rename action
        frm.disable_rename = true;

        // Remove pencil icon
        $(".page-title .editable-title").css("pointer-events", "none");
    }
});