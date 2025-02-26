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
def get_warehouse_dimensions(warehouse: str, plan_uom: str):
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
	if dimension.uom != plan_uom:
		uom_conversion = frappe.get_all(
			"UOM Conversion Factor",
			filters={"category": "Length", "from_uom": dimension.uom, "to_uom": plan_uom},
			pluck="value",
			limit=1,
		)

		if uom_conversion:
			dimension.item_length *= uom_conversion[0]
			dimension.item_width *= uom_conversion[0]

	return dimension
