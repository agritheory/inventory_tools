# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ItemDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.dynamic_link.dynamic_link import DynamicLink
		from frappe.types import DF

		case_height: DF.Float
		case_length: DF.Float
		case_volume: DF.Float
		case_weight: DF.Float
		case_width: DF.Float
		dimension_type: DF.Literal["", "Interior", "Exterior"]
		euro_pallet_breadth: DF.Float
		euro_pallet_cases: DF.Int
		euro_pallet_cases_per_level: DF.Int
		euro_pallet_height: DF.Float
		euro_pallet_length: DF.Float
		euro_pallet_levels: DF.Int
		item_height: DF.Float
		item_length: DF.Float
		item_volume: DF.Float
		item_weight: DF.Float
		item_width: DF.Float
		links: DF.Table[DynamicLink]
		orientation: DF.Check
		us_pallet_breadth: DF.Float
		us_pallet_cases: DF.Int
		us_pallet_cases_per_level: DF.Int
		us_pallet_height: DF.Float
		us_pallet_length: DF.Float
		us_pallet_levels: DF.Int
	# end: auto-generated types

	def validate(self):
		self.calculate_item_volume()
		self.calculate_case_volume()
		self.calculate_us_pallet_cases()
		self.calculate_euro_pallet_cases()
		self.validate_item_case_fit()

	def calculate_item_volume(self):
		self.item_volume = flt(self.item_height) * flt(self.item_length) * flt(self.item_width)

	def calculate_case_volume(self):
		self.case_volume = flt(self.case_height) * flt(self.case_length) * flt(self.case_width)

	def calculate_us_pallet_cases(self):
		self.us_pallet_cases = flt(self.us_pallet_cases_per_level) * flt(self.us_pallet_levels)

	def calculate_euro_pallet_cases(self):
		self.euro_pallet_cases = flt(self.euro_pallet_cases_per_level) * flt(self.euro_pallet_levels)

	def validate_item_case_fit(self):
		if self.item_volume > self.case_volume:
			frappe.throw("Item volume should not be greater than case volume")

		if max(self.item_height, self.item_length, self.item_width) > min(
			self.case_height, self.case_length, self.case_width
		):
			frappe.throw("The longest item dimension does not fit within any case dimension")
