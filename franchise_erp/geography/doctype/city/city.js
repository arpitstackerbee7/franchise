// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

frappe.ui.form.on("City", {
	refresh(frm) {

	},
    country(frm) {
        frm.set_value("state", null);

        frm.set_query("state", function () {
            return {
                filters: {
                    country: frm.doc.country
                }
            };
        });
    },
});
