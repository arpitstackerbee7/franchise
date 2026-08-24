frappe.ui.form.on("Full and Final Statement", {
    refresh(frm) {

        // Only for submitted and unpaid Full & Final Statement
        if (frm.doc.docstatus !== 1 || frm.doc.status !== "Unpaid") {
            return;
        }

        // Override the standard Create Journal Entry event
        frm.events.create_journal_entry = function (frm) {

            // ---------------------------------------------------------
            // First get Employee Payable Account from TZU Setting
            // ---------------------------------------------------------
            frappe.db.get_single_value(
                "TZU Setting",
                "employee_payable_account"
            ).then(employee_payable_account => {

                // -----------------------------------------------------
                // If account is not configured, stop here
                // -----------------------------------------------------
                if (!employee_payable_account) {
                    frappe.throw({
                        title: __("Missing Employee Payable Account"),
                        message: __(
                            "Please set Employee Payable Account in TZU Setting before creating the Journal Entry."
                        )
                    });

                    return;
                }

                // -----------------------------------------------------
                // Create Journal Entry using standard HRMS method
                // -----------------------------------------------------
                frappe.call({
                    method: "create_journal_entry",
                    doc: frm.doc,

                    callback: function (r) {

                        if (!r.message) {
                            return;
                        }

                        // -------------------------------------------------
                        // Journal Entry document returned by HRMS
                        // -------------------------------------------------
                        let journal_entry = r.message;

                        // -------------------------------------------------
                        // Set Voucher Type
                        // -------------------------------------------------
                        journal_entry.voucher_type = "Journal Entry";

                        // -------------------------------------------------
                        // Set Employee Payable Account on CREDIT rows
                        // -------------------------------------------------
                        (journal_entry.accounts || []).forEach(row => {

                            if (flt(row.credit_in_account_currency) > 0) {
                                row.account = employee_payable_account;
                            }

                        });

                        // -------------------------------------------------
                        // Sync Journal Entry document with Frappe
                        // -------------------------------------------------
                        let doclist = frappe.model.sync(journal_entry);

                        // -------------------------------------------------
                        // Open Journal Entry
                        // -------------------------------------------------
                        frappe.set_route(
                            "Form",
                            doclist[0].doctype,
                            doclist[0].name
                        );
                    }
                });

            });
        };
    }
});