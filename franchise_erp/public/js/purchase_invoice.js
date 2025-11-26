frappe.ui.form.on('Purchase Invoice', {
    before_submit: function(frm) {
        const current_user = frappe.session.user;
        const is_return = frm.doc.is_return;
        const owner = frm.doc.owner;
console.log('cu:',current_user)
console.log('ir:',is_return)
console.log('o:',owner)
        // Allow Administrator always
        if (current_user === "Administrator") {
            return;
        }

        // Normal PI: owner (supplier) cannot submit
        if (is_return === 0 && current_user != owner) {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Return PI: supplier (owner) cannot submit
        if (is_return && current_user === owner) {
            frappe.msgprint("Supplier cannot submit Return Purchase Invoice");
            frappe.validated = false;
            return;
        }
    }
});
