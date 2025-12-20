frappe.ui.form.on("Address", {
    refresh(frm) {
		frm.toggle_display("city", false);
	},
	custom_citytown(frm) {
		if (!frm.doc.custom_citytown) return;

		frappe.db.get_value(
			"City",
			frm.doc.custom_citytown,
			["city","state", "country"],
			(city) => {
				if (!city) return;

				frm.set_value("country", city.country);
				frm.set_value("city", city.city);
				frappe.db.get_value(
					"State",
					city.state,
					["state"],
					(state_doc) => {
						if (state_doc) {
							frm.set_value("state", state_doc.state);
						}
					}
				);
			}
		);
	}
});
