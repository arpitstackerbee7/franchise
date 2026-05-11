frappe.ui.form.on("Serial No", {

    refresh(frm) {

        if (frm.doc.item_code && !frm.doc.custom_style) {

            frappe.db.get_value(
                "Item",
                frm.doc.item_code,
                "custom_barcode_code"
            ).then((r) => {

                if (r.message) {

                    frm.set_value(
                        "custom_style",
                        r.message.custom_barcode_code
                    );

                    frm.save();
                }
            });
        }
    },

    item_code(frm) {

        if (frm.doc.item_code) {

            frappe.db.get_value(
                "Item",
                frm.doc.item_code,
                "custom_barcode_code"
            ).then((r) => {

                if (r.message) {

                    frm.set_value(
                        "custom_style",
                        r.message.custom_barcode_code
                    );
                }
            });
        }
    }
});