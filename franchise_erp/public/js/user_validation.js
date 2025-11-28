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
    }
});
