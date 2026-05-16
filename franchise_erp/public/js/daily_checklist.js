frappe.ui.form.on("Daily Checklist", {
    onload: function(frm) {

        // sirf new doc me auto fill
        if (!frm.is_new()) {
            return;
        }

        // Logged in user
        let current_user = frappe.session.user;

        // User ID
        frm.set_value("user_id", current_user);

        // Sales Promoter Name
        frm.set_value("name_of_the_sales_promoter", current_user);

        // User details fetch
        frappe.db.get_doc("User", current_user).then(user => {

            // Default Company
            if (user.company) {

                frm.set_value("sis_counter", user.company);

                // Company ka primary address
                frappe.call({
                    method: "frappe.contacts.doctype.address.address.get_default_address",
                    args: {
                        doctype: "Company",
                        name: user.company
                    },
                    callback: function(r) {

                        if (r.message) {

                            frappe.db.get_doc("Address", r.message)
                                .then(address => {

                                    let full_address = "";

                                    if (address.address_line1) {
                                        full_address += address.address_line1;
                                    }

                                    if (address.address_line2) {
                                        full_address += ", " + address.address_line2;
                                    }

                                    if (address.city) {
                                        full_address += ", " + address.city;
                                    }

                                    if (address.state) {
                                        full_address += ", " + address.state;
                                    }

                                    if (address.pincode) {
                                        full_address += " - " + address.pincode;
                                    }

                                    frm.set_value("location", full_address);
                                });
                        }
                    }
                });
            }
        });
    }
});