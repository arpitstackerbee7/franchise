frappe.ui.form.on("Leave Application", {
    refresh(frm) {
        console.log("=== Franchise ERP Leave JS Loaded ===");

        set_leave_type_filter(frm);
    },

    onload(frm) {
        set_leave_type_filter(frm);
    },

    employee(frm) {gi
        set_leave_type_filter(frm);

        // Clear leave type when employee changes
        frm.set_value("leave_type", "");
    },

    custom_employee_category(frm) {
        set_leave_type_filter(frm);

        // Clear leave type when category changes
        frm.set_value("leave_type", "");
    },

    before_workflow_action(frm) {
        if (frm.selected_workflow_action === "Approve") {
            frm.set_value("custom_rejection_reason", "N/A");
            return;
        }

        if (frm.selected_workflow_action === "Reject") {
            let reason = (frm.doc.custom_rejection_reason || "").trim();

            // Reason already exists, so allow workflow to continue directly
            if (reason !== "" && reason !== "N/A") {
                return;
            }

            return new Promise((resolve, reject) => {
                let completed = false;

                let d = new frappe.ui.Dialog({
                    title: "Reason for Rejection",

                    fields: [
                        {
                            fieldname: "rejection_reason",
                            fieldtype: "Small Text",
                            label: "Rejection Reason",
                            reqd: 1
                        }
                    ],

                    primary_action_label: "Reject",

                    primary_action(values) {
                        let rejection_reason =
                            (values.rejection_reason || "").trim();

                        if (!rejection_reason) {
                            frappe.msgprint(
                                "Please enter a rejection reason."
                            );
                            return;
                        }

                        completed = true;

                        frm.set_value(
                            "custom_rejection_reason",
                            rejection_reason
                        ).then(() => {
                            d.hide();
                            resolve();
                        });
                    }
                });

                d.onhide = () => {
                    // If user closes the dialog without submitting
                    if (!completed) {
                        reject();
                    }
                };

                frappe.dom.unfreeze();

                d.show();
            });
        }
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