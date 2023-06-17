# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryToolsSettings(Document):
	def validate(self):
		self.create_warehouse_path_custom_field()

	def create_warehouse_path_custom_field(self):
		if frappe.db.exists("Custom Field", "Warehouse-warehouse_path"):
			if not self.update_warehouse_path:
				frappe.set_value("Custom Field", "Warehouse-warehouse_path", "hidden", 1)
			return
		cf = frappe.new_doc("Custom Field")
		cf.dt = "Warehouse"
		cf.fieldname = "warehouse_path"
		cf.fieldtype = "Data"
		cf.label = "Warehouse Path"
		cf.module = "Inventory Tools"
		cf.insert_after = "disabled"
		cf.no_copy = 1
		cf.save()

		ps = frappe.new_doc("Property Setter")
		ps.doctype_or_field = "DocType"
		ps.doc_type = "Warehouse"
		ps.property = "search_fields"
		ps.module = "Inventory Tools"
		ps.property_type = "Data"
		ps.value = "warehouse_path"
		ps.save()

		for warehouse in frappe.get_all("Warehouse"):
			wh = frappe.get_doc("Warehouse", warehouse)
			wh.save()


@frappe.whitelist()
def create_inventory_tools_settings(doc, method=None) -> None:
	if frappe.db.exists("Inventory Tools Settings", {"company": doc.name}):
		return
	its = frappe.new_doc("Inventory Tools Settings")
	its.company = doc.name
	its.save()
