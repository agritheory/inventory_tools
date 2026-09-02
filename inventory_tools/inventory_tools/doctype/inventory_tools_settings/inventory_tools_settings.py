# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryToolsSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from inventory_tools.inventory_tools.doctype.cartonization_applicable_doctype.cartonization_applicable_doctype import (
			CartonizationApplicableDoctype,
		)

		aggregated_purchasing_warehouse: DF.Link | None
		aggregated_sales_warehouse: DF.Link | None
		allow_alternative_workstations: DF.Literal[
			"Do Not Allow Alternative Workstations",
			"Allow Manually Defined Alternative Workstations",
			"Allow Alternative Workstations Based on Workstation Type",
		]
		allow_rotation: DF.Check
		block_issue_from_quarantine: DF.Check
		cartonization_doctypes: DF.TableMultiSelect[CartonizationApplicableDoctype]
		company: DF.Link | None
		create_job_cards_automatically: DF.Literal["Yes", "No"]
		create_purchase_orders: DF.Check
		default_packing_mode: DF.Literal["", "2D Floor", "3D Volumetric", "3D Fitted"]
		default_quarantine_warehouse: DF.Link | None
		enable_cartonization: DF.Check
		enable_quarantine_workflow: DF.Check
		enable_alternative_sales_workflow: DF.Check
		enable_work_order_subcontracting: DF.Check
		enforce_uoms: DF.Check
		fitted_policy: DF.Literal["Ignore", "Warn", "Error"]
		floor_packing_policy: DF.Literal["", "Ignore", "Warn", "Error"]
		max_weight_uom: DF.Link | None
		overproduction_percentage_for_work_order: DF.Percent
		prettify_warehouse_tree: DF.Check
		purchase_order_aggregation_company: DF.Link | None
		sales_order_aggregation_company: DF.Link | None
		show_in_listview: DF.Check
		show_on_website: DF.Check
		solver_timeout_seconds: DF.Int
		update_warehouse_path: DF.Check
		volumetric_policy: DF.Literal["Ignore", "Warn", "Error"]
		weight_validation: DF.Literal["Ignore", "Warn", "Error"]
	# end: auto-generated types

	ALTERNATIVE_SALES_WORKFLOW_PROPERTY_SETTERS = (
		("Packing Slip", "delivery_note", "reqd", "Check", "0"),
		("Shipment Delivery Note", "delivery_note", "reqd", "Check", "0"),
		("Shipment Delivery Note", "delivery_note", "hidden", "Check", "1"),
	)

	def validate(self):
		self.create_warehouse_path_custom_field()
		self.validate_single_aggregation_company()
		self.set_faceted_search_for_all_companies()
		self.sync_alternative_sales_workflow_property_setters()

	def create_warehouse_path_custom_field(self):
		if frappe.db.exists("Custom Field", "Warehouse-warehouse_path"):
			if not self.update_warehouse_path:
				frappe.set_value("Custom Field", "Warehouse-warehouse_path", "hidden", 1)
				ps_name = frappe.db.get_value(
					"Property Setter",
					{"doctype_or_field": "DocType", "doc_type": "Warehouse", "property": "search_fields"},
					"name",
				)
				if ps_name:
					frappe.set_value("Property Setter", ps_name, "value", "")
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
		if not self.purchase_order_aggregation_company and not self.sales_order_aggregation_company:
			return

		itsl = [
			frappe.get_doc("Inventory Tools Settings", i)
			for i in frappe.get_all("Inventory Tools Settings")
		]

		if self.purchase_order_aggregation_company:
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

		if self.sales_order_aggregation_company:
			for its in itsl:
				if its.name == self.name or not its.sales_order_aggregation_company:
					continue
				if self.sales_order_aggregation_company != its.sales_order_aggregation_company:
					frappe.throw(
						f"Sales Order Aggregation Company in {its.name} Inventory Tools Settings is set to {its.sales_order_aggregation_company}"
					)
				if self.sales_order_aggregation_company != its.sales_order_aggregation_company:
					frappe.throw(
						f"Sales Order Aggregation Company in {its.name} Inventory Tools Settings is set to {its.sales_order_aggregation_company}"
					)

	def set_faceted_search_for_all_companies(self):
		for its in frappe.get_all("Inventory Tools Settings", pluck="name"):
			if its == self.name:
				continue
			frappe.db.set_value("Inventory Tools Settings", its, "show_on_website", self.show_on_website)
			frappe.db.set_value("Inventory Tools Settings", its, "show_in_listview", self.show_in_listview)

	def sync_alternative_sales_workflow_property_setters(self) -> None:
		enabled = frappe.db.exists(
			"Inventory Tools Settings",
			{"enable_alternative_sales_workflow": 1},
		)
		seen_doctypes = set()
		for (
			doc_type,
			field_name,
			property_name,
			property_type,
			enabled_value,
		) in self.ALTERNATIVE_SALES_WORKFLOW_PROPERTY_SETTERS:
			setter_name = f"{doc_type}-{field_name}-{property_name}-alternative-sales-workflow"
			if enabled:
				if frappe.db.exists("Property Setter", setter_name):
					frappe.db.set_value("Property Setter", setter_name, "value", enabled_value)
				else:
					property_setter = frappe.new_doc("Property Setter")
					property_setter.doctype_or_field = "DocField"
					property_setter.doc_type = doc_type
					property_setter.field_name = field_name
					property_setter.property = property_name
					property_setter.property_type = property_type
					property_setter.value = enabled_value
					property_setter.module = "Inventory Tools"
					property_setter.name = setter_name
					property_setter.insert(ignore_permissions=True)
			elif frappe.db.exists("Property Setter", setter_name):
				frappe.delete_doc("Property Setter", setter_name, force=1)
			seen_doctypes.add(doc_type)

		for doc_type in seen_doctypes:
			frappe.clear_cache(doctype=doc_type)

		legacy_setter = "Shipment Delivery Note-delivery_note-in_list_view-alternative-sales-workflow"
		if frappe.db.exists("Property Setter", legacy_setter):
			frappe.delete_doc("Property Setter", legacy_setter, force=1)
			frappe.clear_cache(doctype="Shipment Delivery Note")


@frappe.whitelist()
def create_inventory_tools_settings(doc, method=None) -> None:
	if not frappe.db.exists("Company", doc.name) or frappe.db.exists(
		"Inventory Tools Settings", {"company": doc.name}
	):
		return
	its = frappe.new_doc("Inventory Tools Settings")
	its.company = doc.name
	its.save()


@frappe.whitelist(allow_guest=True)
def faceted_search_enabled():
	its = frappe.get_last_doc("Inventory Tools Settings")
	return {
		"show_on_website": its.show_on_website,
		"show_in_listview": its.show_in_listview,
	}
