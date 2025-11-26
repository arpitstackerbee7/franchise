frappe.ui.form.on("SIS Debit Note Log", {

    period(frm) {
        if (!frm.doc.period) return;

        let today = frappe.datetime.get_today();
        let year = today.slice(0, 4);
        let month = today.slice(5, 7);

        if (frm.doc.period === "1-15") {
            frm.set_value("from_date", `${year}-${month}-01`);
            frm.set_value("to_date", `${year}-${month}-15`);
        } else {
            frm.set_value("from_date", `${year}-${month}-16`);
            let end = frappe.datetime.get_month_end(today);
            frm.set_value("to_date", end);
        }
    },

    refresh(frm) {

        // Always show Fetch button if required fields present
        if (frm.doc.company && frm.doc.from_date && frm.doc.to_date) {

            frm.add_custom_button("Fetch Invoices", function () {
                frappe.call({
                    method: "franchise_erp.custom.debit_note.fetch_invoices",
                    args: {
                        company: frm.doc.company,
                        from_date: frm.doc.from_date,
                        to_date: frm.doc.to_date
                    },
                    callback(r) {
                        if (r.message && r.message.invoice_list) {

                            frm.invoice_list = r.message.invoice_list;
                            frm.trigger("show_invoice_table");

                            if (r.message.invoice_list.length > 0) {
                                frm.trigger("show_create_button");
                            }

                            frappe.msgprint(r.message.message);
                        }
                    }
                });
            });
        }
    },

   show_invoice_table(frm) {
    frm.$wrapper.find(".invoice-table").remove();

    let html = "<h4 style='margin-top:20px;'>Eligible Discounted Items</h4>";
    html += `
        <table class='table table-bordered table-striped'>
        <tr>
            <th>Invoice</th>
            <th>Date</th>
            <th>Customer</th>
            <th>Item Code</th>
            <th>Item Name</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Total Amount</th>
            <th>Disc%</th>
            <th>Net Amount</th>
        </tr>
    `;

    frm.invoice_list.forEach(row => {
        html += `
            <tr>
                <td>${row.name}</td>
                <td>${row.posting_date}</td>
                <td>${row.customer}</td>
                <td>${row.item_code}</td>
                <td>${row.item_name}</td>
                <td>${row.qty}</td>
                <td>${row.price_list_rate}</td>
                <td>${row.total_amount}</td>
                <td>${row.discount_percentage}</td>
                <td>${row.net_amount}</td>
            </tr>
        `;
    });

    html += "</table>";
    frm.$wrapper.append(`<div class="invoice-table">${html}</div>`);
},


    
show_create_button(frm) {
    frm.page.remove_inner_button("Create Debit Note");

    frm.page.add_inner_button("Create Debit Note", function () {
        frappe.call({
            method: "franchise_erp.custom.debit_note.create_debit_note",
            args: {
                company: frm.doc.company,
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date
            },
            callback(r) {
                frappe.msgprint(r.message);

                if (r.message && r.message.journal_entry) {
                    frappe.set_route("Form", "Journal Entry", r.message.journal_entry);
                }
            }
        });
    });
}


});

