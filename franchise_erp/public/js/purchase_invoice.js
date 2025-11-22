frappe.ui.form.on('Purchase Invoice', {
    before_submit: function(frm) {
        const current_user = frappe.session.user;
        const is_return = frm.doc.is_return;
        const owner = frm.doc.owner;

        // Normal PI: only owner can submit
        if (!is_return && current_user !== owner) {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Return PI: franchise user cannot submit return PI
        if (is_return && current_user === owner) {
            frappe.msgprint("User cannot submit Return Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Supplier users can submit franchise return PI
        // No action needed here; allowed
    }
});


