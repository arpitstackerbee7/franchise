app_name = "franchise_erp"
app_title = "Franchise Erp"
app_publisher = "Franchise Erp"
app_description = "Franchise Erp"
app_email = "admin@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "franchise_erp",
# 		"logo": "/assets/franchise_erp/logo.png",
# 		"title": "Franchise Erp",
# 		"route": "/franchise_erp",
# 		"has_permission": "franchise_erp.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# on_login = "franchise_erp.custom.customs.validate_user_status"



doc_events = {
    "Purchase Order":{
    #    "before_submit" : "franchise_erp.custom.purchase_order.create_po_serials"
    },
   "Purchase Invoice": {
       "before_save": "franchise_erp.custom.purchase_invoice.apply_intercompany_gst",
       "validate": "franchise_erp.custom.purchase_invoice_hooks.apply_item_gst",
       "before_submit": "franchise_erp.custom.purchase_invoice_hooks.update_serial_input_gst",
       "before_insert": "franchise_erp.custom.customs.set_customer_email_as_owner",
       "on_submit": "franchise_erp.custom.purchase_invoice_hooks.calculate_single_item_gst"
    },
    "Journal Entry": {
        "on_submit": "franchise_erp.custom.processed_sales_invoice.process_journal_entry",
    },
   
   "Sales Invoice": {
        "before_save": "franchise_erp.custom.sales_invoice.apply_sis_pricing"
    },
    # "Sales Invoice": {
    #     "before_save": ["franchise_erp.custom.sales_invoice_hooks.before_save","franchise_erp.custom.reset_custom_margins_si_pi.reset_custom_margins"],
    #     "before_submit": ["franchise_erp.custom.sales_invoice_validation.before_submit","franchise_erp.custom.reset_custom_margins_si_pi.reset_custom_margins"],
    #     "on_submit": ["franchise_erp.custom.reset_custom_margins_si_pi.reset_custom_margins","franchise_erp.custom.sales_invoice_hooks.force_margin_totals_after_submit"],
    #     "on_update_after_submit":"franchise_erp.custom.reset_custom_margins_si_pi.reset_custom_margins"
    # },

   "Item": {
        "before_insert": "franchise_erp.custom.item_master.generate_item_code",
        "before_save": "franchise_erp.custom.item_master.generate_item_code",
    },
    "Item Group": {
        "validate": "franchise_erp.custom.item_group.validate_same_parent"
    },
    # "Item Group Tree": {
    #     "validate": "franchise_erp.custom.item_group_tree.validate_unique_combination"
    # }
     "Gate Entry": {
        "on_submit": "franchise_erp.custom.gate_entry.on_submit",
        "on_cancel": "franchise_erp.custom.gate_entry.on_cancel"
    }
}



doctype_js = {
    "Purchase Order": "public/js/purchase_order.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "User": "public/js/user_validation.js",
    "Color": "public/js/colour_code.js",
    "Item": "public/js/item_master.js",
    "Address":"public/js/address.js",
    "Supplier":"public/js/supplier.js",
}


# franchise_erp/hooks.py

# override_whitelisted_methods = {
#     "frappe.desk.treeview.get_children": "franchise_erp.overrides.item_group_tree.get_children"
# }

# override_whitelisted_methods = {
#     "franchise_erp.custom.customs.get_user_role_profiles": 
#         "franchise_erp.custom.customs.get_user_role_profiles"
# }
# after_migrate = "franchise_erp.custom.add_user_custom_fields_v2"
# # hooks.py
# patches = [
#     "franchise_erp.patches.add_user_custom_fields"
# ]


# hooks.py
after_migrate = [
    "franchise_erp.event.add_user_custom_fields.create_custom_fields",
    # "franchise_erp.config.workspace.create_sidebar_items"
]

# after_migrate = "franchise_erp.event.add_user_custom_fields.create_custom_fields"

# app_include_js = "public/js/back_date_disabled.js"

app_include_js = [
    "/assets/franchise_erp/js/back_date_disabled.js",
    ]



# include js, css files in header of web template
# web_include_css = "/assets/franchise_erp/css/franchise_erp.css"
# web_include_js = "/assets/franchise_erp/js/franchise_erp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "franchise_erp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "franchise_erp/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "franchise_erp.utils.jinja_methods",
# 	"filters": "franchise_erp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "franchise_erp.install.before_install"
# after_install = "franchise_erp.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "franchise_erp.uninstall.before_uninstall"
# after_uninstall = "franchise_erp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "franchise_erp.utils.before_app_install"
# after_app_install = "franchise_erp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "franchise_erp.utils.before_app_uninstall"
# after_app_uninstall = "franchise_erp.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "franchise_erp.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	# "ToDo": "custom_app.overrides.CustomToDo"
#     "Item Group": "franchise_erp.overrides.item_group.CustomItemGroup"

# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"franchise_erp.tasks.all"
# 	],
# 	"daily": [
# 		"franchise_erp.tasks.daily"
# 	],
# 	"hourly": [
# 		"franchise_erp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"franchise_erp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"franchise_erp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "franchise_erp.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "franchise_erp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "franchise_erp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["franchise_erp.utils.before_request"]
# after_request = ["franchise_erp.utils.after_request"]

# Job Events
# ----------
# before_job = ["franchise_erp.utils.before_job"]
# after_job = ["franchise_erp.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"franchise_erp.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
# fixtures = [
#     "Custom Field",
#     "Property Setter",
#     "Client Script",
#     "Server Script",
#     "City",
#     "State"
# ]


# fixtures = [
#     {
#         "dt": "Custom Field",
#         "filters": [["name", "=", "User-company"]],
#     }
# ]
fixtures = [
        {"dt": "Property Setter"}
        ]

# fixtures = [
#     {
#         "dt": "DocType",
#         # "filters": [
#         #     ["module", "=", "Franchise Erp"],
#         #     ["custom", "=", 1]
#         # ]
#     }
# ]

# fixtures = [
#     {
#         "dt": "State",
#         "filters": [
#             ["country", "=", "India"]
#         ]
#     },
#     {
#         "dt": "City",
#         # "filters": [
#         #     ["country", "=", "India"]
#         # ]
#     }
# ]
