// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("SIS Debit Note Log", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("SIS Debit Note Log", {
    company: function (frm) {
        console.log("JS Loaded");
        if (!frm.doc.company) return;

        // Clear old value
        frm.set_value("sis_debit_note_creation_period", "");
        frm.set_value("from_date", "");
        frm.set_value("to_date", "");

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "SIS Configuration",
                filters: { company: frm.doc.company },
            },
            callback(r) {
                if (r.message) {
                    let config = r.message;

                    // SET FIELD VALUE
                    frm.set_value(
                        "sis_debit_note_creation_period",
                        config.sis_debit_note_creation_period
                    );
                    if (config.sis_debit_note_creation_period === "Date Range") {
                        frm.set_value("from_date", config.from_date);
                        frm.set_value("to_date", config.to_date);
                    }
                } else {
                    frappe.msgprint("No SIS Configuration found for this company.");
                }
            },
        });
    },


    

    refresh(frm) {
        // First: auto fetch config when company is selected
        if (frm.doc.company) {
            frm.trigger("company");
        }
 console.log("c:",frm.doc.company);
        // Remove button every refresh
        frm.page.remove_inner_button("Create Debit Note");

        if (frm.doc.company) {
            frm.add_custom_button("Fetch Invoices", function () {
                frappe.call({
                    method: "franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log.fetch_invoices",
                    args: {
                        company: frm.doc.company
                    },
                    callback(r) {
                        if (r.message && r.message.invoice_list) {
                            frm.invoice_list = r.message.invoice_list;

                            show_invoice_dialog(frm);

                            // ADD BUTTON AFTER FETCH
                            // show_create_button(frm);

                            frappe.msgprint(r.message.message);
                        }
                    },
                });
                
            });
        }
    },
});


function fetch_and_update() {
    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log.fetch_invoices",
        args: {
            company: frm.doc.company,
            from_date: from_date_ctrl.get_value(),
            to_date: to_date_ctrl.get_value()
        },
        freeze: true,
        callback(r) {
            if (r.message) {
                all_items = r.message.invoice_list || [];
                page = 1;
                update_table();
            }
        }
    });
}

function show_invoice_dialog(frm) {
    let all_items = [];
    let current_filtered_data = [];
    let page = 1;
    let page_size = 10;

    let d = new frappe.ui.Dialog({
        title: "Invoice Items",
        size: "extra-large",
        fields: [
            { fieldname: "header_html", fieldtype: "HTML" },
            { fieldname: "filter_row", fieldtype: "HTML" },
            { fieldname: "items_html", fieldtype: "HTML" },
            { fieldname: "pagination_html", fieldtype: "HTML" }
        ]
    });

    d.show();

    // -----------------------
    // Modal width
    // -----------------------
    d.$wrapper.find('.modal-dialog').css({
        "max-width": "95%",
        "width": "95%"
    });

    // -----------------------
    // Header buttons
    // -----------------------
    d.fields_dict.header_html.$wrapper.html(`
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <div>
                <button class="btn btn-secondary btn-sm" id="print_table_btn">🖨 Print</button>
                <button class="btn btn-success btn-sm" id="export_table_btn">⬇ Export CSV</button>
            </div>
            <button class="btn btn-primary" id="create_debit_note_btn_dialog">
                Create Debit Note
            </button>
        </div>
    `);

    // -----------------------
    // Create Debit Note
    // -----------------------
    d.$wrapper.on("click", "#create_debit_note_btn_dialog", function () {
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log.create_debit_note",
            args: {
                company: frm.doc.company,
                period_type: frm.doc.sis_debit_note_creation_period,
                invoices: current_filtered_data
            },
            callback(r) {
                if (r.message?.journal_entry) {
                    frappe.set_route("Form", "Journal Entry", r.message.journal_entry);
                } else if (r.message) {
                    frappe.msgprint(r.message);
                }
            }
        });
    });

    // -----------------------
    // Filter Row
    // -----------------------
    d.fields_dict.filter_row.$wrapper.html(`
        <div class="invoice-filter-row">
            <div class="from-date"></div>
            <div class="to-date"></div>
            <div class="discount"></div>
            <div class="search"></div>
        </div>
    `);

    let from_date_ctrl = frappe.ui.form.make_control({
        parent: d.$wrapper.find(".from-date"),
        df: {
            fieldtype: "Date",
            label: "From Date",
            onchange() {
                page = 1;
                fetch_and_update();
            }
        },
        render_input: true
    });

    let to_date_ctrl = frappe.ui.form.make_control({
        parent: d.$wrapper.find(".to-date"),
        df: {
            fieldtype: "Date",
            label: "To Date",
            onchange() {
                page = 1;
                fetch_and_update();
            }
        },
        render_input: true
    });

    let discount_ctrl = frappe.ui.form.make_control({
        parent: d.$wrapper.find(".discount"),
        df: {
            fieldtype: "Select",
            label: "Discount %",
            options: ["All", "<= 10%", "> 10%"],
            default: "All",
            onchange() {
                page = 1;
                update_table();
            }
        },
        render_input: true
    });

    let search_ctrl = frappe.ui.form.make_control({
        parent: d.$wrapper.find(".search"),
        df: {
            fieldtype: "Data",
            label: "Search",
            onchange() {
                page = 1;
                update_table();
            }
        },
        render_input: true
    });

    from_date_ctrl.set_value(frappe.datetime.get_today());
    to_date_ctrl.set_value(frappe.datetime.get_today());

    // -----------------------
    // Fetch data
    // -----------------------
    function fetch_and_update() {
        frappe.call({
            method: "franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log.fetch_invoices",
            args: {
                company: frm.doc.company,
                from_date: from_date_ctrl.get_value(),
                to_date: to_date_ctrl.get_value()
            },
            freeze: true,
            callback(r) {
                all_items = r.message?.invoice_list || [];
                update_table();
            }
        });
    }

    // -----------------------
    // Update table
    // -----------------------
    function update_table() {
        let filter_value = discount_ctrl.get_value();
        let search_txt = (search_ctrl.get_value() || "").toLowerCase();

        let filtered = [...all_items];

        if (filter_value === "<= 10%") {
            filtered = filtered.filter(r => flt(r.discount_percentage) <= 10);
        } else if (filter_value === "> 10%") {
            filtered = filtered.filter(r => flt(r.discount_percentage) > 10);
        }

        filtered = filtered.filter(r =>
            (r.item_name || "").toLowerCase().includes(search_txt) ||
            (r.customer || "").toLowerCase().includes(search_txt) ||
            (r.name || "").toLowerCase().includes(search_txt)
        );

        current_filtered_data = filtered;

        let total_pages = Math.ceil(filtered.length / page_size) || 1;
        page = Math.min(page, total_pages);

        let start = (page - 1) * page_size;
        let rows = filtered.slice(start, start + page_size);

        let html = `
        <div style="max-height:420px; overflow:auto; border:1px solid #ddd;">
        <table class="table table-bordered">
        <thead>
            <tr>
                <th>#</th><th>Invoice</th><th>Date</th><th>Customer</th>
                <th>Item</th><th>Qty</th><th>MRP</th><th>Total</th>
                <th>Discount%</th><th>Realized Sale</th><th>Output GST%</th><th>Output GST Value</th><th>Taxable Value</th><th>Margin%</th>
                       <th>Margin Value</th>
                       <th>INV Base Value</th>
                       <th>Input GST Value</th>
                       <th>Collectable</th>
                       <th>CD/DN</th>
            </tr>
        </thead><tbody>`;

        if (!rows.length) {
            html += `<tr><td colspan="10" class="text-center">No Records Found</td></tr>`;
        } else {
            rows.forEach((r, i) => {
                html += `
                <tr>
                    <td>${start + i + 1}</td>
                    <td>${r.name}</td>
                    <td>${r.posting_date}</td>
                    <td>${r.customer}</td>
                    <td>${r.item_name}</td>
                    <td>${r.qty}</td>
                    <td>${r.price_list_rate}</td>
                    <td>${(r.price_list_rate * r.qty).toFixed(2)}</td> 
                    <td>${r.discount_percentage}</td> 
                    <td>${r.net_amount}</td> 
                    <td>${r.gst_percent}</td> 
                    <td>${r.gst_amount}</td> 
                    <td>${(r.net_sale_value).toFixed(2)}</td> 
                    <td>${r.margin_percent}</td>
                       <td>${r.margin_amount}</td> 
                       <td>${r.inv_base_value}</td> 
                       <td>${r.in_put_gst_value}</td> 
                       <td>${(r.invoice_value).toFixed(2)}</td> 
                       <td>${(r.debit_note).toFixed(2)}</td>
                </tr>`;
            });
        }

        html += `</tbody></table></div>`;
        d.get_field("items_html").$wrapper.html(html);

        d.get_field("pagination_html").$wrapper.html(`
            <div style="display:flex; justify-content:space-between; margin-top:10px;">
                <b>Total Records: ${filtered.length}</b>
                <div>
                    <button class="btn btn-sm btn-primary prev" ${page === 1 ? "disabled" : ""}>Prev</button>
                    Page ${page} of ${total_pages}
                    <button class="btn btn-sm btn-primary next" ${page === total_pages ? "disabled" : ""}>Next</button>
                </div>
            </div>
        `);

        d.$wrapper.find(".prev").on("click", () => { page--; update_table(); });
        d.$wrapper.find(".next").on("click", () => { page++; update_table(); });
    }

    // -----------------------
    // PRINT
    // -----------------------
    d.$wrapper.on("click", "#print_table_btn", function () {
        if (!current_filtered_data.length) {
            frappe.msgprint("No data to print");
            return;
        }

        let rows = current_filtered_data.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${r.name}</td>
                    <td>${r.posting_date}</td>
                    <td>${r.customer}</td>
                    <td>${r.item_name}</td>
                    <td>${r.qty}</td>
                    <td>${r.price_list_rate}</td>
                    <td>${(r.price_list_rate * r.qty).toFixed(2)}</td> 
                    <td>${r.discount_percentage}</td> 
                    <td>${r.net_amount}</td> 
                    <td>${r.gst_percent}</td> 
                    <td>${r.gst_amount}</td> 
                    <td>${(r.net_sale_value).toFixed(2)}</td> 
                    <td>${r.margin_percent}</td>
                       <td>${r.margin_amount}</td> 
                       <td>${r.inv_base_value}</td> 
                       <td>${r.in_put_gst_value}</td> 
                       <td>${(r.invoice_value).toFixed(2)}</td> 
                       <td>${(r.debit_note).toFixed(2)}</td>
            </tr>
        `).join("");

        let win = window.open("", "_blank");
        win.document.write(`
            <html><head>
            <style>
                table{width:100%;border-collapse:collapse}
                th,td{border:1px solid #000;padding:6px;font-size:12px}
            </style>
            </head><body>
            <h3>Invoice Report</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th> <th>Invoice</th><th>Date</th><th>Customer</th>
                <th>Item</th><th>Qty</th><th>MRP</th><th>Total</th>
                <th>Discount%</th><th>Realized Sale</th><th>Output GST%</th><th>Output GST Value</th><th>Taxable Value</th><th>Margin%</th>
                       <th>Margin Value</th>
                       <th>INV Base Value</th>
                       <th>Input GST Value</th>
                       <th>Collectable</th>
                       <th>CD/DN</th>

                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
            </body></html>
        `);
        win.document.close();
        win.print();
    });

    // -----------------------
    // EXPORT CSV
    // -----------------------
    d.$wrapper.on("click", "#export_table_btn", function () {
        if (!current_filtered_data.length) {
            frappe.msgprint("No data to export");
            return;
        }

        let csv = "Invoice,Date,Customer,Item,Qty,MRP,Total,Discount%,Realized Sale,Output GST%,Output GST Value,Taxable Value,Margin%,Margin Value,INV Base Value,Input GST Value,Collectable,CD/DN\n";

        current_filtered_data.forEach(r => {
            csv += [
                r.name, r.posting_date, r.customer, r.item_code,
                r.qty, r.price_list_rate,(r.price_list_rate * r.qty).toFixed(2),r.discount_percentage, r.net_amount, r.gst_percent, r.gst_amount,
                (r.net_sale_value).toFixed(2),r.margin_percent,r.margin_amount,  r.inv_base_value,r.in_put_gst_value, (r.invoice_value).toFixed(2),     (r.debit_note).toFixed(2),
            ].join(",") + "\n";
        });

        let blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "Invoice_Report.csv";
        a.click();
        URL.revokeObjectURL(url);
    });

    // -----------------------
    // CSS
    // -----------------------
    d.$wrapper.append(`
        <style>
            .invoice-filter-row{
                display:grid;
                grid-template-columns:1fr 1fr 1fr 2fr;
                gap:12px;
                margin-bottom:15px;
            }
        </style>
    `);

    fetch_and_update();
}



// function show_invoice_dialog(frm) {
//     let all_items = frm.invoice_list || [];
//     let page = 1;
//     let page_size = 10;

//     // let d = new frappe.ui.Dialog({
//     //     title: "Invoice Items",
//     //     size: "extra-large",
//     //     fields: [
//     //         { fieldname: "header_html", fieldtype: "HTML" },
//     //         {
//     //             fieldname: "discount_filter",
//     //             label: "Filter by Discount %",
//     //             fieldtype: "Select",
//     //             options: ["All", "<= 10%", "> 10%"],
//     //             default: "All",
//     //             onchange: () => { page = 1; update_table(); }
//     //         },
//     //         {
//     //             fieldname: "search_box",
//     //             fieldtype: "Data",
//     //             label: "Search Item / Customer / Invoice",
//     //             onchange: () => { page = 1; update_table(); }
//     //         },
//     //         { fieldname: "items_html", fieldtype: "HTML" },
//     //         { fieldname: "pagination_html", fieldtype: "HTML" }
//     //     ]
//     // });
//         let d = new frappe.ui.Dialog({
//         title: "Invoice Items",
//         size: "extra-large",
//         fields: [
//             { fieldname: "header_html", fieldtype: "HTML" },

//             {
//                 fieldname: "from_date",
//                 label: "From Date",
//                 fieldtype: "Date",
//                 onchange: () => {
//                     page = 1;
//                     fetch_and_update();
//                 }
//             },
//             {
//                 fieldname: "to_date",
//                 label: "To Date",
//                 fieldtype: "Date",
//                 onchange: () => {
//                     page = 1;
//                     fetch_and_update();
//                 }
//             },

//             {
//                 fieldname: "discount_filter",
//                 label: "Filter by Discount %",
//                 fieldtype: "Select",
//                 options: ["All", "<= 10%", "> 10%"],
//                 default: "All",
//                 onchange: () => { page = 1; update_table(); }
//             },
//             {
//                 fieldname: "search_box",
//                 fieldtype: "Data",
//                 label: "Search Item / Customer / Invoice",
//                 onchange: () => { page = 1; update_table(); }
//             },
//             { fieldname: "items_html", fieldtype: "HTML" },
//             { fieldname: "pagination_html", fieldtype: "HTML" }
//         ]
//     });

//     // Show dialog first
//     d.show();

//     // -----------------------
//     // 1. Increase modal width
//     // -----------------------
//     d.$wrapper.find('.modal-dialog').css({
//         "max-width": "95%",
//         "width": "95%"
//     });

//     // -----------------------
//     // 2. Override max-width of page sections
//     // -----------------------
//     let page_div = d.$wrapper.find('div.modal-body.ui-front .form-page > div > div');
//     if (page_div.length) {
//         page_div.css('max-width', '1350px');
//     }
//     // -----------------------
//     // 3. Add Create button in header
//     // -----------------------
//     d.fields_dict.header_html.$wrapper.html(`
//         <div style="display:flex; justify-content:flex-end; margin-bottom:10px;">
//             <button class="btn btn-primary" id="create_debit_note_btn_dialog">
//                 Create Debit Note
//             </button>
//         </div>
//     `);

//     d.$wrapper.on("click", "#create_debit_note_btn_dialog", function () {
//         frappe.call({
//             method: "franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log.create_debit_note",
//             args: {
//                 company: frm.doc.company,
//                 period_type: frm.doc.sis_debit_note_creation_period,
//                 invoices: all_items          // <--- FIXED
//             },
//             callback(r) {
//                 if (r.message?.journal_entry) {
//                     frappe.set_route("Form", "Journal Entry", r.message.journal_entry);
//                 } else if (r.message) {
//                     frappe.msgprint(r.message);
//                 }
//             }
//         });
//     });



//     function update_table() {
//         let filter_value = d.get_value("discount_filter");
//         let search_txt = (d.get_value("search_box") || "").toLowerCase();

//         let filtered = [...all_items];

//         if (filter_value === "<= 10%") {
//             filtered = filtered.filter(r => flt(r.discount_percentage) <= 10);
//         } else if (filter_value === "> 10%") {
//             filtered = filtered.filter(r => flt(r.discount_percentage) > 10);
//         }

//         filtered = filtered.filter(r =>
//             (r.item_code || "").toLowerCase().includes(search_txt) ||
//             (r.item_name || "").toLowerCase().includes(search_txt) ||
//             (r.customer || "").toLowerCase().includes(search_txt) ||
//             (r.name || "").toLowerCase().includes(search_txt)
//         );

//         let total_pages = Math.ceil(filtered.length / page_size) || 1;
//         if (page > total_pages) page = total_pages;
//         if (page < 1) page = 1;

//         let start = (page - 1) * page_size;
//         let paginated = filtered.slice(start, start + page_size);

//         // --- TABLE HTML ---
//         let table = `
//             <div style="
//                 max-height: 420px;
//                 overflow-y: auto;
//                 overflow-x: auto;
//                 border: 1px solid #ddd;
//             ">
//             <table class="table table-bordered" style="margin-bottom:0;">
//                 <thead>
//                     <tr>
//                         <th>S.No</th>
//                         <th>Invoice</th>
//                         <th>Date</th>
//                         <th>Customer</th>
//                         <th>Item Code</th>
//                         <th>Item Name</th>
//                         <th>Qty</th>
//                         <th>MRP</th>
//                         <th>Total</th>
//                         <th>Discount</th>
//                         <th>Realized Sale</th>
//                         <th>Output GST%</th>
//                         <th>Output GST Value</th>
//                         <th>Taxable Value</th>
//                         <th>Margin%</th>
//                         <th>Margin Value</th>
//                         <th>INV Base Value</th>
                        
//                         <th>Input GST Value</th>
//                         <th>Collectable</th>
//                         <th>CD/DN</th>
                        

//                     </tr>
//                 </thead>
//                 <tbody>
            
//         `;
        

//         if (paginated.length === 0) {
//             table += `<tr><td colspan="12" class="text-center">No Records Found</td></tr>`;
//         } else {
//             paginated.forEach((r, idx) => {
//                 const serial = start + idx + 1;
//                 table += `
//                     <tr>
//                         <td>${serial}</td>
//                         <td>${r.name}</td>
//                         <td>${r.posting_date} ${r.posting_time.split('.')[0]}</td>
//                         <td>${r.customer}</td>
//                         <td>${r.item_code}</td>
//                         <td>${r.item_name}</td>
//                         <td>${r.qty}</td>
//                         <td>${r.price_list_rate}</td> 
//                         <td>${(r.price_list_rate * r.qty).toFixed(2)}</td> <!-- Grand Total -->
//                         <td>${r.discount_percentage}</td> <!-- Discount -->
//                         <td>${r.net_amount}</td> <!-- Realized Sale -->
//                         <td>${r.gst_percent}</td> <!-- Output GST% -->
//                         <td>${r.gst_amount}</td> <!-- Output GST Value -->
//                         <td>${(r.net_sale_value).toFixed(2)}</td> <!-- Net Sale Value -->
//                         <td>${r.margin_percent}</td> <!-- Margin% -->
//                         <td>${r.margin_amount}</td> <!-- Margin Value -->
//                         <td>${r.inv_base_value}</td> <!-- INV Base Value -->
//                         <td>${r.in_put_gst_value}</td> <!-- Input GST Value -->
//                         <td>${(r.invoice_value).toFixed(2)}</td> <!-- Invoice Value -->
//                         <td>${(r.debit_note).toFixed(2)}</td>
//                     </tr>
//                 `;
//             });
//         }

//         table += `</tbody></table></div>`;

//         // Inject table
//         d.get_field("items_html").$wrapper.html(table);

//         // --- RECORD COUNT + PAGINATION BELOW TABLE ---
//         let footer = `
//             <div style="display:flex; justify-content:space-between; align-items:center; margin-top:15px;">
                
//                 <!-- LEFT: Total Records -->
//                 <div style="font-weight:bold;">
//                     Total Records: ${filtered.length}
//                 </div>

//                 <!-- RIGHT: Pagination -->
//                 <div>
//                     <button class="btn btn-sm btn-primary" id="prev_page" ${page === 1 ? "disabled" : ""}>Prev</button>
//                     <span style="margin:0 10px;">Page ${page} of ${total_pages}</span>
//                     <button class="btn btn-sm btn-primary" id="next_page" ${page === total_pages ? "disabled" : ""}>Next</button>
//                 </div>
//             </div>
//         `;

//         d.get_field("pagination_html").$wrapper.html(footer);

//         // --- Bind Events ---
//         d.$wrapper.find("#prev_page").off("click").on("click", () => {
//             if (page > 1) { page--; update_table(); }
//         });

//         d.$wrapper.find("#next_page").off("click").on("click", () => {
//             if (page < total_pages) { page++; update_table(); }
//         });
//     }

//     // d.show();

//     update_table();
// }




