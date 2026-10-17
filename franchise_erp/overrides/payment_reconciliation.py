
import frappe
from frappe import _

from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import (
    PaymentReconciliation,
)


class CustomPaymentReconciliation(PaymentReconciliation):
    def reconcile_allocations(self, skip_ref_details_update_for_pe=False):
        # Run this restriction only when enabled in TZU Setting.
        block_system_generated_je = frappe.db.get_single_value(
            "TZU Setting",
            "is_system_generated_je",
        )

        if block_system_generated_je:
            for row in self.get("allocation"):
                if (
                    row.get("invoice_number")
                    and row.get("allocated_amount")
                    and row.get("reference_type")
                    in ("Sales Invoice", "Purchase Invoice")
                ):
                    frappe.throw(
                        _(
                            "Reconciliation stopped: automatic system-generated "
                            "Credit Note/Debit Note Journal Entries are disabled "
                            "for this reconciliation. Please review TZU Setting."
                        )
                    )

        return super().reconcile_allocations(
            skip_ref_details_update_for_pe=skip_ref_details_update_for_pe
        )
