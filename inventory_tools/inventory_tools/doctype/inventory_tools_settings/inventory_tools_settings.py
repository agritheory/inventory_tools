# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryToolsSettings(Document):
	def validate(self):
		if self.update_warehouse_path:
			create_warehouse_path_custom_field()


def create_warehouse_path_custom_field():
	if frappe.db.exists("Custom Field", "Warehouse-warehouse_path"):
		return
	cf = frappe.new_doc("Custom Field")
	cf.field_name = ""
	cf.field_type = "Data"
	cf.label = "Warehouse Path"
	# cf.save()

	# property setter for warehouse path


@frappe.whitelist()
def create_inventory_tools_settings(doc, method=None) -> None:
	if frappe.db.exists("Inventory Tools Settings", {"company": doc.name}):
		return
	its = frappe.new_doc("Inventory Tools Settings")
	its.company = doc.name
	its.save()
