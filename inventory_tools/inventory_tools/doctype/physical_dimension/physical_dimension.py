# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PhysicalDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		dimension_type: DF.Literal["Exterior", "Interior"]
		item_height: DF.Float
		item_length: DF.Float
		item_volume: DF.Float
		item_weight: DF.Float
		item_width: DF.Float
		orientation: DF.Check
		reference_doctype: DF.Link
		reference_document: DF.DynamicLink
		uom: DF.Link
		visualization: DF.AttachImage | None
	# end: auto-generated types

	def validate(self):
		self.calculate_item_volume()
		self.validate_item_case_fit()

	def calculate_item_volume(self):
		self.item_volume = flt(self.item_height) * flt(self.item_length) * flt(self.item_width)

	def validate_item_case_fit(self):
		if self.item_volume > self.case_volume:
			frappe.throw("Item volume should not be greater than case volume")
		if self.item_volume == 0:
			frappe.throw("Item volume cannot be zero")
