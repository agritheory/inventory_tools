# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryToolsSettings(Document):
	pass


@frappe.whitelist()
def create_inventory_tools_settings(doc, method=None):
	if not frappe.db.exists("Company", doc.name) or frappe.db.exists(
		"Inventory Tools Settings", doc.name
	):
		return
	its = frappe.new_doc("Inventory Tools Settings")
	its.company = doc.name
	its.save()
