frappe.ui.form.on('SIS Configuration', {
    custom_sis_debit_note_creation_period(frm) {
        let period = frm.doc.custom_sis_debit_note_creation_period;

        // Get wrapper of the select field
        let wrapper = $(frm.fields_dict.custom_sis_debit_note_creation_period.wrapper);

        // Remove old span if exists
        wrapper.find(".period-info-text").remove();

        // Define message
        let msg = "";
        if (period === "Weekly") {
            msg = "Monday to Sunday";
        } else if (period === "Fortnightly") {
            msg = "15 days (1 to 15 & 16 to 30/31)";
        } else if (period === "Monthly") {
            msg = "Full month";
        }

        // Append span after select input
        if (msg) {
            wrapper.append(
                `<div class="period-info-text" style="font-size:12px; color:#666; margin-top:3px;">${msg}</div>`
            );
        }
    },

    refresh(frm) {
        // Run on form load also
        frm.trigger('custom_sis_debit_note_creation_period');
    }
});
