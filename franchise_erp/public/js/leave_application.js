frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		console.log("=== Franchise ERP Leave JS Loaded ===");

		set_leave_type_filter(frm);
	},

	onload(frm) {
		set_leave_type_filter(frm);
	},

	employee(frm) {
		set_leave_type_filter(frm);

		// Clear leave type when employee changes
		frm.set_value("leave_type", "");
	},

	custom_employee_category(frm) {
		set_leave_type_filter(frm);

		// Clear leave type when category changes
		frm.set_value("leave_type", "");
	}
});

function set_leave_type_filter(frm) {
	frm.set_query("leave_type", function () {
		console.log(
			"Filtering Leave Types for Category:",
			frm.doc.custom_employee_category
		);

		return {
			filters: {
				custom_employee_category:
					frm.doc.custom_employee_category
			}
		};
	});
}