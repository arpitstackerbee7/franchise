
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
