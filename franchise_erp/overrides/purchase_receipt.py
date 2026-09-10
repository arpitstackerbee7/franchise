import frappe
from frappe.utils import flt

from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
    PurchaseReceipt as ERPNextPurchaseReceipt
)


class PurchaseReceipt(ERPNextPurchaseReceipt):

    def validate(self):

        # --------------------------------------------------
        # NORMAL PURCHASE RECEIPT
        # --------------------------------------------------

        if not (
            self.get("is_return")
            and self.get("custom_bulk_purchase_return")
        ):

            return super().validate()

        # --------------------------------------------------
        # BULK PURCHASE RETURN
        #
        # ERPNext standard validation expects every
        # purchase_receipt_item to belong to return_against.
        #
        # Our Bulk Purchase Return can contain items from
        # multiple GRNs.
        #
        # Temporarily remove return_against only while
        # standard validate_return() runs.
        # --------------------------------------------------

        original_return_against = (
            self.return_against
        )

        self.return_against = None

        try:

            super().validate()

        finally:

            # Restore actual header reference
            self.return_against = (
                original_return_against
            )

    def _remove_bulk_return_status_updater(self):

        """
        Standard ERPNext status updater updates
        Purchase Receipt Item.returned_qty using
        return_against.

        That works for one GRN only.

        For Bulk Purchase Return we update all original
        GRN items manually.
        """

        self.status_updater = [

            updater

            for updater in self.status_updater

            if not (
                updater.get("target_dt")
                == "Purchase Receipt Item"

                and updater.get("target_field")
                == "returned_qty"
            )
        ]

    def _update_bulk_returned_qty(
        self,
        reverse=False
    ):

        """
        Update returned_qty on every original
        Purchase Receipt Item used by this combined return.
        """

        processed = {}

        for item in self.items:

            purchase_receipt_item = (
                item.get("purchase_receipt_item")
            )

            if not purchase_receipt_item:
                continue

            qty = abs(
                flt(
                    item.get("received_stock_qty")
                    or item.get("stock_qty")
                    or item.get("qty")
                )
            )

            if not qty:
                continue

            processed.setdefault(
                purchase_receipt_item,
                0
            )

            processed[
                purchase_receipt_item
            ] += qty

        affected_prs = set()

        for purchase_receipt_item, qty in processed.items():

            source = frappe.db.get_value(
                "Purchase Receipt Item",
                purchase_receipt_item,
                [
                    "parent",
                    "qty",
                    "returned_qty"
                ],
                as_dict=True
            )

            if not source:
                continue

            current_returned = flt(
                source.returned_qty
            )

            if reverse:

                new_returned = max(
                    0,
                    current_returned - qty
                )

            else:

                new_returned = (
                    current_returned + qty
                )

            # Do not exceed received qty
            new_returned = min(
                new_returned,
                abs(flt(source.qty))
            )

            frappe.db.set_value(
                "Purchase Receipt Item",
                purchase_receipt_item,
                "returned_qty",
                new_returned,
                update_modified=False
            )

            affected_prs.add(
                source.parent
            )

        # --------------------------------------------------
        # UPDATE % RETURNED ON ORIGINAL GRNs
        # --------------------------------------------------

        for purchase_receipt in affected_prs:

            totals = frappe.db.sql(
                """
                SELECT
                    COALESCE(
                        SUM(ABS(qty)),
                        0
                    ) AS total_qty,

                    COALESCE(
                        SUM(ABS(returned_qty)),
                        0
                    ) AS returned_qty

                FROM `tabPurchase Receipt Item`

                WHERE parent = %s
                """,
                purchase_receipt,
                as_dict=True
            )[0]

            total_qty = flt(
                totals.total_qty
            )

            returned_qty = flt(
                totals.returned_qty
            )

            per_returned = 0

            if total_qty:

                per_returned = min(
                    100,
                    (
                        returned_qty
                        / total_qty
                    ) * 100
                )

            frappe.db.set_value(
                "Purchase Receipt",
                purchase_receipt,
                "per_returned",
                per_returned,
                update_modified=False
            )

    def on_submit(self):

        is_bulk_return = (
            self.get("is_return")
            and self.get("custom_bulk_purchase_return")
        )

        if not is_bulk_return:

            return super().on_submit()

        # --------------------------------------------------
        # Don't let standard status updater update only
        # the first GRN.
        # --------------------------------------------------

        self._remove_bulk_return_status_updater()

        # Normal ERPNext submit:
        #
        # stock ledger
        # GL
        # PO returned qty
        # etc.
        #
        # remains intact.
        super().on_submit()

        # Update ALL original GRN items
        self._update_bulk_returned_qty(
            reverse=False
        )

    def on_cancel(self):

        is_bulk_return = (
            self.get("is_return")
            and self.get("custom_bulk_purchase_return")
        )

        if not is_bulk_return:

            return super().on_cancel()

        self._remove_bulk_return_status_updater()

        # Normal ERPNext cancellation
        super().on_cancel()

        # Reverse returned qty for ALL original GRNs
        self._update_bulk_returned_qty(
            reverse=True
        )