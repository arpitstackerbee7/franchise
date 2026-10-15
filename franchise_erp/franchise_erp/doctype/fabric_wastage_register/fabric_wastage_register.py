import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.accounts.utils import get_fiscal_year


class FabricWastageRegister(Document):

    def autoname(self):
        fy = get_fiscal_year(self.posting_date)[0]
        fy_short = f"{fy[:4][-2:]}-{fy[-4:][-2:]}"
        self.name = make_autoname(f"FWR/{fy_short}/.#####")

    def before_save(self):
        if self.docstatus == 0:
            self.status = "Draft"

    def validate(self):
        self.validate_duplicate()
        self.validate_qty()

    def validate_qty(self):

        for row in self.fabric_wastage_detail:

            wastage_qty = row.actual_wastage_qty or 0

            if wastage_qty < 0:
                frappe.throw(
                    f"Row {row.idx}: Actual Wastage cannot be negative."
                )

            if wastage_qty > 0 and not row.reason:
                frappe.throw(
                    f"Row {row.idx}: Please select Wastage Reason."
                )

    def validate_duplicate(self):

        existing = frappe.db.exists(
            "Fabric Wastage Register",
            {
                "subcontracting_order": self.subcontracting_order,
                "docstatus": ["!=", 2],
                "name": ["!=", self.name]
            }
        )

        if existing:
            frappe.throw(
                f"Fabric Wastage Register <b>{existing}</b> already exists for "
                f"Subcontracting Order <b>{self.subcontracting_order}</b>."
            )

    # =========================================================
    # SUBMIT
    # =========================================================

    def on_submit(self):

        self.create_stock_entry()

        self.db_set(
            "status",
            "Submitted",
            update_modified=False
        )

    # =========================================================
    # CANCEL
    # =========================================================

    def on_cancel(self):

        if self.stock_entry:

            se = frappe.get_doc(
                "Stock Entry",
                self.stock_entry
            )

            # Cancel only if submitted
            if se.docstatus == 1:

                se.flags.ignore_links = True
                se.cancel()

        self.db_set(
            "status",
            "Cancelled",
            update_modified=False
        )

    # =========================================================
    # CREATE MATERIAL ISSUE
    # =========================================================

    def create_stock_entry(self):

        # -----------------------------------------------------
        # Prevent duplicate Stock Entry
        # -----------------------------------------------------

        if self.stock_entry:

            existing_se = frappe.db.get_value(
                "Stock Entry",
                self.stock_entry,
                "docstatus"
            )

            if existing_se is not None:
                frappe.throw(
                    f"Stock Entry <b>{self.stock_entry}</b> already exists "
                    f"for Fabric Wastage Register <b>{self.name}</b>."
                )

        # -----------------------------------------------------
        # Get Subcontracting Order
        # -----------------------------------------------------

        subcontracting_order = frappe.get_doc(
            "Subcontracting Order",
            self.subcontracting_order
        )

        # -----------------------------------------------------
        # ACTUAL JOBBER WAREHOUSE
        #
        # Example:
        # Amjad Textiles - TZUPL
        # -----------------------------------------------------

        source_warehouse = subcontracting_order.supplier_warehouse

        if not source_warehouse:
            frappe.throw(
                f"Jobber Warehouse is not set in "
                f"Subcontracting Order <b>{self.subcontracting_order}</b>."
            )

        # -----------------------------------------------------
        # Create Stock Entry
        # -----------------------------------------------------

        stock_entry = frappe.new_doc("Stock Entry")

        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.company = self.company
        stock_entry.posting_date = self.posting_date
        stock_entry.posting_time = self.posting_time

        # -----------------------------------------------------
        # Link Fabric Wastage Register
        # -----------------------------------------------------

        if stock_entry.meta.has_field(
            "custom_fabric_wastage_register"
        ):
            stock_entry.custom_fabric_wastage_register = self.name

        # -----------------------------------------------------
        # Remarks
        # -----------------------------------------------------

        stock_entry.remarks = (
            f"Fabric Wastage against Subcontracting Order "
            f"{self.subcontracting_order} "
            f"through Fabric Wastage Register {self.name}"
        )

        # -----------------------------------------------------
        # Add Wastage Items
        # -----------------------------------------------------

        for row in self.fabric_wastage_detail:

            wastage_qty = row.actual_wastage_qty or 0

            if wastage_qty <= 0:
                continue

            item_code = row.rm_item_code or row.item_code

            if not item_code:
                frappe.throw(
                    f"Row {row.idx}: Item is required."
                )

            # -------------------------------------------------
            # Material Issue
            #
            # Only source warehouse.
            # NO target warehouse.
            # NO In Transit.
            # -------------------------------------------------

            stock_entry.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": wastage_qty,
                    "uom": row.uom,
                    "stock_uom": row.uom,
                    "s_warehouse": source_warehouse
                }
            )

        # -----------------------------------------------------
        # Validate Items
        # -----------------------------------------------------

        if not stock_entry.items:
            frappe.throw(
                "Please enter Actual Wastage Qty before submitting."
            )

        # -----------------------------------------------------
        # Insert
        # -----------------------------------------------------

        stock_entry.insert()

        # -----------------------------------------------------
        # Submit
        #
        # This removes stock from Jobber Warehouse.
        # -----------------------------------------------------

        stock_entry.submit()

        # -----------------------------------------------------
        # Save Reference
        # -----------------------------------------------------

        if self.meta.has_field("stock_entry"):

            self.db_set(
                "stock_entry",
                stock_entry.name,
                update_modified=False
            )

        return stock_entry.name


# =============================================================
# GET SUBCONTRACTING ORDER DATA
# =============================================================

@frappe.whitelist()
def get_subcontracting_order_data(subcontracting_order):

    scr = frappe.get_doc(
        "Subcontracting Order",
        subcontracting_order
    )

    # ---------------------------------------------------------
    # Finished Qty
    # ---------------------------------------------------------

    finished_qty = 0

    if scr.items:
        finished_qty = (
            scr.items[0].received_qty
            or scr.items[0].qty
            or 0
        )

    # ---------------------------------------------------------
    # Basic Data
    # ---------------------------------------------------------

    data = {
        "supplier": scr.supplier,
        "set_warehouse": scr.set_warehouse,
        "items": []
    }

    # ---------------------------------------------------------
    # Supplied Items
    # ---------------------------------------------------------

    for row in scr.supplied_items:

        item_details = frappe.db.get_value(
            "Item",
            row.rm_item_code,
            [
                "custom_size",
                "custom_colour_name",
                "custom_top_fabrics"
            ],
            as_dict=True
        ) or {}

        # -----------------------------------------------------
        # Standard Consumption
        # -----------------------------------------------------

        standard_consumption = 0

        if finished_qty:
            standard_consumption = (
                row.required_qty / finished_qty
            )

        # -----------------------------------------------------
        # Append Item
        # -----------------------------------------------------

        data["items"].append(
            {
                "item_code": row.rm_item_code,
                "rm_item_code": row.rm_item_code,
                "reserve_warehouse": row.reserve_warehouse,
                "size": item_details.get("custom_size"),
                "color": item_details.get("custom_colour_name"),
                "top_fabrics": item_details.get(
                    "custom_top_fabrics"
                ),
                "fabric_sent_qty": row.required_qty,
                "finished_qty_received": finished_qty,
                "standard_consumption": standard_consumption,
                "actual_consumption": row.consumed_qty,
                "uom": row.stock_uom,
                "rate": row.rate,
                "amount": row.amount
            }
        )

    return data