# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from . import __version__ as app_version

app_name = "inventory_tools"
app_title = "Inventory Tools"
app_publisher = "AgriTheory"
app_description = "Inventory Tools"
app_email = "support@agritheory.dev"
app_license = "MIT"
required_apps = ["erpnext", "hrms"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/inventory_tools/css/inventory_tools.css"
app_include_js = ["inventory_tools.bundle.js"]

# include js, css files in header of web template
# web_include_css = "/assets/inventory_tools/css/inventory_tools.css"
# web_include_js = "/assets/inventory_tools/js/inventory_tools.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "inventory_tools/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Job Card": "public/js/job_card_custom.js",
	"Purchase Invoice": "public/js/purchase_invoice_custom.js",
	"Purchase Order": "public/js/purchase_order_custom.js",
	"Operation": "public/js/operation_custom.js",
	"Purchase Invoice": "public/js/purchase_invoice_custom.js",
	"Purchase Order": "public/js/purchase_order_custom.js",
	"Stock Entry": "public/js/stock_entry_custom.js",
	"Work Order": "public/js/work_order_custom.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

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
# 	"methods": "inventory_tools.utils.jinja_methods",
# 	"filters": "inventory_tools.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "inventory_tools.install.before_install"
# after_install = "inventory_tools.install.after_install"
after_migrate = "inventory_tools.customize.load_customizations"

# Uninstallation
# ------------

# before_uninstall = "inventory_tools.uninstall.before_uninstall"
# after_uninstall = "inventory_tools.uninstall.after_uninstall"

# Boot
# ------------
extend_bootinfo = "inventory_tools.inventory_tools.boot.boot_session"


# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "inventory_tools.notifications.get_notification_config"

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

override_doctype_class = {
	"Job Card": "inventory_tools.inventory_tools.overrides.job_card.InventoryToolsJobCard",
	"Production Plan": "inventory_tools.inventory_tools.overrides.production_plan.InventoryToolsProductionPlan",
	"Purchase Invoice": "inventory_tools.inventory_tools.overrides.purchase_invoice.InventoryToolsPurchaseInvoice",
	"Purchase Order": "inventory_tools.inventory_tools.overrides.purchase_order.InventoryToolsPurchaseOrder",
	"Purchase Receipt": "inventory_tools.inventory_tools.overrides.purchase_receipt.InventoryToolsPurchaseReceipt",
	"Sales Order": "inventory_tools.inventory_tools.overrides.sales_order.InventoryToolsSalesOrder",
	"Stock Entry": "inventory_tools.inventory_tools.overrides.stock_entry.InventoryToolsStockEntry",
	"Work Order": "inventory_tools.inventory_tools.overrides.work_order.InventoryToolsWorkOrder",
}


# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
		"validate": ["inventory_tools.inventory_tools.overrides.uom.validate_uom_has_conversion"],
	},
	"Company": {
		"validate": [
			"inventory_tools.inventory_tools.doctype.inventory_tools_settings.inventory_tools_settings.create_inventory_tools_settings",
		],
		"after_insert": [
			"inventory_tools.inventory_tools.doctype.inventory_tools_settings.inventory_tools_settings.create_inventory_tools_settings",
		],
	},
	"Item": {
		"validate": ["inventory_tools.inventory_tools.overrides.uom.duplicate_weight_to_uom_conversion"],
	},
	"Warehouse": {
		"validate": ["inventory_tools.inventory_tools.overrides.warehouse.update_warehouse_path"]
	},
	"Operation": {
		"validate": [
			"inventory_tools.inventory_tools.overrides.operation.validate_alternative_workstation"
		]
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"inventory_tools.tasks.all"
# 	],
# 	"daily": [
# 		"inventory_tools.tasks.daily"
# 	],
# 	"hourly": [
# 		"inventory_tools.tasks.hourly"
# 	],
# 	"weekly": [
# 		"inventory_tools.tasks.weekly"
# 	],
# 	"monthly": [
# 		"inventory_tools.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "inventory_tools.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry": "inventory_tools.inventory_tools.overrides.work_order.make_stock_entry",
	"erpnext.stock.get_item_details.get_item_details": "inventory_tools.inventory_tools.overrides.purchase_order.get_item_details",
}


# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "inventory_tools.task.get_dashboard_data"
# }

standard_queries = {
	"Warehouse": "inventory_tools.inventory_tools.overrides.warehouse.warehouse_query",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["inventory_tools.utils.before_request"]
# after_request = ["inventory_tools.utils.after_request"]

# Job Events
# ----------
# before_job = ["inventory_tools.utils.before_job"]
# after_job = ["inventory_tools.utils.after_job"]

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
# 	"inventory_tools.auth.validate"
# ]

# Inventory Tools UOM Enforcement
# --------------------------------

inventory_tools_uom_enforcement = {
	"BOM": {
		"BOM Item": {"items": ["uom"]},
	},
	"Delivery Note": {
		"Delivery Note Item": {"items": ["uom", "weight_uom"]},
	},
	"Item Price": {"Item Price": ["uom"]},
	"Item": {"Item": ["sales_uom", "purchase_uom", "weight_uom"]},
	"Job Card": {"Job Card Item": {"items": ["uom"]}},
	"Material Request": {"Material Request Item": {"items": ["uom"]}},
	"Opportunity": {"Opportunity Item": {"items": ["uom"]}},
	"Pick List": {"Pick List Item": {"locations": ["uom"]}},
	"POS Invoice": {"POS Invoice Item": {"items": ["uom"]}},
	"Production Plan": {"Production Plan Item": {"po_items": ["planned_uom"]}},
	"Purchase Invoice": {
		"Purchase Invoice Item": {"items": ["uom", "weight_uom"]},
	},
	"Purchase Order": {"Purchase Order Item": {"items": ["uom"]}},
	"Purchase Receipt": {
		"Purchase Receipt Item": {"items": ["uom", "weight_uom"]},
	},
	"Putaway Rule": {"Putaway Rule Item": ["uom"]},
	"Quotation": {"Quotation Item": {"items": ["uom"]}},
	"Request for Quotation": {"Request for Quotation Item": {"items": ["uom"]}},
	"Sales Invoice": {"Sales Invoice Item": {"items": ["uom"]}},
	"Sales Order": {
		"Sales Order Item": {"items": ["uom", "weight_uom"]},
	},
	"Stock Entry": {"Stock Entry Detail": {"items": ["uom"]}},
	"Supplier Quotation": {"Supplier Quotation Item": {"items": ["uom"]}},
}
