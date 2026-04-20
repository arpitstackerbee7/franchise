// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Gate Out", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Gate Out', {

    refresh(frm) {
        if (frm.doc.gate_out_box_barcode && frm.doc.gate_out_box_barcode.length) {

            frm.doc.gate_out_box_barcode.sort((a, b) => {
                return new Date(b.scan_date_time) - new Date(a.scan_date_time);
            });

            frm.refresh_field("gate_out_box_barcode");
        }
        setTimeout(() => {
            frm.fields_dict.scan_barcode.$input.focus();
        }, 500);
    },

    scan_barcode(frm) {

        let barcode = frm.doc.scan_barcode;
        if (!barcode) return;

        // ✅ DUPLICATE CHECK
        let already = (frm.doc.gate_out_box_barcode || [])
            .some(d => d.box_barcode === barcode);

        if (already) {
            frappe.msgprint("Already Scanned ❌");
            frm.set_value("scan_barcode", "");
            return;
        }

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Outgoing Logistics",
                filters: {
                    name: barcode
                },
                fields: ["name", "docstatus", "is_gate_out", "quantity"]
            },
            callback: function(r) {

                if (!r.message || r.message.length === 0) {
                    frappe.msgprint("Invalid Barcode");
                    frm.set_value("scan_barcode", "");
                    return;
                }

                let doc = r.message[0];

                if (doc.docstatus != 1) {
                    frappe.msgprint("Only Submitted Allowed");
                    frm.set_value("scan_barcode", "");
                    return;
                }

                if (doc.is_gate_out) {
                    frappe.msgprint("Already Gate Out ❌");
                    frm.set_value("scan_barcode", "");
                    return;
                }

                let row = frm.add_child("gate_out_box_barcode");

                row.box_barcode = barcode;
                row.barcode_qty = doc.quantity || 0;
                row.scan_date_time = frappe.datetime.now_datetime();

                // 👇 ADD THIS
                frm.doc.gate_out_box_barcode.unshift(frm.doc.gate_out_box_barcode.pop());

                frm.refresh_field("gate_out_box_barcode");

                frm.set_value("scan_barcode", "");
            }
        });
    }
});

//  method: "franchise_erp.franchise_erp.doctype.gate_out.gate_out.get_pending_outgoing_logistics",

// frappe.ui.form.on('Gate Out', {

//     refresh(frm) {

//         frm.add_custom_button("Get Pending Logistics", function () {

//             frappe.call({
//                 method: "franchise_erp.franchise_erp.doctype.gate_out.gate_out.get_pending_outgoing_logistics",
//                 callback: function (r) {

//                     let data = r.message || [];

//                     if (!data.length) {
//                         frappe.msgprint("No Pending Logistics");
//                         return;
//                     }

//                     let dialog = new frappe.ui.Dialog({
//                         title: "Pending Outgoing Logistics",
//                         size: "large",
//                         fields: [
//                             {
//                                 fieldname: "logistics_list",
//                                 fieldtype: "Table",
//                                 cannot_add_rows: true,
//                                 in_place_edit: false,
//                                 fields: [
//                                     {
//                                         fieldname: "name",
//                                         fieldtype: "Data",
//                                         label: "Outgoing Logistics",
//                                         in_list_view: 1,
//                                         read_only: 1
//                                     }
//                                 ]
//                             }
//                         ],
//                         primary_action_label: "Get Items",
//                         primary_action(values) {

//                             let selected = dialog.selected_rows || [];

//                             if (!selected.length) {
//                                 frappe.msgprint("Select at least one");
//                                 return;
//                             }

//                             selected.forEach(name => {
//                                 let row = frm.add_child("gate_out_box_barcode");

//                                 row.box_barcode = name;
//                                 row.barcode_qty = 1;
//                                 row.scan_date_time = frappe.datetime.now_datetime();
//                             });

//                             frm.refresh_field("gate_out_box_barcode");

//                             dialog.hide();
//                         }
//                     });

//                     // add data
//                     dialog.fields_dict.logistics_list.df.data = data.map(d => ({
//                         name: d.name
//                     }));

//                     dialog.fields_dict.logistics_list.grid.refresh();
//                     dialog.show();

//                     // ✅ selection logic (row click)
//                     dialog.selected_rows = [];

//                     setTimeout(() => {

//                         dialog.$wrapper.find('.grid-row').on('click', function () {

//                             let row = $(this);
//                             let name = row.attr("data-name");

//                             if (row.hasClass("selected-row")) {
//                                 row.removeClass("selected-row");
//                                 dialog.selected_rows = dialog.selected_rows.filter(n => n !== name);
//                             } else {
//                                 row.addClass("selected-row");
//                                 dialog.selected_rows.push(name);
//                             }

//                         });

//                         // ✅ highlight style
//                         dialog.$wrapper.append(`
//                             <style>
//                                 .selected-row {
//                                     background-color: #d1f7c4 !important;
//                                 }
//                             </style>
//                         `);

//                         // ✅ scroll
//                         dialog.$wrapper.find('.grid-body').css({
//                             'max-height': '300px',
//                             'overflow-y': 'auto'
//                         });

//                     }, 300);

//                 }
//             });

//         });

//     }
// });