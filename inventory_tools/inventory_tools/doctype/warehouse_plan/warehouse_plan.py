# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehousePlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		floor_plan: DF.AttachImage | None
		group_warehouse: DF.Link | None
		horizontal: DF.Float
		matrix: DF.LongText | None
		offset: DF.Data | None
		uom: DF.Link | None
		vertical: DF.Float
	# end: auto-generated types

	@frappe.whitelist()
	def get_plan_warehouses(self):
		return frappe.get_all(
			"Warehouse",
			filters={"warehouse_plan": self.name},
			fields=["name", "warehouse_plan_coordinates", "rotation", "accessible_path"],
		)

	@frappe.whitelist()
	def set_warehouse_plan_details(self, warehouses: list):
		existing_warehouses = frappe.get_all(
			"Warehouse",
			filters={"warehouse_plan": self.name},
			pluck="name",
		)

		for warehouse in warehouses:
			warehouse_doc = frappe.get_doc("Warehouse", warehouse.get("warehouse_name"))
			warehouse_doc.update(
				{
					"warehouse_plan": self.name,
					"warehouse_plan_coordinates": warehouse.get("coordinates"),
					"rotation": warehouse.get("rotation"),
					"accessible_path": warehouse.get("accessible_path"),
				}
			)
			warehouse_doc.save()

			if warehouse_doc.name in existing_warehouses:
				existing_warehouses.remove(warehouse_doc.name)

		# if warehouses are deleted, remove them from the warehouse plan
		if len(existing_warehouses) > 0:
			for warehouse in existing_warehouses:
				frappe.db.set_value("Warehouse", warehouse, "warehouse_plan", None)
				frappe.db.set_value("Warehouse", warehouse, "warehouse_plan_coordinates", None)
				frappe.db.set_value("Warehouse", warehouse, "rotation", 0)
				frappe.db.set_value("Warehouse", warehouse, "accessible_path", None)

	@frappe.whitelist()
	def get_warehouse_dimensions(self, warehouse: str):
		warehouse_doc = frappe.get_doc("Warehouse", warehouse)
		dimensions = frappe.get_all(
			"Physical Dimension",
			filters={"reference_doctype": "Warehouse", "reference_document": warehouse_doc.name},
			fields=["item_length", "item_width", "uom"],
		)

		if not dimensions:
			return {}

		dimension = dimensions[0]

		# convert warehouse dimension UOM using UOM Conversion records
		if dimension.uom != self.uom:
			uom_conversion = frappe.get_all(
				"UOM Conversion Factor",
				filters={"category": "Length", "from_uom": dimension.uom, "to_uom": self.uom},
				pluck="value",
				limit=1,
			)

			if uom_conversion:
				dimension.item_length *= uom_conversion[0]
				dimension.item_width *= uom_conversion[0]

		return dimension
