// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Daily Checklist", {
    refresh(frm) {
        if (!frm.is_new()) return;

        let current_user = frappe.session.user;

        frm.set_value("user_id", current_user);

        frappe.db.get_value("Employee", {
            user_id: current_user
        }, "name").then(r => {
            if (r.message?.name) {
                frm.set_value("employee", r.message.name);
            }
        });

        frappe.db.get_doc("User", current_user).then(user => {
            if (user.company) {
                frm.set_value("sis_counter", user.company);

                frappe.call({
                    method: "frappe.contacts.doctype.address.address.get_default_address",
                    args: {
                        doctype: "Company",
                        name: user.company
                    },
                    callback(r) {
                        if (r.message) {
                            frappe.db.get_doc("Address", r.message).then(address => {
                                let full_address = [
                                    address.address_line1,
                                    address.address_line2,
                                    address.city,
                                    address.state
                                ].filter(Boolean).join(", ");

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