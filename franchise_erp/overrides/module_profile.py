import frappe

from frappe.config import get_modules_from_all_apps
from frappe.core.doctype.module_profile.module_profile import ModuleProfile


class CustomModuleProfile(ModuleProfile):

    def onload(self):

        all_modules = sorted(
            m.get("module_name")
            for m in get_modules_from_all_apps()
            if m.get("module_name")
        )


        if frappe.session.user == "Administrator":
            self.set_onload(
                "all_modules",
                all_modules
            )
            return

        restricted_modules = set()

        try:

            viewer_docs = frappe.get_all(
                "User Role Viewer",
                filters={
                    "user": frappe.session.user,
                    "enabled": 1
                },
                pluck="name"
            )

            for viewer in viewer_docs:

                rows = frappe.get_all(
                    "User Module Profile Viewer Detail",
                    filters={
                        "parent": viewer,
                        "parenttype": "User Role Viewer",
                        "check": 1
                    },
                    pluck="role"
                )

                restricted_modules.update(
                    module
                    for module in rows
                    if module
                )

        except Exception:
            restricted_modules = set()


        allowed_modules = [
            module
            for module in all_modules
            if module not in restricted_modules
        ]


        self.set_onload(
            "all_modules",
            sorted(set(allowed_modules))
        )