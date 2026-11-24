import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
    SerialandBatchBundle,
)


class CustomSerialandBatchBundle(SerialandBatchBundle):

    def set_incoming_rate_for_inward_transaction(
        self, row=None, save=False, prev_sle=None
    ):
        """
        Preserve serial-wise original sale valuation only for
        custom return stock recovery bundles.

        All other ERPNext transactions use standard valuation.
        """

        if not self.get("custom_is_return_stock_recovery"):
            return super().set_incoming_rate_for_inward_transaction(
                row=row,
                save=save,
                prev_sle=prev_sle,
            )

        precision = frappe.get_precision(
            "Serial and Batch Entry", "incoming_rate"
        )

        for entry in self.entries:

            rate = flt(entry.incoming_rate, precision)

            if rate < 0:
                frappe.throw(
                    _(
                        "Return stock recovery stopped: original valuation "
                        "rate is missing for Serial No {0}."
                    ).format(entry.serial_no or entry.name)
                )

            entry.incoming_rate = rate
            entry.stock_value_difference = flt(entry.qty) * rate

            if save:
                entry.db_set(
                    {
                        "incoming_rate": rate,
                        "stock_value_difference": entry.stock_value_difference,
                    }
                )
