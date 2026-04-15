frappe.ui.form.on('Employee', {
    onload: function(frm) {
        // Form load hote hi filter apply karein
        apply_holiday_filter(frm);
    },
    refresh: function(frm) {
        // Refresh par bhi filter lagayein
        apply_holiday_filter(frm);
    },
    custom_employee_category: function(frm) {
        // Agar user category badalta hai, toh purani holiday_list clear ho jaye
        // aur naya filter apply ho jaye
        frm.set_value("holiday_list", "");
        apply_holiday_filter(frm);
    }
});

function apply_holiday_filter(frm) {
    frm.set_query("holiday_list", function() {
        if (frm.doc.custom_employee_category) {
            return {
                filters: {
                    // Holiday List DocType mein jo custom_employee_category hai
                    // wo Employee DocType ki selected value se match karni chahiye
                    "custom_employee_category": frm.doc.custom_employee_category
                }
            };
        } else {
            // Agar koi category select nahi hai, toh filter hat jayega ya sab dikhayega
            return {
                filters: {}
            };
        }
    });
}