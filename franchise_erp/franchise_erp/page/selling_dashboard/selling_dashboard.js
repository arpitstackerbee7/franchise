frappe.pages['selling-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Selling Dashboard',
		single_column: true
	});
}