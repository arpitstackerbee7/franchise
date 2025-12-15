frappe.ui.form.on("Color", {
    __newname(frm) {
        if (frm.doc.__newname) {
            frm.set_value("custom_color_code", generate_short_code(frm.doc.__newname));
        }
    }
});

function generate_short_code(name) {
    if (!name) return "";

    const words = name.trim().toUpperCase().split(/\s+/);

    if (words.length === 1) {
        return words[0].substring(0, 2);
    }

    return words[0][0] + words[1][0];
}
