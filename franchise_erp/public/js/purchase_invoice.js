frappe.ui.form.on("Purchase Invoice", {
    async before_submit(frm) {

        // Fetch role profiles for current logged-in user
        const result = await frappe.call({
            method: "franchise_erp.custom.customs.get_user_role_profiles",
            args: { user: frappe.session.user }
        });

        const profile_names = result.message || [];

        console.log("User Role Profiles:", profile_names);

        const has_franchise_profile = profile_names.includes("Franchise Role");
        const is_return_invoice = frm.doc.is_return === 1;

        // Franchise user cannot submit return PI
        if (has_franchise_profile && is_return_invoice) {
            frappe.msgprint("Franchise user cannot submit Return Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // Supplier (no Franchise Role) cannot submit normal PI
        if (!has_franchise_profile && !is_return_invoice) {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }
    }
});
