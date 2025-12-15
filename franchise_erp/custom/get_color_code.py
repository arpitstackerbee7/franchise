@frappe.whitelist()
def get_color_code(color_name):
    return frappe.db.get_value("Color", {"color_name": color_name}, "color_code") or ""
