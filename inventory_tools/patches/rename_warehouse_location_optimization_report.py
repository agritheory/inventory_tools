# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


TARGET_NAME = "Warehouse Location Optimization"
LEGACY_NAMES = (
	"Warehouse Location Optimization Report",
	"Warehouse Location Suggestion",
)


def execute():
	for old_name in LEGACY_NAMES:
		if not frappe.db.exists("Report", old_name):
			continue

		if frappe.db.exists("Report", TARGET_NAME):
			frappe.delete_doc("Report", old_name, force=1)
		else:
			frappe.rename_doc("Report", old_name, TARGET_NAME, force=1)

	frappe.reload_doc("inventory_tools", "report", "warehouse_location_optimization", force=True)
