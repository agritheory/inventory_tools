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

		case_height: DF.Float
		case_length: DF.Float
		case_volume: DF.Float
		case_weight: DF.Float
		case_width: DF.Float
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
		self.calculate_case_volume()
		self.validate_item_case_fit()

	def calculate_item_volume(self):
		self.item_volume = flt(self.item_height) * flt(self.item_length) * flt(self.item_width)

	def calculate_case_volume(self):
		self.case_volume = flt(self.case_height) * flt(self.case_length) * flt(self.case_width)

	def validate_item_case_fit(self):
		if self.item_volume > self.case_volume:
			frappe.throw("Item volume should not be greater than case volume")

		if self.item_volume == 0:
			frappe.throw("Item volume cannot be zero")
		if self.case_volume == 0:
			frappe.throw("Case volume cannot be zero")

		item_dims = sorted([self.item_length, self.item_width, self.item_height])
		case_dims = sorted([self.case_length, self.case_width, self.case_height])
		if any(item_dim > case_dim for item_dim, case_dim in zip(item_dims, case_dims)):
			frappe.throw("Item dimensions do not fit within the case dimensions")
