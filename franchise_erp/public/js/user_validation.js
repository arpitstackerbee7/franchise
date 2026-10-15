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

        apply_user_role_viewer_restrictions(frm);

    },

    module_profile(frm) {

        // Module Profile change hone ke baad
        // Module Def list render hone do
        setTimeout(() => {
            apply_user_role_viewer_restrictions(frm);
        }, 500);

    }

});


function apply_user_role_viewer_restrictions(frm) {

    if (!frm.doc.name || frm.doc.__islocal) {
        return;
    }

    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_hidden_roles_for_user",

        args: {
            user: frm.doc.name
        },

        callback(r) {

            const hidden_roles = r.message || [];

            if (hidden_roles.length) {
                hide_role_checkboxes(frm, hidden_roles);
            }

        }

    });


    frappe.call({

        method:
            "franchise_erp.franchise_erp.doctype.user_role_viewer.user_role_viewer.get_hidden_modules_for_user",

        args: {
            user: frm.doc.name
        },

        callback(r) {

            const hidden_modules = r.message || [];

            if (hidden_modules.length) {
                hide_module_definitions(frm, hidden_modules);
            }

        }

    });

}


// =========================================================
// HIDE RESTRICTED ROLES
// =========================================================

function hide_role_checkboxes(frm, hidden_roles) {

    const roles_wrapper = frm.fields_dict.roles_html?.wrapper;

    if (!roles_wrapper) {
        return;
    }

    $(roles_wrapper)
        .find(".checkbox")
        .each(function () {

            const checkbox = $(this);

            const label = checkbox
                .text()
                .trim();

            if (hidden_roles.includes(label)) {
                checkbox.hide();
            }

        });
}


// =========================================================
// HIDE RESTRICTED MODULE DEF
// =========================================================

function hide_module_definitions(frm, hidden_modules) {

    const page_wrapper = frm.page.wrapper;

    if (!page_wrapper) {
        return;
    }

    $(page_wrapper)
        .find(".checkbox")
        .each(function () {

            const checkbox = $(this);

            const label = checkbox
                .text()
                .trim();

            if (!label) {
                return;
            }

            if (hidden_modules.includes(label)) {

                checkbox.hide();

                // Parent container bhi hide karo
                checkbox.closest(".form-check").hide();

                checkbox.closest(".checkbox").hide();
            }

        });
}