frappe.ui.form.on('Sales Order', {
     customer(frm) {
        if (!frm.doc.customer) return;

        // wait for ERPNext to populate sales_team
        setTimeout(() => {
            (frm.doc.sales_team || []).forEach(row => {
                set_incentive_from_sales_person(frm, row);
            });
        }, 500);
    },

    refresh(frm) {
            if (frm.doc.status === "On Hold" && frappe.session.user === "Administrator") {
                frm.add_custom_button("Update Item Price", function () {
                    open_price_update_dialog(frm);
                });
            }
            // Remove default Resume button for non-admin users
            if (frm.doc.status === "On Hold" && frappe.session.user !== "Administrator") {
                frm.remove_custom_button("Resume", "Status");
            }
    
            // Only Administrator can see Resume
            if (frm.doc.status === "On Hold" && frappe.session.user === "Administrator") {
                frm.add_custom_button(
                    __("Resume"),
                    function () {
                        frm.cscript.update_status("Resume", "Draft");
                    },
                    __("Status")
                );
            }
        
        // handles reload / back navigation
        (frm.doc.sales_team || []).forEach(row => {
            if (!row.incentives) {
                set_incentive_from_sales_person(frm, row);
            }
        });
    },
    custom_scan_product_bundle(frm) {
        if (!frm.doc.custom_scan_product_bundle) return;

        const bundle_serial = frm.doc.custom_scan_product_bundle.trim();

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Product Bundle",
                filters: { custom_bundle_serial_no: bundle_serial },
                fieldname: ["new_item_code"]
            },
            callback(r) {
                if (!r.message?.new_item_code) {
                    frappe.msgprint(__('No Item found for scanned bundle serial'));
                    frm.set_value('custom_scan_product_bundle', '');
                    return;
                }

                let row = frm.doc.items.find(d => !d.item_code) || frm.add_child('items');

                frappe.model.set_value(row.doctype, row.name, 'item_code', r.message.new_item_code);
                frappe.model.set_value(row.doctype, row.name, 'qty', row.qty || 1);

                frm.refresh_field('items');
                frm.set_value('custom_scan_product_bundle', '');
            }
        });
    },
    scan_barcode: function(frm) {

        let barcode = frm.doc.scan_barcode;

        if (!barcode) return;

        frappe.call({
            method: "franchise_erp.custom.sales_order.validate_scanned_serial",
            args: {
                serial_no: barcode,
                customer: frm.doc.customer
            },
            callback: function(r) {

                if (!r.message) return;

                // Already invoiced
                if (r.message.used) {

    frappe.msgprint({
        title: __("Serial Already Used"),
        indicator: "red",
        message: `
            <div style="line-height:1.8">
                <b>Scanned Serial No:</b> ${barcode}<br>
                <b>Item Code:</b> ${r.message.item_code}<br>
                <b>Sales Invoice:</b> ${r.message.invoice}<br>
                <b>Customer:</b> ${r.message.customer}<br>
                <b>Status:</b> ${r.message.status}<br><br>

                <span style="color:#d9534f;">
                    This serial has already been used in a Sales Invoice and cannot be scanned again.
                </span>

                <br><br>

                <b>Other Available Active Serials:</b><br>
                ${
                    r.message.active_serials.length
                        ? r.message.active_serials.join("<br>")
                        : "No other active serials available."
                }
            </div>
        `
    });

    frm.set_value("scan_barcode", "");

    // Remove row if ERPNext already added it
    setTimeout(() => {
        let rows = frm.doc.items || [];

        rows.forEach(row => {
            if (
                row.serial_no === barcode ||
                row.serial_and_batch_bundle === barcode
            ) {
                frappe.model.clear_doc(row.doctype, row.name);
            }
        });

        frm.refresh_field("items");
    }, 300);

    return;
}

               // Active serial
               let activeSerialHtml = "";

                if (r.message.active_serials && r.message.active_serials.length > 0) {
                    activeSerialHtml = `
                        <b>Other Available Active Serials:</b><br>
                        ${r.message.active_serials.join("<br>")}
                    `;
                } else {
                    activeSerialHtml = `
                        <b>No other active serials are currently available for this item.</b>
                    `;
                }

                frappe.msgprint({
                    title: __("Serial Available"),
                    indicator: "green",
                    message: `
                        <div style="line-height:1.8">
                            <b>Scanned Serial No:</b> ${barcode}<br>
                            <b>Item Code:</b> ${r.message.item_code}<br><br>

                            <span style="color:green;">
                                This serial has not been invoiced for the selected customer and can be added to this Sales Order.
                            </span>

                            <br><br>

                            ${activeSerialHtml}
                        </div>
                    `
                });
            }
        });
    }
});



function set_incentive_from_sales_person(frm, row) {
    if (!row.sales_person) return;

    frappe.db.get_value(
        "Sales Person",
        row.sales_person,
        "custom_commission_amount"
    ).then(r => {
        if (r && r.message && r.message.custom_commission_amount != null) {
            frappe.model.set_value(
                row.doctype,
                row.name,
                "incentives",
                r.message.custom_commission_amount
            );
        }
    });
}


frappe.ui.form.on("Sales Team", {
    sales_person(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        set_incentive_from_sales_person(frm, row);
    }
});









frappe.ui.form.on("Sales Order Item", {
    rate(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let price_list = frm.doc.selling_price_list;

        if (!["MRP", "RSP"].includes(price_list)) return;

        frappe.call({
            method: "franchise_erp.api.get_item_price",
            args: {
                item_code: row.item_code,
                price_list: price_list
            },
            callback(r) {
                if (!r.message) return;

                let system_rate = r.message.rate;
                let so_rate = row.rate;

                if (system_rate != so_rate) {
                    frappe.confirm(
                        `
                        <b>Price Mismatch Found</b><br><br>
                        Item: ${row.item_code}<br>
                        System Price: ${system_rate}<br>
                        Sales Order Price: ${so_rate}<br><br>
                        Do you want to update price from Administrator?
                        `,
                        // YES
                        function () {
                            frm.set_value("status", "On Hold");
                            frappe.msgprint(
                                "Sales Order moved to Hold. Please ask Administrator to update the price."
                            );
                        },
                        // NO
                        function () {
                            frappe.msgprint(
                                "Sales Order will continue with entered price."
                            );
                        }
                    );
                }
            }
        });
    }
});




function open_price_update_dialog(frm) {
    let row = frm.doc.items[0];   // simple case: first item
    let price_list = frm.doc.selling_price_list;

    let d = new frappe.ui.Dialog({
        title: "Update Item Price & Release SO",
        fields: [
            {
                label: "Rate",
                fieldname: "rate",
                fieldtype: "Float",
                reqd: 1,
                default: row.rate
            },
            {
                label: "Valid From",
                fieldname: "valid_from",
                fieldtype: "Date",
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: "Valid Upto",
                fieldname: "valid_upto",
                fieldtype: "Date"
            }
        ],
        primary_action_label: "Update Price",
        primary_action(values) {
            frappe.call({
                method: "franchise_erp.api.update_price_and_release_so",
                args: {
                    so_name: frm.doc.name,
                    item_code: row.item_code,
                    price_list: price_list,
                    rate: values.rate,
                    valid_from: values.valid_from,
                    valid_upto: values.valid_upto
                },
                callback() {
                    frappe.msgprint("Price updated successfully. Sales Order released from Hold.");
                    frm.reload_doc();
                    d.hide();
                }
            });
        }
    });

    d.show();
}
