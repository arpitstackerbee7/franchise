import frappe
from erpnext.setup.doctype.item_group.item_group import ItemGroup

class CustomItemGroup(ItemGroup):

    def autoname(self):
        print("self autoname =======================>",self)

        if self.parent_item_group and self.parent_item_group != "All Item Groups":
            self.name = f"{self.parent_item_group}-{self.item_group_name}"
        else:
            self.name = self.item_group_name

    # def on_update(self):
    #     super().on_update()   
    #     frappe.db.set_value("Item Group", self.name, "item_group_name", "vk00")

