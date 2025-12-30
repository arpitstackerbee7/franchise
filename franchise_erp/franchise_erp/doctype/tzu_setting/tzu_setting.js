// Copyright (c) 2025, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("TZU Setting", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("TZU Setting", {
    validate(frm) {
        let serial_uoms = (frm.doc.serial_no_uom || []).map(r => r.uom);
        let batch_uoms = (frm.doc.batch_uom || []).map(r => r.uom);

        let common = serial_uoms.filter(u => batch_uoms.includes(u));

        if (common.length) {
            frappe.throw(
                `Same UOM(s) cannot be selected in both Serial No UOM and Batch UOM.<br><br>
                Conflicting UOM(s): ${common.join(", ")}`
            );
        }
    }
});



