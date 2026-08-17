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
            actual_consumption = row.actual_consumption or 0

            if wastage_qty < 0:
                frappe.throw(
                    f"Row {row.idx}: Actual Wastage cannot be negative."
                )

            # if wastage_qty > actual_consumption:
            #     frappe.throw(
            #         f"Row {row.idx}: Actual Wastage Qty cannot be greater than Actual Consumption."
            #     )

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

    def on_submit(self):
        self.create_stock_entry()
        self.db_set("status", "Submitted", update_modified=False)

    def on_cancel(self):

        if self.stock_entry:
            se = frappe.get_doc("Stock Entry", self.stock_entry)
    
            if se.docstatus == 1:
                se.flags.ignore_links = True
                se.cancel()
                
        self.db_set("status", "Cancelled", update_modified=False)     
            

    # def create_stock_entry(self):

    #     stock_entry = frappe.new_doc("Stock Entry")

    #     stock_entry.stock_entry_type = "Material Issue"
    #     stock_entry.company = self.company
    #     stock_entry.posting_date = self.posting_date
    #     stock_entry.posting_time = self.posting_time

    #     # Optional Custom Reference Fields
    #     if stock_entry.meta.has_field("custom_fabric_wastage_register"):
    #         stock_entry.custom_fabric_wastage_register = self.name

    #     # if stock_entry.meta.has_field("subcontracting_order"):
    #     #     stock_entry.subcontracting_order = self.subcontracting_order

    #     stock_entry.remarks = (
    #         f"Fabric Wastage against Subcontracting Order "
    #         f"{self.subcontracting_order} "
    #         f"through Fabric Wastage Register {self.name}"
    #     )

    #     for row in self.fabric_wastage_detail:

    #         if not row.actual_wastage_qty:
    #             continue

    #         stock_entry.append("items", {
    #             "item_code": row.item_code,
    #             "qty": row.actual_wastage_qty,
    #             "uom": row.uom,
    #             "stock_uom": row.uom,
    #             "s_warehouse": self.warehouse
    #         })
    #     # for row in self.fabric_wastage_detail:

    #     #     stock_entry.append("items", {
    #     #         "item_code": row.item_code,
    #     #         "qty": row.actual_wastage_qty,
    #     #         "uom": row.uom,
    #     #         "stock_uom": row.uom,
    #     #         "s_warehouse": row.reserve_warehouse
    #     #     })
        
    #     if not stock_entry.items:
    #         frappe.throw("Please enter Actual Wastage Qty before submitting.")

    #     stock_entry.insert()
    #     stock_entry.submit()

    #     if self.meta.has_field("stock_entry"):
    #         self.db_set("stock_entry", stock_entry.name)
    def create_stock_entry(self):

        stock_entry = frappe.new_doc("Stock Entry")

        # =========================================================
        # STOCK ENTRY SETTINGS
        # =========================================================

        stock_entry.stock_entry_type = "Material Receipt"
        stock_entry.company = self.company
        stock_entry.posting_date = self.posting_date
        stock_entry.posting_time = self.posting_time

        # =========================================================
        # LINK TO FABRIC WASTAGE REGISTER
        # =========================================================

        if stock_entry.meta.has_field("custom_fabric_wastage_register"):
            stock_entry.custom_fabric_wastage_register = self.name

        stock_entry.remarks = (
            f"Fabric Wastage against Subcontracting Order "
            f"{self.subcontracting_order} "
            f"through Fabric Wastage Register {self.name}"
        )

        # =========================================================
        # ADD ITEMS
        # =========================================================

        for row in self.fabric_wastage_detail:

            wastage_qty = row.actual_wastage_qty or 0

            # Skip zero wastage
            if wastage_qty <= 0:
                continue

            # Target warehouse
            target_warehouse = row.reserve_warehouse or self.warehouse

            if not target_warehouse:
                frappe.throw(
                    f"Row {row.idx}: Please select Warehouse."
                )

            stock_entry.append("items", {
                "item_code": row.item_code,
                "qty": wastage_qty,
                "uom": row.uom,
                "stock_uom": row.uom,
                "t_warehouse": target_warehouse
            })

        # =========================================================
        # VALIDATION
        # =========================================================

        if not stock_entry.items:
            frappe.throw(
                "Please enter Actual Wastage Qty before submitting."
            )

        # =========================================================
        # CREATE STOCK ENTRY AS DRAFT
        # =========================================================

        stock_entry.insert()

        # IMPORTANT:
        # Do NOT submit here.
        #
        # stock_entry.submit()

        # =========================================================
        # SAVE REFERENCE
        # =========================================================

        if self.meta.has_field("stock_entry"):
            self.db_set(
                "stock_entry",
                stock_entry.name,
                update_modified=False
            )

        return stock_entry.name


@frappe.whitelist()
def get_subcontracting_order_data(subcontracting_order):

    scr = frappe.get_doc("Subcontracting Order", subcontracting_order)

    finished_qty = 0
    if scr.items:
        finished_qty = scr.items[0].received_qty or scr.items[0].qty or 0

    data = {
        "supplier": scr.supplier,
        "set_warehouse": scr.set_warehouse,
        "items": []
    }

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

        standard_consumption = 0
        if finished_qty:
            standard_consumption = row.required_qty / finished_qty
                    
        data["items"].append({
            "item_code": row.rm_item_code,          # ✅ RM Item
            "rm_item_code": row.rm_item_code,       # ✅
            "reserve_warehouse": row.reserve_warehouse,   # ✅
            "size": item_details.get("custom_size"),
            "color": item_details.get("custom_colour_name"),
            "top_fabrics": item_details.get("custom_top_fabrics"),
            "fabric_sent_qty": row.required_qty,
            "finished_qty_received": finished_qty,
            "standard_consumption": standard_consumption,
            "actual_consumption": row.consumed_qty,
            "uom": row.stock_uom,
            "rate": row.rate,
            "amount": row.amount
        })

    return data




