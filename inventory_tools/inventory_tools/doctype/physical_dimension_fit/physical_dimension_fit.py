# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PhysicalDimensionFit(Document):
	def validate(self):
		src = frappe.get_cached_doc("Physical Dimension", self.source_dimension)
		tgt = frappe.get_cached_doc("Physical Dimension", self.target_dimension)

		if src.dimension_type != "Exterior":
			frappe.throw(_("Source Dimension must be Exterior type."))
		if tgt.dimension_type != "Interior":
			frappe.throw(_("Target Dimension must be Interior type."))

		filters = [
			["source_dimension", "=", self.source_dimension],
			["target_dimension", "=", self.target_dimension],
		]
		if self.name:
			filters.append(["name", "!=", self.name])
		if self.company:
			filters.append(["company", "=", self.company])
		else:
			filters.append(["company", "is", "not set"])

		dupe = frappe.db.get_value("Physical Dimension Fit", filters, "name")
		if dupe:
			frappe.throw(_("Physical Dimension Fit already exists for this source, target, and company."))
