import frappe
from frappe.model.document import Document

class IncomingLogistic(Document):

    def validate(self):
        self.set_company()
        self.set_item_rate_amount()

    def on_submit(self):
        self.create_purchase_invoice()

    def set_company(self):
        # Default company if blank
        if not self.company:
            self.company = frappe.defaults.get_global_default("company")

    def set_item_rate_amount(self):
        if self.item_code and self.received_qty:
            # standard rate from Item master
            item = frappe.get_doc("Item", self.item_code)
            rate = item.standard_rate or 0
            self.rate = rate
            self.amount = rate * self.received_qty

    def create_purchase_invoice(self):
        # Prevent duplicate PI
        if self.purchase_invoice:
            return

        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = self.supplier
        pi.company = self.company

        pi.append("items", {
            "item_code": self.item_code,
            "qty": self.received_qty,
            "rate": self.rate
        })

        pi.insert(ignore_permissions=True)
        pi.submit()

        # Save PI reference in Incoming Logistic
        self.purchase_invoice = pi.name
        frappe.db.set_value(
            self.doctype,
            self.name,
            "purchase_invoice",
            pi.name
        )
