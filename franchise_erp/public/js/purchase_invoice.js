frappe.ui.form.on('Purchase Invoice', {
    before_submit: function(frm) {
        const user_roles = frappe.user_roles; // current user roles
        const is_franchise = user_roles.includes('Franchise Role'); // adjust role name
        const is_return_invoice = frm.doc.is_return === 1;

        // Case 1: Franchise user cannot submit return PI
        if (is_franchise && is_return_invoice) {
            frappe.msgprint(__('Franchise cannot submit return Purchase Invoice'));
            frappe.validated = false;
            return;
        }

        // Case 2: Non-franchise (supplier) user cannot submit normal PI
        if (!is_franchise && !is_return_invoice) {
            frappe.msgprint(__('Supplier cannot submit normal Purchase Invoice'));
            frappe.validated = false;
            return;
        }

        // Case 3: Supplier (non-franchise) can submit return PI → allowed
    }
});

