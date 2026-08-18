frappe.ui.form.on("User", {
    validate(frm) {
        let mobile = (frm.doc.mobile_no || "").replace(/\D/g, "");

        if (mobile && mobile.length !== 10) {
            frappe.msgprint({
                title: "Invalid Mobile Number",
                message: "Mobile Number must be exactly 10 digits.",
                indicator: "red"
            });

            frappe.validated = false;
            return;
        }

        frm.set_value("mobile_no", mobile);
    },
    refresh(frm) {
        hide_restricted_roles(frm);
    }
});

function hide_restricted_roles(frm) {
    if (!frm.doc.name || frm.doc.__islocal) {
        return;
    }

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_hidden_roles_for_user",
        args: {
            user: frm.doc.name
        },
        callback(r) {
            const hidden_roles = r.message || [];

            if (!hidden_roles.length) {
                return;
            }

            hide_role_checkboxes(frm, hidden_roles);
        }
    });
}

function hide_role_checkboxes(frm, hidden_roles) {
    const roles_wrapper = frm.fields_dict.roles_html?.wrapper;

    if (!roles_wrapper) {
        return;
    }

    $(roles_wrapper).find(".checkbox").each(function () {
        const checkbox = $(this);
        const label = checkbox.text().trim();

        if (hidden_roles.includes(label)) {
            checkbox.hide();
        }
    });
}