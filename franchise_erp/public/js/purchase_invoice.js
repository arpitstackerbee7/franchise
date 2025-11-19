frappe.ui.form.on("Purchase Invoice", {
    async before_submit(frm) {

        let profile_names = [];

        try {
            const result = await frappe.call({
            method: "franchise_erp.custom.customs.get_user_role_profiles",
            args: { user: frappe.session.user }
        });

        const profile_names = result.message || [];

        } catch (error) {
            console.error("Error fetching user role profiles:", error);
            frappe.msgprint("Unable to verify user roles. Submission blocked.");
            frappe.validated = false;
            return;
        }

        console.log("User Role Profiles:", profile_names);

        const has_franchise_profile = profile_names.includes("Franchise Role");
        const is_return_invoice = frm.doc.is_return == 1;

        // 🚫 Franchise user → Cannot submit RETURN PI
        if (has_franchise_profile && is_return_invoice) {
            frappe.msgprint("Franchise user cannot submit Return Purchase Invoice");
            frappe.validated = false;
            return;
        }

        // 🚫 Supplier (no franchise role) → Cannot submit NORMAL PI
        if (!has_franchise_profile && !is_return_invoice) {
            frappe.msgprint("Supplier cannot submit Normal Purchase Invoice");
            frappe.validated = false;
            return;
        }
    }
});
