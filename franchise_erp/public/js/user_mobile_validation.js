frappe.ui.form.on("User", {
    validate(frm) {
        let mobile = (frm.doc.mobile_no || "").replace(/\D/g, "");

        if (mobile && mobile.length !== 10) {
            frappe.throw("Mobile Number must be exactly 10 digits.");
        }

        // Save clean number
        frm.set_value("mobile_no", mobile);
    }
});


