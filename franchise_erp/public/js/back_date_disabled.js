// // DocType: Sales Invoice
// frappe.ui.form.on('Sales Invoice', {
//     // Trigger on load and validate
//     onload: function(frm) {
//         disable_back_date(frm);
//     },
//     validate: function(frm) {
//         disable_back_date(frm);
//     },
//     posting_date: function(frm) {
//         disable_back_date(frm);
//     }
// });

// // DocType: Purchase Invoice
// frappe.ui.form.on('Purchase Invoice', {
//     onload: function(frm) {
//         disable_back_date(frm);
//     },
//     validate: function(frm) {
//         disable_back_date(frm);
//     },
//     posting_date: function(frm) {
//         disable_back_date(frm);
//     }
// });


// // Common function
// function disable_back_date(frm) {
//     const today = frappe.datetime.get_today(); // current date YYYY-MM-DD

//     if (frm.doc.posting_date && frm.doc.posting_date < today) {
//         frappe.msgprint(__('Back-dating is not allowed. Posting Date set to today.'));
//         frm.set_value('posting_date', today); // auto reset to today
//     }
// }
// frappe.ui.form.on(['Sales Invoice', 'Purchase Invoice'], {
//     before_submit(frm) {

//         let posting_date = frm.doc.posting_date;
//         let today = frappe.datetime.get_today();

//         // Convert to Date objects
//         posting_date = new Date(posting_date);
//         today = new Date(today);

//         if (posting_date < today) {
//             frappe.throw("Back-dated entries are not allowed.");
//         }
//     }
// });
frappe.ui.form.on(['Sales Invoice', 'Purchase Invoice'], {
    posting_date(frm) {
        validate_back_date(frm);
    }
});

function validate_back_date(frm) {
    let posting_date = frm.doc.posting_date;
    let today = frappe.datetime.get_today();

    let d1 = new Date(posting_date);
    let d2 = new Date(today);

    if (d1 < d2) {
        frappe.msgprint({
            title: "Not Allowed",
            message: "Back-dated date not allowed.",
            indicator: "red"
        });

        // Reset to today
        frm.set_value("posting_date", today);
    }
}
