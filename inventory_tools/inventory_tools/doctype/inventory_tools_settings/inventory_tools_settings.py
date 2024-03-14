# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryToolsSettings(Document):
	def validate(self):
		self.create_warehouse_path_custom_field()
		self.validate_single_aggregation_company()

	def create_warehouse_path_custom_field(self):
		if frappe.db.exists("Custom Field", "Warehouse-warehouse_path"):
			if not self.update_warehouse_path:
				frappe.set_value("Custom Field", "Warehouse-warehouse_path", "hidden", 1)
				frappe.set_value(
					"Property Setter",
					{"doctype_or_field": "DocType", "doc_type": "Warehouse", "property": "search_fields"},
					"search_fields",
					"",
				)
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

	def validate_single_aggregation_company(self):
		if not self.purchase_order_aggregation_company:
			return

		itsl = [
			frappe.get_doc("Inventory Tools Settings", i)
			for i in frappe.get_all("Inventory Tools Settings")
		]
		for its in itsl:
			if its.name == self.name or not its.purchase_order_aggregation_company:
				continue
			if self.purchase_order_aggregation_company != its.purchase_order_aggregation_company:
				frappe.throw(
					f"Purchase Order Aggregation Company in {its.name} Inventory Tools Settings is set to {its.purchase_order_aggregation_company}"
				)
			if self.aggregated_purchasing_warehouse != its.aggregated_purchasing_warehouse:
				frappe.throw(
					f"Purchase Order Aggregation Company in {its.name} Inventory Tools Settings is set to {its.aggregated_purchasing_warehouse}"
				)


@frappe.whitelist()
def create_inventory_tools_settings(doc, method=None) -> None:
	if not frappe.db.exists("Company", doc.name) or frappe.db.exists(
		"Inventory Tools Settings", {"company": doc.name}
	):
		return
	its = frappe.new_doc("Inventory Tools Settings")
	its.company = doc.name
	its.save()
