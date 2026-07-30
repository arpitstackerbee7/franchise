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
        validate_max_rows(
            frm,
            "individual_sales_representative_incentives",
            "Individual Sales Representative Incentives"
        );

        validate_max_rows(
            frm,
            "counter_store_level_performance",
            "Counter Store Level Performance"
        );
    }
});


frappe.ui.form.on("Individual Sales Representative Incentives", {
    individual_sales_representative_incentives_add(frm, cdt, cdn) {
        limit_child_table_rows(
            frm,
            cdt,
            cdn,
            "individual_sales_representative_incentives",
            "Individual Sales Representative Incentives"
        );
    }
});


frappe.ui.form.on("Counter Store Level Performance", {
    counter_store_level_performance_add(frm, cdt, cdn) {
        limit_child_table_rows(
            frm,
            cdt,
            cdn,
            "counter_store_level_performance",
            "Counter Store Level Performance"
        );
    }
});


function limit_child_table_rows(
    frm,
    cdt,
    cdn,
    fieldname,
    label
) {
    const rows = frm.doc[fieldname] || [];

    if (rows.length > 3) {
        frappe.model.delete_doc(cdt, cdn);

        frappe.msgprint(
            __("{0} can have a maximum of 3 rows.", [label])
        );

        frm.refresh_field(fieldname);
    }
}


function validate_max_rows(frm, fieldname, label) {
    const rows = frm.doc[fieldname] || [];

    if (rows.length > 3) {
        frappe.throw(
            __("{0} can have a maximum of 3 rows.", [label])
        );
    }
}



