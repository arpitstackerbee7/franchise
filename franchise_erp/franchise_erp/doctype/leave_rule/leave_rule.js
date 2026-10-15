// Copyright (c) 2026, Franchise Erp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Leave Rule", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Leave Rule", {
    refresh: function(frm) {
        let rules_html = `
            <div style="
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 8px;
                background: #f9fbfd;
                color: #222;
                font-size: 13px;
                line-height: 1.6;
            ">
                <h4 style="margin-bottom: 10px; font-size: 14px; font-weight: bold; color: #0a3d62;">
                    Priority Rules (How they work)
                </h4>
                <ol style="padding-left: 18px; margin: 0;">
                    <li>
                        <b>Daily Hours Fulfilment</b> → 
                        If an employee completes the required daily working hours, other rules (late entry, early exit, etc.) are ignored.  
                        <i>Example:</i> Even if someone comes late but still works 9 hrs, it won’t be counted as a violation.
                    </li>
                    <li>
                        <b>Monthly Late Time Allowance</b> → 
                        Provides a buffer (e.g. 60 mins late/month). As long as the employee is within this allowance, no deductions apply.  
                        <i>Example:</i> If the allowance is 60 mins and an employee is late 15 mins × 4 times = 60 mins, it’s still fine. On the 61st minute, deduction rules kick in.
                    </li>
                    <li>
                        <b>Late Entry Count</b> → 
                        Defines how many times an employee can arrive late before deductions start.  
                        <i>Example:</i> Allowed 3 late entries/month. On the 4th late entry, deductions begin.
                    </li>
                    <li>
                        <b>Early Exit Count</b> → 
                        Defines how many times an employee can leave early before deductions start.  
                        <i>Example:</i> Allowed 2 early exits/month. On the 3rd early exit, deductions begin.
                    </li>
                    <li>
                        <b>Sandwich</b> → 
                        If enabled, leaves between two holidays are also treated as leave.  
                        <i>Example:</i> If Friday and Monday are absent, Saturday & Sunday in between will also be marked as leave.
                    </li>
                </ol>

                <p style="margin-top: 10px; font-size: 12px; color: #555;">
                    <b>Note:</b> Daily Hours Fulfilment has the highest priority, followed by Monthly Late Time Allowance. 
                    Late Entry and Early Exit work together. Sandwich works independently.
                </p>

                <hr style="margin: 14px 0; border-top: 1px solid #ddd;">

                <h4 style="margin-bottom: 8px; font-size: 14px; font-weight: bold; color: #0a3d62;">
                    Deduction Modes
                </h4>
                <ul style="padding-left: 18px; margin: 0;">
                    <li>
                        <b>Affect Leave Balance</b> → 
                        Deductions are made from the employee’s available leave balance based on leave priorities (e.g. Casual → Sick → LWP).  
                        <i>Example:</i> After 3 late entries, 1 day of leave is deducted. If CL balance is 0.5 and SL balance is 0.5, deduction is split across both.  
                        <br>
                        <span style="color:#006266; font-size:12px;">
                            ⚙️ System Impact: Creates a record in <b>Leave Deduction Log</b> and updates the <b>Leave Ledger</b> to reflect reduced balance.
                        </span>
                    </li>
                    <li>
                        <b>Affect Payroll Directly</b> → 
                        Instead of using leave balances, the deduction directly reduces the employee’s payable days or salary in Payroll.  
                        <i>Example:</i> 1 day salary is deducted directly after 3 late entries, without touching leave balances.  
                        <br>
                        <span style="color:#006266; font-size:12px;">
                            ⚙️ System Impact: Creates a record in <b>Payroll Deduction Log</b> and updates the <b>Salary Slip</b> calculations.
                        </span>
                    </li>
                </ul>

                <p style="margin-top: 10px; font-size: 12px; color: #555;">
                    <b>Tip:</b> You can enable either <i>Affect Leave Balance</i> or <i>Affect Payroll Directly</i>, not both at the same time.
                </p>
            </div>
        `;

        frm.fields_dict.priority_rules_display.$wrapper.html(rules_html);

        frm.set_query('leave_type', () => {
            return {
                filters: { is_lwp: 0 }
            };
        });
    }
});


frappe.ui.form.on('Leave Rule', {
    validate: function(frm) {
        if (frm.doc.affect_leave_balance && frm.doc.affect_payroll_directly) {
            frappe.throw(__('You cannot enable both "Affect Leave Balance" and "Affect Payroll Directly" at the same time.'));
        }
    },
    affect_leave_balance: function(frm) {
        if (frm.doc.affect_leave_balance && frm.doc.affect_payroll_directly) {
            frm.set_value('affect_payroll_directly', 0);
            frappe.msgprint(__('Disabled "Affect Payroll Directly" since "Affect Leave Balance" is enabled.'));
        }
    },
    affect_payroll_directly: function(frm) {
        if (frm.doc.affect_payroll_directly && frm.doc.affect_leave_balance) {
            frm.set_value('affect_leave_balance', 0);
            frappe.msgprint(__('Disabled "Affect Leave Balance" since "Affect Payroll Directly" is enabled.'));
        }
    }
});


frappe.ui.form.on("Leave Rule", {
    affect_leave_balance(frm) {
        // If affect_leave_balance is checked
        if (frm.doc.affect_leave_balance) {
            frm.set_df_property("deduction_unit", "options", ["1", "0.5"]);
            frm.set_value("deduction_unit", ""); // reset selection
        } else {
            // Restore full options for payroll deduction
            frm.set_df_property("deduction_unit", "options", ["0.25", "0.33", "0.5", "0.75", "1"]);
        }
    },

    refresh(frm) {
        // Apply once when form loads
        if (frm.doc.affect_leave_balance) {
            frm.set_df_property("deduction_unit", "options", ["1", "0.5"]);
        } else {
            frm.set_df_property("deduction_unit", "options", ["0.25", "0.33", "0.5", "0.75", "1"]);
        }
    }
});